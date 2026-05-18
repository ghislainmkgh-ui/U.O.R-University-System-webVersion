"""Service d'authentification principal"""
import logging
import os
import secrets
import hashlib
from typing import Optional, List, Dict, Tuple
from core.security.password_hasher import PasswordHasher
from core.security.validators import Validators
from core.models.student import Student
from core.database.connection import DatabaseConnection
from app.services.integration.notification_service import NotificationService
from config.settings import (
    ACCESS_APPROVAL_BASE_URL,
    ACCESS_APPROVAL_TOKEN_TTL_HOURS,
    ACCESS_APPROVAL_TOKEN_SECRET,
)

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Service d'authentification pour les étudiants et administrateurs"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.password_hasher = PasswordHasher()
        self.validators = Validators()
        self._last_error = None
        self.notification_service = NotificationService()
        self._ensure_administrator_access_columns()
        self._ensure_access_request_table()
        self._ensure_access_request_token_table()

    def get_last_error(self) -> Optional[str]:
        """Retourne le dernier message d'erreur métier/technique."""
        return self._last_error

    def _set_last_error(self, message: Optional[str]):
        self._last_error = message

    def _get_table_columns(self, table_name: str) -> set:
        try:
            query = """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = %s
            """
            rows = self.db.execute_query(query, (table_name,)) or []
            return {row.get("COLUMN_NAME") for row in rows if row.get("COLUMN_NAME")}
        except Exception as e:
            logger.error(f"Error fetching columns for {table_name}: {e}")
            return set()

    def _ensure_administrator_access_columns(self):
        """Garantit que la table administrator peut porter les rôles et emails de notification."""
        try:
            columns = self._get_table_columns("administrator")
            if not columns:
                return

            if "email" not in columns:
                self.db.execute_update("ALTER TABLE administrator ADD COLUMN email VARCHAR(255) NULL")
            if "is_active" not in columns:
                self.db.execute_update("ALTER TABLE administrator ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1")
            if "is_super_admin" not in columns:
                self.db.execute_update(
                    "ALTER TABLE administrator ADD COLUMN is_super_admin TINYINT(1) NOT NULL DEFAULT 0"
                )

            refreshed_columns = self._get_table_columns("administrator")
            if "is_super_admin" in refreshed_columns:
                self._bootstrap_super_admin_if_missing(refreshed_columns)
        except Exception as e:
            logger.error(f"Error ensuring administrator access columns: {e}")

    def _bootstrap_super_admin_if_missing(self, columns: Optional[set] = None):
        """Attribue automatiquement le rôle super admin si un seul administrateur existe."""
        try:
            columns = columns or self._get_table_columns("administrator")
            if not columns or "is_super_admin" not in columns:
                return

            super_admins = self.db.execute_query(
                "SELECT id FROM administrator WHERE is_super_admin = 1 LIMIT 1"
            ) or []
            if super_admins:
                return

            active_filter = " WHERE is_active = 1" if "is_active" in columns else ""
            admins = self.db.execute_query(
                f"SELECT id FROM administrator{active_filter} ORDER BY id ASC LIMIT 2"
            ) or []

            if len(admins) == 1:
                self.db.execute_update(
                    "UPDATE administrator SET is_super_admin = 1 WHERE id = %s",
                    (admins[0]["id"],),
                )
                logger.info("No super admin found in database; promoted the only administrator to super admin")
            elif len(admins) > 1:
                logger.warning("Multiple administrators exist but none is marked as super admin in the database")
        except Exception as e:
            logger.warning(f"Unable to bootstrap super admin role from database: {e}")

    def _get_super_admin_recipients(self) -> List[str]:
        """Retourne les emails des super admins actifs stockés en base."""
        try:
            columns = self._get_table_columns("administrator")
            if not columns or "is_super_admin" not in columns or "email" not in columns:
                return []

            conditions = ["is_super_admin = 1", "email IS NOT NULL", "TRIM(email) <> ''"]
            if "is_active" in columns:
                conditions.append("is_active = 1")

            rows = self.db.execute_query(
                f"SELECT email FROM administrator WHERE {' AND '.join(conditions)} ORDER BY id ASC"
            ) or []

            seen = set()
            recipients = []
            for row in rows:
                email = str(row.get("email") or "").strip().lower()
                if email and email not in seen:
                    seen.add(email)
                    recipients.append(email)
            return recipients
        except Exception as e:
            logger.warning(f"Unable to load super admin recipients from database: {e}")
            return []

    def _email_belongs_to_super_admin(self, email: str) -> bool:
        """Indique si un email appartient déjà à un super admin en base."""
        try:
            email = (email or "").strip().lower()
            if not email:
                return False

            columns = self._get_table_columns("administrator")
            if not columns or "email" not in columns or "is_super_admin" not in columns:
                return False

            conditions = ["LOWER(email) = %s", "is_super_admin = 1"]
            if "is_active" in columns:
                conditions.append("is_active = 1")

            rows = self.db.execute_query(
                f"SELECT id FROM administrator WHERE {' AND '.join(conditions)} LIMIT 1",
                (email,),
            ) or []
            return bool(rows)
        except Exception as e:
            logger.warning(f"Unable to check super admin email in database: {e}")
            return False

    def _ensure_access_request_table(self):
        """Crée la table des demandes d'accès si absente."""
        try:
            query = """
                CREATE TABLE IF NOT EXISTS user_access_request (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
                    reviewed_by VARCHAR(255) NULL,
                    reviewed_at DATETIME NULL,
                    decision_note TEXT NULL,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_uar_username (username),
                    UNIQUE KEY uq_uar_email (email),
                    INDEX idx_uar_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            self.db.execute_update(query)
        except Exception as e:
            logger.error(f"Error ensuring user_access_request table: {e}")

    def _ensure_access_request_token_table(self):
        """Crée la table des jetons d'approbation email si absente."""
        try:
            query = """
                CREATE TABLE IF NOT EXISTS user_access_request_token (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    request_id INT NOT NULL,
                    action ENUM('APPROVE', 'REJECT') NOT NULL,
                    token_hash VARCHAR(128) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    used_at DATETIME NULL,
                    reviewer_identifier VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_uart_request (request_id),
                    INDEX idx_uart_action (action),
                    INDEX idx_uart_expires (expires_at),
                    UNIQUE KEY uq_uart_token_hash (token_hash),
                    CONSTRAINT fk_uart_request FOREIGN KEY (request_id)
                        REFERENCES user_access_request(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            self.db.execute_update(query)
        except Exception as e:
            logger.error(f"Error ensuring user_access_request_token table: {e}")

    @staticmethod
    def _normalize_action(action: str) -> Optional[str]:
        val = (action or "").strip().upper()
        if val in ("APPROVE", "REJECT"):
            return val
        return None

    def _hash_access_approval_token(self, raw_token: str) -> str:
        """Hash déterministe d'un jeton d'approbation (non stocké en clair)."""
        secret = ACCESS_APPROVAL_TOKEN_SECRET or "uor-access-approval-secret"
        payload = f"{secret}:{raw_token}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _invalidate_open_approval_tokens(self, request_id: int):
        """Invalide les anciens jetons non utilisés d'une demande."""
        try:
            self.db.execute_update(
                """
                UPDATE user_access_request_token
                SET used_at = NOW(), reviewer_identifier = %s
                WHERE request_id = %s AND used_at IS NULL
                """,
                ("system:rotated", request_id),
            )
        except Exception as e:
            logger.warning(f"Unable to invalidate old approval tokens for request {request_id}: {e}")

    def _create_access_approval_token(self, request_id: int, action: str) -> Optional[str]:
        """Crée un jeton one-time pour approuver/rejeter une demande."""
        try:
            action = self._normalize_action(action)
            if not action:
                return None

            raw_token = secrets.token_urlsafe(32)
            token_hash = self._hash_access_approval_token(raw_token)
            ttl_hours = max(1, int(ACCESS_APPROVAL_TOKEN_TTL_HOURS or 72))

            self.db.execute_update(
                """
                INSERT INTO user_access_request_token (request_id, action, token_hash, expires_at)
                VALUES (%s, %s, %s, DATE_ADD(NOW(), INTERVAL %s HOUR))
                """,
                (request_id, action, token_hash, ttl_hours),
            )
            return raw_token
        except Exception as e:
            logger.warning(f"Unable to create approval token for request {request_id}: {e}")
            return None

    def _build_access_approval_link(self, token: str, action: str) -> Optional[str]:
        """Construit le lien de décision utilisé dans l'e-mail Super Admin."""
        base_url = (os.getenv("ACCESS_APPROVAL_BASE_URL") or ACCESS_APPROVAL_BASE_URL or "").strip().rstrip("/")
        if not base_url:
            return None
        action = (action or "").strip().lower()
        return f"{base_url}/access-request/decision?action={action}&token={token}"

    def process_access_request_token_decision(
        self,
        token: str,
        action: str,
        reviewer_identifier: str = "super_admin_email",
    ) -> Tuple[bool, str]:
        """Traite une décision provenant d'un lien e-mail (one-time token)."""
        try:
            token = (token or "").strip()
            action_norm = self._normalize_action(action)

            if not token:
                return False, "Jeton manquant"
            if not action_norm:
                return False, "Action invalide"

            token_hash = self._hash_access_approval_token(token)
            rows = self.db.execute_query(
                """
                SELECT id, request_id, action, expires_at, used_at
                FROM user_access_request_token
                WHERE token_hash = %s
                LIMIT 1
                """,
                (token_hash,),
            ) or []

            if not rows:
                return False, "Lien invalide ou expiré"

            tok = rows[0]
            if str(tok.get("action") or "").upper() != action_norm:
                return False, "Action non autorisée pour ce lien"
            if tok.get("used_at"):
                return False, "Ce lien a déjà été utilisé"

            exp_rows = self.db.execute_query(
                "SELECT NOW() <= %s AS is_valid",
                (tok.get("expires_at"),),
            ) or []
            if not exp_rows or not bool(exp_rows[0].get("is_valid")):
                return False, "Lien expiré"

            request_id = int(tok.get("request_id"))
            if action_norm == "APPROVE":
                ok, msg = self.approve_access_request(request_id, reviewer_identifier=reviewer_identifier)
            else:
                ok, msg = self.reject_access_request(request_id, reviewer_identifier=reviewer_identifier)

            if not ok:
                return False, msg

            self.db.execute_update(
                """
                UPDATE user_access_request_token
                SET used_at = NOW(), reviewer_identifier = %s
                WHERE id = %s
                """,
                (reviewer_identifier, tok.get("id")),
            )
            return True, msg
        except Exception as e:
            logger.error(f"Error processing access token decision: {e}")
            return False, f"Erreur: {str(e)}"

    def _resolve_admin_role(self, admin: dict, identifier: str = "") -> str:
        """Détermine le rôle admin final: super_admin ou user."""
        if bool(admin.get("is_super_admin")):
            return "super_admin"

        admin_id = admin.get("id")
        if admin_id:
            try:
                rows = self.db.execute_query(
                    "SELECT is_super_admin FROM administrator WHERE id = %s LIMIT 1",
                    (admin_id,),
                ) or []
                if rows and bool(rows[0].get("is_super_admin")):
                    return "super_admin"
            except Exception:
                pass

        return "user"

    def _get_access_request_by_identifier(self, identifier: str) -> Optional[dict]:
        """Retourne la dernière demande d'accès correspondant au username/email."""
        try:
            value = (identifier or "").strip().lower()
            if not value:
                return None
            rows = self.db.execute_query(
                """
                SELECT *
                FROM user_access_request
                WHERE LOWER(username) = %s OR LOWER(email) = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (value, value),
            ) or []
            return rows[0] if rows else None
        except Exception:
            return None

    def get_pending_access_requests(self) -> List[Dict]:
        """Liste des demandes d'accès en attente de validation super admin."""
        try:
            rows = self.db.execute_query(
                """
                SELECT id, username, email, status, requested_at
                FROM user_access_request
                WHERE status = 'PENDING'
                ORDER BY requested_at ASC
                """
            )
            return rows or []
        except Exception as e:
            logger.error(f"Error loading pending access requests: {e}")
            return []

    def _notify_super_admin_new_request(self, username: str, email: str) -> None:
        """Envoie une alerte email au super admin quand une demande est soumise."""
        try:
            recipients = self._get_super_admin_recipients()
            if not recipients:
                return

            req_rows = self.db.execute_query(
                """
                SELECT id, requested_at
                FROM user_access_request
                WHERE LOWER(username) = %s AND LOWER(email) = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                ((username or "").strip().lower(), (email or "").strip().lower()),
            ) or []

            request_id = req_rows[0].get("id") if req_rows else None
            requested_at = req_rows[0].get("requested_at") if req_rows else None

            approve_link = None
            reject_link = None
            if request_id:
                self._invalidate_open_approval_tokens(int(request_id))
                approve_token = self._create_access_approval_token(int(request_id), "APPROVE")
                reject_token = self._create_access_approval_token(int(request_id), "REJECT")
                if approve_token:
                    approve_link = self._build_access_approval_link(approve_token, "approve")
                if reject_token:
                    reject_link = self._build_access_approval_link(reject_token, "reject")

            subject = "Nouvelle demande d'accès logiciel - U.O.R"
            body_lines = [
                "Bonjour Super Admin,",
                "",
                "Une nouvelle demande d'accès au logiciel a été soumise.",
                "",
                f"- Username: {username}",
                f"- Email: {email}",
            ]

            if request_id:
                body_lines.append(f"- Référence demande: #{request_id}")
            if requested_at:
                body_lines.append(f"- Date de demande: {requested_at}")

            body_lines.extend(["", "Validation rapide à distance :"])

            if approve_link and reject_link:
                body_lines.extend([
                    f"- Valider la demande : {approve_link}",
                    f"- Rejeter la demande : {reject_link}",
                    "",
                    "Ces liens sont à usage unique et expirent automatiquement.",
                ])
            else:
                body_lines.extend([
                    "- Les liens d'approbation e-mail ne sont pas configurés.",
                    "- Configurez ACCESS_APPROVAL_BASE_URL pour activer la validation distante.",
                    "- En attendant, vous pouvez valider/rejeter depuis le dashboard.",
                ])

            body_lines.extend(["", "U.O.R - Système de Contrôle d'Accès"])
            body = "\n".join(body_lines)

            for recipient in recipients:
                self.notification_service._send_email(recipient, subject, body)
        except Exception as e:
            logger.warning(f"Unable to notify super admin for access request: {e}")

    def _notify_requester_decision(self, email: str, approved: bool) -> None:
        """Informe le demandeur de la décision super admin."""
        try:
            if not email:
                return
            if approved:
                subject = "Votre accès au logiciel U.O.R a été approuvé"
                body = (
                    "Bonjour,\n\n"
                    "Votre demande d'accès au logiciel U.O.R a été validée par le Super Admin.\n"
                    "Vous pouvez maintenant vous connecter à l'application.\n\n"
                    "U.O.R - Système de Contrôle d'Accès"
                )
            else:
                subject = "Votre demande d'accès au logiciel U.O.R n'a pas été approuvée"
                body = (
                    "Bonjour,\n\n"
                    "Votre demande d'accès au logiciel U.O.R a été rejetée par le Super Admin.\n"
                    "Contactez l'administration pour plus d'informations si nécessaire.\n\n"
                    "U.O.R - Système de Contrôle d'Accès"
                )
            self.notification_service._send_email(email, subject, body)
        except Exception as e:
            logger.warning(f"Unable to notify requester decision: {e}")

    def _notify_access_revoked(self, email: str, username: str = "") -> None:
        """Informe un administrateur que son accès au logiciel a été révoqué."""
        try:
            email = (email or "").strip().lower()
            if not email:
                return

            display_name = (username or "").strip() or "utilisateur"
            subject = "Accès révoqué - U.O.R"
            body = (
                f"Bonjour {display_name},\n\n"
                "Votre compte administrateur a été supprimé par le Super Admin.\n"
                "Vous n'avez plus accès au logiciel.\n\n"
                "Si vous pensez qu'il s'agit d'une erreur, veuillez contacter l'administration.\n\n"
                "U.O.R - Système de Contrôle d'Accès"
            )

            self.notification_service._send_email(email, subject, body)
        except Exception as e:
            logger.warning(f"Unable to notify revoked access for '{username}': {e}")

    def register_user_access_request(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """Crée une demande d'accès (workflow validé par super admin)."""
        try:
            username = (username or "").strip()
            email = (email or "").strip().lower()
            password = (password or "").strip()

            if not username or not email or not password:
                return False, "Username, email et mot de passe requis"
            if len(password) < 6:
                return False, "Le mot de passe doit avoir au moins 6 caractères"

            # Refuser explicitement les demandes sur un email déjà utilisé par un super admin en base
            if self._email_belongs_to_super_admin(email):
                return False, "Cet email est réservé au super admin"

            admin_columns = self._get_table_columns("administrator")
            if not admin_columns:
                return False, "Table administrator introuvable"

            # Vérifier compte déjà actif
            existing_user = self.db.execute_query(
                "SELECT id FROM administrator WHERE LOWER(username) = %s",
                (username.lower(),),
            )
            if existing_user:
                return False, "Ce nom d'utilisateur existe déjà"

            if "email" in admin_columns:
                existing_email = self.db.execute_query(
                    "SELECT id FROM administrator WHERE LOWER(email) = %s",
                    (email,),
                )
                if existing_email:
                    return False, "Cet email existe déjà"

            # Vérifier demande déjà existante
            existing_request = self.db.execute_query(
                "SELECT id, status FROM user_access_request WHERE LOWER(username) = %s OR LOWER(email) = %s LIMIT 1",
                (username.lower(), email),
            ) or []

            password_hash = self.password_hasher.hash_password(password)

            if existing_request:
                req = existing_request[0]
                status = str(req.get("status") or "").upper()
                if status == "PENDING":
                    return False, "Une demande est déjà en attente de validation"

                # Réouverture d'une demande rejetée/ancienne
                self.db.execute_update(
                    """
                    UPDATE user_access_request
                    SET username = %s,
                        email = %s,
                        password_hash = %s,
                        status = 'PENDING',
                        reviewed_by = NULL,
                        reviewed_at = NULL,
                        decision_note = NULL
                    WHERE id = %s
                    """,
                    (username, email, password_hash, req.get("id")),
                )
            else:
                self.db.execute_update(
                    """
                    INSERT INTO user_access_request (username, email, password_hash, status)
                    VALUES (%s, %s, %s, 'PENDING')
                    """,
                    (username, email, password_hash),
                )

            self._notify_super_admin_new_request(username, email)
            return True, "Demande envoyée au super admin pour validation"
        except Exception as e:
            logger.error(f"Error creating access request: {e}")
            return False, f"Erreur: {str(e)}"

    def approve_access_request(self, request_id: int, reviewer_identifier: str = "super_admin") -> Tuple[bool, str]:
        """Valide une demande en attente et crée le compte utilisateur."""
        try:
            rows = self.db.execute_query(
                "SELECT * FROM user_access_request WHERE id = %s",
                (request_id,),
            ) or []
            if not rows:
                return False, "Demande introuvable"

            req = rows[0]
            if str(req.get("status") or "").upper() != "PENDING":
                return False, "Cette demande n'est plus en attente"

            columns = self._get_table_columns("administrator")
            if not columns:
                return False, "Table administrator introuvable"
            if "username" not in columns or "password_hash" not in columns:
                return False, "La table administrator ne contient pas les colonnes requises"

            username = req.get("username")
            email = req.get("email")
            password_hash = req.get("password_hash")

            # anti-duplication finale
            if self.db.execute_query("SELECT id FROM administrator WHERE LOWER(username)=%s", (str(username).lower(),)):
                return False, "Compte déjà existant (username)"
            if "email" in columns and self.db.execute_query("SELECT id FROM administrator WHERE LOWER(email)=%s", (str(email).lower(),)):
                return False, "Compte déjà existant (email)"

            insert_columns = ["username", "password_hash"]
            insert_values = [username, password_hash]

            if "email" in columns:
                insert_columns.append("email")
                insert_values.append(email)
            if "is_active" in columns:
                insert_columns.append("is_active")
                insert_values.append(1)
            if "is_super_admin" in columns:
                insert_columns.append("is_super_admin")
                insert_values.append(0)

            self.db.execute_update(
                f"INSERT INTO administrator ({', '.join(insert_columns)}) VALUES ({', '.join(['%s'] * len(insert_columns))})",
                tuple(insert_values),
            )

            self.db.execute_update(
                """
                UPDATE user_access_request
                SET status='APPROVED', reviewed_by=%s, reviewed_at=NOW()
                WHERE id=%s
                """,
                (reviewer_identifier, request_id),
            )

            self._notify_requester_decision(email, approved=True)
            return True, "Demande approuvée avec succès"
        except Exception as e:
            logger.error(f"Error approving access request: {e}")
            return False, f"Erreur: {str(e)}"

    def reject_access_request(self, request_id: int, reviewer_identifier: str = "super_admin", note: str = "") -> Tuple[bool, str]:
        """Rejette une demande en attente."""
        try:
            rows = self.db.execute_query(
                "SELECT * FROM user_access_request WHERE id = %s",
                (request_id,),
            ) or []
            if not rows:
                return False, "Demande introuvable"

            req = rows[0]
            if str(req.get("status") or "").upper() != "PENDING":
                return False, "Cette demande n'est plus en attente"

            self.db.execute_update(
                """
                UPDATE user_access_request
                SET status='REJECTED', reviewed_by=%s, reviewed_at=NOW(), decision_note=%s
                WHERE id=%s
                """,
                (reviewer_identifier, note or None, request_id),
            )

            self._notify_requester_decision(req.get("email"), approved=False)
            return True, "Demande rejetée"
        except Exception as e:
            logger.error(f"Error rejecting access request: {e}")
            return False, f"Erreur: {str(e)}"
    
    def get_approved_administrators(self) -> List[Dict]:
        """Retourne tous les comptes administrateurs approuvés (non super-admin) avec leurs infos."""
        try:
            columns = self._get_table_columns("administrator")
            if not columns:
                return []
            select_cols = ["id", "username"]
            if "email" in columns:
                select_cols.append("email")
            if "is_active" in columns:
                select_cols.append("is_active")
            if "is_super_admin" in columns:
                select_cols.append("is_super_admin")
            rows = self.db.execute_query(
                f"SELECT {', '.join(select_cols)} FROM administrator ORDER BY id ASC"
            )
            return rows or []
        except Exception as e:
            logger.error(f"Error loading administrators: {e}")
            return []

    def delete_administrator(self, admin_id: int, requester_is_super_admin: bool = False) -> Tuple[bool, str]:
        """Supprime un compte administrateur non-super-admin. Seul le super admin peut effectuer cette action."""
        if not requester_is_super_admin:
            return False, "Accès refusé : opération réservée au super admin"
        try:
            columns = self._get_table_columns("administrator")
            if not columns:
                return False, "Table administrator introuvable"

            select_cols = ["id", "username", "is_super_admin"]
            if "email" in columns:
                select_cols.append("email")

            rows = self.db.execute_query(
                f"SELECT {', '.join(select_cols)} FROM administrator WHERE id = %s LIMIT 1",
                (admin_id,),
            ) or []
            if not rows:
                return False, "Utilisateur introuvable"
            target = rows[0]
            if target.get("is_super_admin"):
                return False, "Impossible de supprimer le super administrateur"
            username = target.get("username", str(admin_id))
            target_email = target.get("email") if "email" in select_cols else None
            self.db.execute_update("DELETE FROM administrator WHERE id = %s", (admin_id,))
            self._notify_access_revoked(target_email, username)
            logger.info(f"Administrator '{username}' (id={admin_id}) deleted by super admin")
            return True, f"Utilisateur « {username} » supprimé avec succès"
        except Exception as e:
            logger.error(f"Error deleting administrator {admin_id}: {e}")
            return False, f"Erreur: {str(e)}"

    def register_student(self, student: Student, password: str) -> bool:
        """
        Enregistre un nouvel étudiant
        
        Args:
            student: Objet Student
            password: Mot de passe en clair
            
        Returns:
            True si l'enregistrement réussit
        """
        try:
            # Valider les entrées
            valid, msg = self.validators.validate_numeric_password(password)
            if not valid:
                logger.warning(f"Invalid password for student {student.student_number}: {msg}")
                return False
            
            # Hacher le mot de passe
            password_hash = self.password_hasher.hash_password(password)
            
            # Insérer en base de données
            query = """
                INSERT INTO student (student_number, firstname, lastname, email, phone_number, promotion_id, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                student.student_number,
                student.firstname,
                student.lastname,
                student.email,
                student.phone_number,
                student.promotion_id,
                password_hash
            )
            
            self.db.execute_update(query, params)
            logger.info(f"Student {student.student_number} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error registering student: {e}")
            return False
    
    def authenticate_student(self, student_number: str, password: str) -> dict:
        """
        Authentifie un étudiant
        
        Args:
            student_number: Numéro d'étudiant
            password: Mot de passe en clair
            
        Returns:
            Dictionnaire avec les données de l'étudiant ou None
        """
        try:
            # Récupérer l'étudiant de la base
            query = "SELECT * FROM student WHERE student_number = %s"
            results = self.db.execute_query(query, (student_number,))
            
            if not results:
                logger.warning(f"Authentication failed: Student {student_number} not found")
                return None
            
            student = results[0]
            
            # Vérifier le mot de passe
            if not self.password_hasher.verify_password(password, student['password_hash']):
                logger.warning(f"Authentication failed: Wrong password for {student_number}")
                return None
            
            logger.info(f"Student {student_number} authenticated successfully")
            return student
            
        except Exception as e:
            logger.error(f"Error authenticating student: {e}")
            return None

    def authenticate_admin(self, username: str, password: str) -> dict:
        """Authentifie un administrateur"""
        try:
            columns = self._get_table_columns("administrator")
            if "email" in columns:
                query = """
                    SELECT *
                    FROM administrator
                    WHERE (username = %s OR LOWER(email) = %s)
                      AND is_active = 1
                """
                results = self.db.execute_query(query, (username, (username or "").strip().lower()))
            else:
                query = "SELECT * FROM administrator WHERE username = %s AND is_active = 1"
                results = self.db.execute_query(query, (username,))

            if not results:
                logger.warning(f"Authentication failed: Admin {username} not found")
                return None

            admin = results[0]

            if not self.password_hasher.verify_password(password, admin['password_hash']):
                logger.warning(f"Authentication failed: Wrong password for admin {username}")
                return None

            logger.info(f"Admin {username} authenticated successfully")
            return admin
        except Exception as e:
            logger.error(f"Error authenticating admin: {e}")
            return None

    def authenticate(self, identifier: str, password: str):
        """Authentifie par numéro d'étudiant ou email.

        Returns:
            (user_dict, error_message)
        """
        if not identifier or not password:
            return None, "Identifiant et mot de passe requis"

        # 1) Try admin
        admin = self.authenticate_admin(identifier, password)
        if admin:
            admin["role"] = self._resolve_admin_role(admin, identifier)
            return admin, None

        # 2) Try student number
        user = self.authenticate_student(identifier, password)
        if user:
            user["role"] = "student"
            return user, None

        # 3) Try student email
        try:
            query = "SELECT * FROM student WHERE email = %s"
            results = self.db.execute_query(query, (identifier,))
            if results:
                student = results[0]
                if self.password_hasher.verify_password(password, student['password_hash']):
                    student["role"] = "student"
                    logger.info(f"Student {student.get('email')} authenticated successfully")
                    return student, None
        except Exception as e:
            logger.error(f"Error authenticating by email: {e}")

        # 4) Informer si une demande est en attente/rejetée
        req = self._get_access_request_by_identifier(identifier)
        if req:
            status = str(req.get("status") or "").upper()
            if status == "PENDING":
                return None, "Votre compte est en attente de validation par le super admin"
            if status == "REJECTED":
                return None, "Votre demande d'acces a ete rejetee"

        return None, "Identifiant ou mot de passe incorrect. Verifiez vos informations puis reessayez."

    def register_admin_account(self, username: str, email: str, password: str) -> tuple:
        """Soumet une demande d'accès (validation par super admin).

        Returns:
            (success: bool, message: str)
        """
        return self.register_user_access_request(username, email, password)
    
    def change_password(self, student_number: str, old_password: str, new_password: str) -> bool:
        """
        Change le mot de passe d'un étudiant
        
        Args:
            student_number: Numéro d'étudiant
            old_password: Ancien mot de passe
            new_password: Nouveau mot de passe
            
        Returns:
            True si le changement réussit
        """
        try:
            # Valider les entrées
            valid, msg = self.validators.validate_numeric_password(new_password)
            if not valid:
                logger.warning(f"Invalid new password for {student_number}: {msg}")
                return False
            
            # Authentifier avec l'ancien mot de passe
            student = self.authenticate_student(student_number, old_password)
            if not student:
                logger.warning(f"Password change failed: Authentication failed for {student_number}")
                return False
            
            # Hacher le nouveau mot de passe
            new_hash = self.password_hasher.hash_password(new_password)
            
            # Mettre à jour en base
            query = "UPDATE student SET password_hash = %s WHERE student_number = %s"
            self.db.execute_update(query, (new_hash, student_number))
            
            logger.info(f"Password changed successfully for {student_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False

    def reset_password_by_email(self, identifier: str, new_password: str) -> tuple:
        """Réinitialise le mot de passe via email ou matricule (flux 'mot de passe oublié').

        Returns:
            (success: bool, message: str)
        """
        try:
            identifier = (identifier or "").strip()
            if not identifier or not new_password:
                return False, "Identifiant et mot de passe requis"
            if len(new_password) < 4:
                return False, "Le mot de passe doit avoir au moins 4 caractères"

            new_hash = self.password_hasher.hash_password(new_password)

            # 1) Admin par username
            res = self.db.execute_query(
                "SELECT id FROM administrator WHERE username = %s", (identifier,)
            )
            if res:
                self.db.execute_update(
                    "UPDATE administrator SET password_hash = %s WHERE username = %s",
                    (new_hash, identifier),
                )
                logger.info(f"Admin password reset for '{identifier}'")
                return True, "Mot de passe réinitialisé avec succès"

            # 2) Étudiant par email
            res = self.db.execute_query(
                "SELECT id FROM student WHERE email = %s", (identifier,)
            )
            if res:
                self.db.execute_update(
                    "UPDATE student SET password_hash = %s WHERE email = %s",
                    (new_hash, identifier),
                )
                logger.info(f"Student password reset by email '{identifier}'")
                return True, "Mot de passe réinitialisé avec succès"

            # 3) Étudiant par matricule
            res = self.db.execute_query(
                "SELECT id FROM student WHERE student_number = %s", (identifier,)
            )
            if res:
                self.db.execute_update(
                    "UPDATE student SET password_hash = %s WHERE student_number = %s",
                    (new_hash, identifier),
                )
                logger.info(f"Student password reset by number '{identifier}'")
                return True, "Mot de passe réinitialisé avec succès"

            return False, "Aucun compte trouvé pour cet identifiant"

        except Exception as e:
            logger.error(f"reset_password_by_email error: {e}")
            return False, f"Erreur: {str(e)}"

    def authenticate_by_email_no_pw(self, email: str) -> dict:
        """Authentifie un utilisateur par email uniquement (flux OAuth — identité vérifiée par le provider).

        Returns:
            dict with 'role' key, or None if not found.
        """
        try:
            email_lower = (email or "").strip().lower()
            if not email_lower:
                return None

            # Vérifie dans administrator si une colonne email existe
            try:
                res = self.db.execute_query(
                    "SELECT * FROM administrator WHERE LOWER(email) = %s AND is_active = 1",
                    (email_lower,),
                )
                if res:
                    admin = res[0]
                    admin["role"] = self._resolve_admin_role(admin, email_lower)
                    logger.info(f"OAuth admin login: {email_lower}")
                    return admin
            except Exception:
                pass  # colonne email absente dans administrator – non bloquant

            # Vérifie dans student
            res = self.db.execute_query(
                "SELECT * FROM student WHERE LOWER(email) = %s", (email_lower,)
            )
            if res:
                student = res[0]
                student["role"] = "student"
                logger.info(f"OAuth student login: {email_lower}")
                return student

            logger.warning(f"OAuth: no account for email '{email_lower}'")
            return None

        except Exception as e:
            logger.error(f"authenticate_by_email_no_pw error: {e}")
            return None

    def _generate_placeholder_password(self) -> str:
        """Génère un mot de passe temporaire non communiqué"""
        return secrets.token_urlsafe(24)

    def register_student_with_face(self, student: Student, password: Optional[str], face_encoding: Optional[bytes]) -> int:
        """
        Enregistre un nouvel étudiant avec encodage facial

        Args:
            student: Objet Student
            password: Mot de passe en clair
            face_encoding: Encodage facial en bytes

        Returns:
            ID de l'étudiant si succès, sinon 0
        """
        self._set_last_error(None)
        try:
            if password:
                valid, msg = self.validators.validate_numeric_password(password)
                if not valid:
                    error_msg = f"Mot de passe invalide: {msg}"
                    self._set_last_error(error_msg)
                    logger.warning(f"Invalid password for student {student.student_number}: {msg}")
                    return 0
                password_to_hash = password
            else:
                password_to_hash = self._generate_placeholder_password()

            password_hash = self.password_hasher.hash_password(password_to_hash)

            columns = self._get_table_columns("student")
            insert_columns = []
            insert_values = []

            def add_column(name, value):
                if name in columns:
                    insert_columns.append(name)
                    insert_values.append(value)

            add_column("student_number", student.student_number)
            add_column("firstname", student.firstname)
            add_column("lastname", student.lastname)
            add_column("postnom", getattr(student, "postnom", None))
            add_column("email", student.email)
            add_column("phone_number", student.phone_number)
            add_column("promotion_id", student.promotion_id)
            add_column("passport_photo_path", student.passport_photo_path)
            add_column("passport_photo_blob", student.passport_photo_blob)
            add_column("password_hash", password_hash)
            add_column("face_encoding", face_encoding)
            add_column("academic_year_id", student.academic_year_id)

            placeholders = ", ".join(["%s"] * len(insert_columns))
            columns_sql = ", ".join(insert_columns)
            query = f"INSERT INTO student ({columns_sql}) VALUES ({placeholders})"
            self.db.execute_update(query, tuple(insert_values))

            result = self.db.execute_query(
                "SELECT id FROM student WHERE student_number = %s",
                (student.student_number,)
            )
            if not result:
                error_msg = "Étudiant inséré mais identifiant introuvable"
                self._set_last_error(error_msg)
                logger.error("Student inserted but ID not found")
                return 0

            student_id = result[0]["id"]
            self._set_last_error(None)
            if face_encoding is None:
                logger.info(f"Student {student.student_number} registered without face encoding")
            else:
                logger.info(f"Student {student.student_number} registered with face encoding")
            return student_id

        except Exception as e:
            error_msg = str(e)
            self._set_last_error(error_msg)
            logger.error(f"Error registering student with face: {e}")
            return 0
