"""Service de gestion des finances"""
import logging
import random
import threading
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
from core.database.connection import DatabaseConnection
from app.services.finance.academic_year_service import AcademicYearService
from app.services.integration.notification_service import NotificationService
from app.services.auth.authentication_service import AuthenticationService

logger = logging.getLogger(__name__)


class FinanceService:
    """Service pour gérer les paiements et seuils financiers"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.academic_service = AcademicYearService()
        self.notification_service = NotificationService()
        self.auth_service = AuthenticationService()
        self._last_error: Optional[str] = None

    def get_last_error(self) -> Optional[str]:
        """Retourne la dernière erreur métier rencontrée."""
        return self._last_error

    def _set_last_error(self, message: Optional[str]):
        self._last_error = message

    def _ensure_payment_history_table(self) -> None:
        """Crée la table d'historique des paiements si nécessaire"""
        try:
            query = """
                CREATE TABLE IF NOT EXISTS payment_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    amount_paid_fc DECIMAL(15, 2) NOT NULL,
                    amount_paid_usd DECIMAL(15, 2) NOT NULL,
                    payment_method VARCHAR(50) DEFAULT NULL,
                    payment_reference VARCHAR(255) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_student (student_id),
                    INDEX idx_created (created_at),
                    CONSTRAINT fk_payment_student FOREIGN KEY (student_id)
                        REFERENCES student(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            self.db.execute_update(query)
        except Exception as e:
            logger.error(f"Error ensuring payment_history table: {e}")

    def _ensure_access_code_history_table(self) -> None:
        """Crée la table d'historique des codes d'accès si nécessaire"""
        try:
            query = """
                CREATE TABLE IF NOT EXISTS access_code_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    access_code VARCHAR(20) NOT NULL,
                    access_type ENUM('full', 'partial') NOT NULL,
                    expires_at DATETIME DEFAULT NULL,
                    issued_at DATETIME NOT NULL,
                    INDEX idx_student (student_id),
                    INDEX idx_issued (issued_at),
                    CONSTRAINT fk_access_code_student FOREIGN KEY (student_id)
                        REFERENCES student(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            self.db.execute_update(query)
        except Exception as e:
            logger.error(f"Error ensuring access_code_history table: {e}")

    def _get_table_columns(self, table_name: str) -> set:
        """Retourne l'ensemble des colonnes existantes pour une table"""
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
    
    def get_student_finance(self, student_id: int) -> Optional[dict]:
        """Récupère le profil financier d'un étudiant"""
        try:
            query = "SELECT * FROM finance_profile WHERE student_id = %s"
            results = self.db.execute_query(query, (student_id,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting finance profile: {e}")
            return None

    def create_finance_profile(self, student_id: int, threshold_required: Decimal = None, academic_year_id: int = None) -> bool:
        """Crée un profil financier initial pour un étudiant
        
        NOUVELLE ARCHITECTURE: Utilise les frais/seuils de la PROMOTION de l'étudiant
        Les frais finaux et seuils sont maintenant définis par promotion (pas année académique)
        """
        try:
            columns = self._get_table_columns("finance_profile")
            if not columns:
                columns = {
                    "student_id",
                    "amount_paid",
                    "threshold_required",
                    "is_eligible",
                    "last_payment_date",
                    "created_at",
                    "updated_at",
                    "final_fee",
                    "academic_year_id",
                }
            
            # Récupérer la promotion de l'étudiant (source unique de vérité pour frais/seuils)
            promo_data = self.db.execute_query(
                """
                SELECT p.fee_usd, p.threshold_amount, p.name AS promotion_name,
                       d.name AS department_name, f.name AS faculty_name
                FROM student s
                JOIN promotion p ON s.promotion_id = p.id
                JOIN department d ON p.department_id = d.id
                JOIN faculty f ON d.faculty_id = f.id
                WHERE s.id = %s
                """,
                (student_id,)
            )
            
            if promo_data and len(promo_data) > 0:
                # Utiliser les valeurs de la promotion
                promo = promo_data[0]
                final_fee = Decimal(str(promo.get('fee_usd') or 0))
                threshold_amount = Decimal(str(promo.get('threshold_amount') or 0))
                logger.info(f"Creating finance profile for student {student_id} - Promotion: {promo.get('promotion_name')}, Final Fee: ${final_fee}, Threshold: ${threshold_amount}")
            else:
                # Fallback si la promotion n'a pas de valeurs configurées
                logger.warning(f"No promotion data found for student {student_id}, using fallback values")
                threshold_amount = Decimal(str(threshold_required or 0))
                final_fee = Decimal(str(threshold_required or 0))

            now = datetime.now()
            insert_columns = []
            insert_values = []

            def add_column(name, value):
                if name in columns:
                    insert_columns.append(name)
                    insert_values.append(value)

            add_column("student_id", student_id)
            add_column("amount_paid", "0")
            add_column("threshold_required", str(threshold_amount))
            add_column("final_fee", str(final_fee))
            add_column("academic_year_id", academic_year_id)
            add_column("is_eligible", 0)
            add_column("last_payment_date", None)
            add_column("created_at", now)
            add_column("updated_at", now)

            placeholders = ", ".join(["%s"] * len(insert_columns))
            columns_sql = ", ".join(insert_columns)
            query = f"INSERT INTO finance_profile ({columns_sql}) VALUES ({placeholders})"
            self.db.execute_update(query, tuple(insert_values))
            logger.info(f"Finance profile created for student {student_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating finance profile: {e}")
            return False
    
    def is_threshold_reached(self, student_id: int) -> bool:
        """Vérifie si le seuil financier est atteint"""
        try:
            finance = self.get_student_finance(student_id)
            if not finance:
                logger.warning(f"No finance profile found for student {student_id}")
                return False
            
            amount_paid = Decimal(str(finance['amount_paid']))
            threshold = Decimal(str(finance['threshold_required']))

            # Règle métier: sans seuil configuré (0 ou NULL),
            # on considère que le seuil n'est pas applicable (jamais "atteint").
            if threshold <= 0:
                return False
            
            is_eligible = amount_paid >= threshold
            logger.info(f"Student {student_id} threshold check: {is_eligible}")
            return is_eligible
            
        except Exception as e:
            logger.error(f"Error checking threshold: {e}")
            return False
    
    def record_payment(self, student_id: int, amount: Decimal) -> bool:
        """Enregistre un paiement pour un étudiant
        
        NOUVELLE ARCHITECTURE: Utilise les frais/seuils de la PROMOTION de l'étudiant
        """
        try:
            self._set_last_error(None)
            self._ensure_payment_history_table()
            finance = self.get_student_finance(student_id)
            if not finance:
                logger.error(f"No finance profile for student {student_id}")
                self._set_last_error(f"NO_FINANCE_PROFILE: student_id={student_id}")
                return False
            
            current_paid = Decimal(str(finance['amount_paid']))
            new_amount = current_paid + amount
            
            # TOUJOURS utiliser les valeurs de la PROMOTION (source unique de vérité)
            promo_data = self.db.execute_query(
                """
                SELECT p.fee_usd, p.threshold_amount, p.name AS promotion_name,
                       d.name AS department_name, f.name AS faculty_name,
                       s.firstname, s.lastname, s.email, s.phone_number
                FROM student s
                JOIN promotion p ON s.promotion_id = p.id
                JOIN department d ON p.department_id = d.id
                JOIN faculty f ON d.faculty_id = f.id
                WHERE s.id = %s
                """,
                (student_id,)
            )
            
            if not promo_data or len(promo_data) == 0:
                logger.error(f"No promotion data found for student {student_id}")
                self._set_last_error(f"NO_PROMOTION_DATA: student_id={student_id}")
                return False
            
            promo = promo_data[0]
            # Utiliser les valeurs ACTUELLES de la promotion
            threshold = Decimal(str(promo.get('threshold_amount') or 0))
            final_fee = Decimal(str(promo.get('fee_usd') or threshold))
            promotion_name = promo.get('promotion_name', 'N/A')
            department_name = promo.get('department_name', 'N/A')
            faculty_name = promo.get('faculty_name', 'N/A')
            threshold_enabled = threshold > 0

            # ⚠️ VÉRIFICATION STRICTE: Pas de paiement si aucun frais n'est défini
            if final_fee <= 0:
                logger.warning(f"Payment rejected for student {student_id}: No active academic fees (final_fee={final_fee})")
                self._set_last_error(
                    f"NO_ACTIVE_FEES: student_id={student_id}; promotion={promotion_name}; final_fee={final_fee}"
                )
                return False

            if final_fee > 0 and new_amount > final_fee:
                logger.warning(f"Overpayment blocked for student {student_id}: {new_amount} > {final_fee}")
                self._set_last_error(
                    f"OVERPAYMENT: student_id={student_id}; attempted_total={new_amount}; final_fee={final_fee}"
                )
                return False

            # Sans seuil, ne jamais marquer "seuil atteint".
            is_eligible = 1 if (threshold_enabled and new_amount >= threshold) else 0
            now = datetime.now()

            query = """
                UPDATE finance_profile 
                SET amount_paid = %s, last_payment_date = %s, is_eligible = %s, updated_at = %s
                WHERE student_id = %s
            """
            params = (str(new_amount), now, is_eligible, now, student_id)
            self.db.execute_update(query, params)

            try:
                history_cols = self._get_table_columns("payment_history")
                amount_usd = amount
                insert_cols = []
                insert_vals = []

                def add_hist(name, value):
                    if name in history_cols:
                        insert_cols.append(name)
                        insert_vals.append(value)

                add_hist("student_id", student_id)
                add_hist("amount_paid_fc", str(amount_usd))
                add_hist("amount_paid_usd", str(amount_usd))
                add_hist("payment_method", "Paiement bancaire")
                add_hist("payment_reference", None)
                add_hist("created_at", now)

                if insert_cols:
                    placeholders = ", ".join(["%s"] * len(insert_cols))
                    cols_sql = ", ".join(insert_cols)
                    self.db.execute_update(
                        f"INSERT INTO payment_history ({cols_sql}) VALUES ({placeholders})",
                        tuple(insert_vals)
                    )
            except Exception as e:
                logger.error(f"Error inserting payment history: {e}")

            remaining_amount = final_fee - new_amount
            if remaining_amount < 0:
                remaining_amount = Decimal("0")

            def _notify_async():
                try:
                    logger.info(f"Starting async notification for student {student_id}")
                    if threshold_enabled and is_eligible:
                        is_full_paid = new_amount >= final_fee
                        self._issue_access_code_if_needed(student_id, is_full_paid)

                    success = self.notification_service.send_payment_notification(
                        student_email=promo.get('email'),
                        student_phone=promo.get('phone_number'),
                        student_name=f"{promo.get('firstname')} {promo.get('lastname')}",
                        amount_paid=float(new_amount),
                        remaining_amount=float(remaining_amount),
                        final_fee=float(final_fee),
                        threshold_amount=float(threshold) if threshold_enabled else None,
                        threshold_reached=bool(is_eligible) if threshold_enabled else None,
                        promotion_info=f"{faculty_name} / {department_name} / {promotion_name}"
                    )
                    if not success:
                        logger.error(f"Notification failed for student {student_id} - Email: {promo.get('email')}, Phone: {promo.get('phone_number')}")
                    else:
                        logger.info(f"Notification sent successfully for student {student_id}")
                except Exception as notify_err:
                    logger.error(f"Notification async error for student {student_id}: {notify_err}", exc_info=True)

            threading.Thread(target=_notify_async, daemon=True).start()

            logger.info(f"Payment recorded for student {student_id} ({promotion_name}): {amount}")
            self._set_last_error(None)
            return True
            
        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            self._set_last_error(f"PAYMENT_EXCEPTION: {e}")
            return False

    def get_student_payment_history(self, student_id: int, limit: int = 100) -> list:
        """Retourne l'historique des paiements d'un étudiant"""
        try:
            self._ensure_payment_history_table()
            query = """
                SELECT amount_paid_fc, amount_paid_usd, payment_method, payment_reference, created_at
                FROM payment_history
                WHERE student_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            return self.db.execute_query(query, (student_id, limit))
        except Exception as e:
            logger.error(f"Error fetching payment history: {e}")
            return []

    def get_latest_access_code(self, student_id: int) -> Optional[dict]:
        """Retourne le dernier code d'accès généré"""
        try:
            self._ensure_access_code_history_table()
            query = """
                SELECT access_code, access_type, expires_at, issued_at
                FROM access_code_history
                WHERE student_id = %s
                ORDER BY issued_at DESC
                LIMIT 1
            """
            results = self.db.execute_query(query, (student_id,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error fetching access code: {e}")
            return None

    def resend_latest_access_code_notification(self, student_id: int) -> bool:
        """Renvoie au contact de l'etudiant le dernier code d'acces encore valide."""
        try:
            self._set_last_error(None)
            latest = self.get_latest_access_code(student_id)
            if not latest:
                self._set_last_error(f"NO_ACCESS_CODE: student_id={student_id}")
                return False

            access_code = latest.get("access_code")
            code_type = str(latest.get("access_type") or "").strip().lower()
            expires_at = latest.get("expires_at")
            parsed_expires = self._coerce_datetime(expires_at)

            if parsed_expires and datetime.now() > parsed_expires:
                self._set_last_error(f"ACCESS_CODE_EXPIRED: student_id={student_id}")
                return False

            if not access_code or code_type not in {"full", "partial"}:
                self._set_last_error(f"INVALID_ACCESS_CODE: student_id={student_id}")
                return False

            ok = self._send_access_code_notification_for_student(
                student_id,
                access_code,
                code_type,
                parsed_expires or expires_at,
            )
            if not ok:
                self._set_last_error(f"ACCESS_CODE_NOTIFICATION_FAILED: student_id={student_id}")
                return False
            self._set_last_error(None)
            return True
        except Exception as e:
            logger.error(f"Error resending access code notification: {e}", exc_info=True)
            self._set_last_error(f"ACCESS_CODE_RESEND_EXCEPTION: {e}")
            return False

    def get_eligible_students(self) -> list:
        """Récupère tous les étudiants éligibles"""
        try:
            query = """
                SELECT s.*, f.amount_paid, f.threshold_required
                FROM student s
                JOIN finance_profile f ON s.id = f.student_id
                WHERE f.amount_paid >= f.threshold_required AND s.is_active = 1
            """
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error getting eligible students: {e}")
            return []
    
    def get_non_eligible_students(self) -> list:
        """Récupère tous les étudiants non éligibles"""
        try:
            query = """
                SELECT s.*, f.amount_paid, f.threshold_required
                FROM student s
                JOIN finance_profile f ON s.id = f.student_id
                WHERE f.amount_paid < f.threshold_required AND s.is_active = 1
            """
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error getting non-eligible students: {e}")
            return []

    def is_access_code_valid(self, student_id: int) -> bool:
        """Vérifie la validité du mot de passe d'accès"""
        try:
            finance = self.get_student_finance(student_id)
            if not finance:
                return False

            expires_at = finance.get('access_code_expires_at')
            access_type = finance.get('access_code_type')
            academic_year_id = finance.get('academic_year_id')

            if expires_at and isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)

            if expires_at and datetime.now() > expires_at:
                return False

            if access_type == 'full' and academic_year_id:
                if not self.academic_service.is_within_exam_period(academic_year_id):
                    return False

            return True
        except Exception as e:
            logger.error(f"Error checking access code validity: {e}")
            return False

    def update_financial_thresholds(self, academic_year_id: int, threshold_amount: Decimal,
                                   final_fee: Decimal, partial_valid_days: int) -> bool:
        """Met à jour le seuil et invalide les accès partiels"""
        try:
            # VALIDATION CRITIQUE : Le seuil ne peut JAMAIS dépasser les frais académiques
            if threshold_amount > final_fee:
                logger.error(f"Threshold ({threshold_amount}) cannot exceed final_fee ({final_fee})")
                return False
            
            now = datetime.now()
            old_threshold = None
            old_final_fee = None
            try:
                current = self.db.execute_query(
                    "SELECT threshold_amount, final_fee FROM academic_year WHERE academic_year_id = %s",
                    (academic_year_id,)
                )
                if current:
                    old_threshold = Decimal(str(current[0].get("threshold_amount") or 0))
                    old_final_fee = Decimal(str(current[0].get("final_fee") or 0))
            except Exception as e:
                logger.warning(f"Unable to load current thresholds: {e}")

            query_year = """
                UPDATE academic_year
                SET threshold_amount = %s, final_fee = %s, partial_valid_days = %s, updated_at = %s
                WHERE academic_year_id = %s
            """
            self.db.execute_update(query_year, (str(threshold_amount), str(final_fee), partial_valid_days, now, academic_year_id))

            # Mettre à jour finance_profile - vérifier si la colonne final_fee existe
            columns = self._get_table_columns("finance_profile")
            if "final_fee" in columns:
                query_fp = """
                    UPDATE finance_profile
                    SET threshold_required = %s, final_fee = %s, updated_at = %s
                    WHERE academic_year_id = %s
                """
                self.db.execute_update(query_fp, (str(threshold_amount), str(final_fee), now, academic_year_id))
            else:
                # Si final_fee n'existe pas, mettre à jour seulement threshold_required
                query_fp = """
                    UPDATE finance_profile
                    SET threshold_required = %s, updated_at = %s
                    WHERE academic_year_id = %s
                """
                self.db.execute_update(query_fp, (str(threshold_amount), now, academic_year_id))

            # Recalculer l'éligibilité selon le nouveau seuil (effet immédiat dans l'interface)
            if "is_eligible" in columns:
                query_elig = """
                    UPDATE finance_profile
                    SET is_eligible = CASE WHEN amount_paid >= %s THEN 1 ELSE 0 END,
                        updated_at = %s
                    WHERE academic_year_id = %s
                """
                self.db.execute_update(query_elig, (str(threshold_amount), now, academic_year_id))

            self._invalidate_partial_access_codes(academic_year_id)
            self._notify_threshold_change(
                academic_year_id,
                threshold_amount,
                final_fee,
                old_threshold,
                old_final_fee
            )

            logger.info("Financial thresholds updated and partial codes invalidated")
            return True
        except Exception as e:
            logger.error(f"Error updating thresholds: {e}")
            return False

    def _issue_access_code_if_needed(self, student_id: int, is_full_paid: bool) -> None:
        """Génère et délivre un nouveau mot de passe si éligible"""
        try:
            self._ensure_access_code_history_table()
            columns = self._get_table_columns("finance_profile")
            finance = self.get_student_finance(student_id)
            if not finance:
                return

            academic_year_id = finance.get('academic_year_id')
            access_type = 'full' if is_full_paid else 'partial'

            active_year = self.academic_service.get_active_year()
            if not active_year:
                return

            if access_type == 'full':
                expires_at = active_year.get('end_date')
            else:
                # Valide jusqu'à modification du seuil (pas d'expiration temps)
                expires_at = None

            # Ne pas régénérer inutilement un code déjà actif du même type.
            latest = self.get_latest_access_code(student_id)
            if latest:
                latest_type = str(latest.get('access_type') or '').strip().lower()
                latest_expires = latest.get('expires_at')

                latest_expires = self._coerce_datetime(latest_expires) or latest_expires

                still_valid = (latest_expires is None) or (datetime.now() <= latest_expires)
                if latest_type == access_type and still_valid:
                    logger.info(
                        "Access code already active for student %s (type=%s); resending notification",
                        student_id,
                        access_type,
                    )
                    self._send_access_code_notification_for_student(
                        student_id,
                        latest.get('access_code'),
                        access_type,
                        latest_expires,
                    )
                    return

            access_code = self._generate_access_code()
            password_hash = self.auth_service.password_hasher.hash_password(access_code)

            self.db.execute_update(
                "UPDATE student SET password_hash = %s WHERE id = %s",
                (password_hash, student_id)
            )

            now = datetime.now()
            update_fields = []
            params = []

            def add_field(name, value):
                if name in columns:
                    update_fields.append(f"{name} = %s")
                    params.append(value)

            add_field("access_code_issued_at", now)
            add_field("access_code_expires_at", expires_at)
            add_field("access_code_type", access_type)
            add_field("updated_at", now)

            if update_fields:
                query = f"UPDATE finance_profile SET {', '.join(update_fields)} WHERE student_id = %s"
                params.append(student_id)
                self.db.execute_update(query, tuple(params))

            try:
                self.db.execute_update(
                    """
                    INSERT INTO access_code_history (student_id, access_code, access_type, expires_at, issued_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (student_id, access_code, access_type, expires_at, now)
                )
            except Exception as e:
                logger.error(f"Error inserting access code history: {e}")

            self._send_access_code_notification_for_student(student_id, access_code, access_type, expires_at)
        except Exception as e:
            logger.error(f"Error issuing access code: {e}")

    def _send_access_code_notification_for_student(self, student_id: int, access_code: str, code_type: str, expires_at) -> bool:
        """Envoie le code d'acces existant au contact email/WhatsApp de l'etudiant."""
        try:
            if not access_code:
                logger.error("Cannot send empty access code for student %s", student_id)
                return False

            student_row = self.db.execute_query("SELECT * FROM student WHERE id = %s", (student_id,))
            if not student_row:
                logger.error("Cannot send access code: student %s not found", student_id)
                return False

            student = student_row[0]
            email = (student.get('email') or "").strip()
            phone = (student.get('phone_number') or "").strip()
            if not email and not phone:
                logger.error("Cannot send access code for student %s: missing email and phone", student_id)
                return False

            ok = self.notification_service.send_access_code_notification(
                student_email=email,
                student_phone=phone,
                student_name=f"{student.get('firstname')} {student.get('lastname')}".strip() or "Etudiant",
                access_code=access_code,
                code_type=code_type,
                expires_at=expires_at
            )
            if ok:
                logger.info(f"Code d'acces {code_type} envoye a {email or phone}")
            else:
                logger.error(f"Code d'acces {code_type} non envoye pour student_id={student_id} (email={email}, phone={phone})")
            return ok
        except Exception as e:
            logger.error(f"Error sending access code notification: {e}", exc_info=True)
            return False

    def _coerce_datetime(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo else value
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except Exception:
            return None

    def _invalidate_partial_access_codes(self, academic_year_id: int) -> None:
        """Expire tous les accès partiels après changement de seuil"""
        try:
            columns = self._get_table_columns("finance_profile")
            if "access_code_expires_at" not in columns or "access_code_type" not in columns:
                return
            now = datetime.now()
            query = """
                UPDATE finance_profile
                SET access_code_expires_at = %s, updated_at = %s
                WHERE academic_year_id = %s AND access_code_type = 'partial'
            """
            self.db.execute_update(query, (now, now, academic_year_id))
        except Exception as e:
            logger.error(f"Error invalidating partial access codes: {e}")

    def _notify_threshold_change(self, academic_year_id: int, threshold_amount: Decimal,
                                 final_fee: Decimal, old_threshold: Decimal = None,
                                 old_final_fee: Decimal = None) -> None:
        """Notifie les étudiants du changement de seuil"""
        try:
            columns = self._get_table_columns("finance_profile")
            has_final_fee = "final_fee" in columns
            select_final_fee = ", f.final_fee" if has_final_fee else ""
            query = f"""
                SELECT s.email, s.phone_number, s.firstname, s.lastname,
                       f.amount_paid, f.threshold_required{select_final_fee}
                FROM student s
                JOIN finance_profile f ON s.id = f.student_id
                WHERE f.academic_year_id = %s AND s.is_active = 1
            """
            students = self.db.execute_query(query, (academic_year_id,))
            for s in students:
                amount_paid = Decimal(str(s.get("amount_paid") or 0))
                total_due = s.get("final_fee") if has_final_fee else None
                if total_due is None or Decimal(str(total_due or 0)) <= 0:
                    total_due = final_fee
                total_due = Decimal(str(total_due or 0))

                if total_due <= 0 or amount_paid >= total_due:
                    continue

                threshold_reached = amount_paid >= threshold_amount
                remaining_amount = total_due - amount_paid
                if remaining_amount < 0:
                    remaining_amount = Decimal("0")

                self.notification_service.send_threshold_change_notification(
                    student_email=s.get('email'),
                    student_phone=s.get('phone_number'),
                    student_name=f"{s.get('firstname')} {s.get('lastname')}",
                    old_threshold=float(old_threshold) if old_threshold is not None else None,
                    new_threshold=float(threshold_amount),
                    old_final_fee=float(old_final_fee) if old_final_fee is not None else None,
                    new_final_fee=float(final_fee),
                    amount_paid=float(amount_paid),
                    remaining_amount=float(remaining_amount),
                    threshold_reached=bool(threshold_reached)
                )
        except Exception as e:
            logger.error(f"Error notifying threshold change: {e}")

    def _generate_access_code(self) -> str:
        """Génère un mot de passe numérique (6 chiffres) unique dans l'historique."""
        self._ensure_access_code_history_table()
        max_attempts = 20

        for _ in range(max_attempts):
            candidate = f"{random.randint(0, 999999):06d}"
            exists = self.db.execute_query(
                "SELECT 1 FROM access_code_history WHERE access_code = %s LIMIT 1",
                (candidate,),
            )
            if not exists:
                return candidate

        # Fallback robuste (ajoute composante temporelle millisecondes tout en restant 6 chiffres)
        suffix = int(datetime.now().strftime("%f")) % 1000
        return f"{random.randint(0, 999):03d}{suffix:03d}"
