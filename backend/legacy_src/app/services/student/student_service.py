"""Service de gestion des étudiants"""
import json
import logging
import re
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from core.models.student import Student
from core.models.promotion import Promotion
from core.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class StudentService:
    """Service pour gérer les étudiants"""
    
    def __init__(self):
        self.db = DatabaseConnection()

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

    def _ensure_academic_year_migration_audit_table(self) -> None:
        """Crée la table d'audit des bascules annuelles si nécessaire."""
        try:
            query = """
                CREATE TABLE IF NOT EXISTS academic_year_migration_audit (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    actor_identifier VARCHAR(255) DEFAULT NULL,
                    actor_role VARCHAR(50) DEFAULT NULL,
                    from_academic_year_id INT NOT NULL,
                    to_academic_year_id INT NOT NULL,
                    eligible_only BOOLEAN DEFAULT FALSE,
                    moved_count INT DEFAULT 0,
                    eligible_count INT DEFAULT 0,
                    regenerated_full_count INT DEFAULT 0,
                    moved_student_ids_json LONGTEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created_at (created_at),
                    INDEX idx_from_year (from_academic_year_id),
                    INDEX idx_to_year (to_academic_year_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            self.db.execute_update(query)
        except Exception as e:
            logger.error(f"Error ensuring academic_year_migration_audit table: {e}")

    def log_academic_year_migration_audit(
        self,
        *,
        actor_identifier: str,
        actor_role: str,
        from_academic_year_id: int,
        to_academic_year_id: int,
        eligible_only: bool,
        moved_student_ids: list,
        eligible_student_ids: list = None,
        regenerated_full_count: int = 0,
    ) -> bool:
        """Journalise une bascule annuelle effectuée par un Super Admin."""
        try:
            self._ensure_academic_year_migration_audit_table()
            moved_student_ids = [int(x) for x in (moved_student_ids or [])]
            eligible_student_ids = [int(x) for x in (eligible_student_ids or [])]
            payload = json.dumps(moved_student_ids, ensure_ascii=False)

            query = """
                INSERT INTO academic_year_migration_audit (
                    actor_identifier,
                    actor_role,
                    from_academic_year_id,
                    to_academic_year_id,
                    eligible_only,
                    moved_count,
                    eligible_count,
                    regenerated_full_count,
                    moved_student_ids_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.db.execute_update(
                query,
                (
                    (actor_identifier or None),
                    (actor_role or None),
                    int(from_academic_year_id),
                    int(to_academic_year_id),
                    1 if eligible_only else 0,
                    len(moved_student_ids),
                    len(eligible_student_ids),
                    int(regenerated_full_count or 0),
                    payload,
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Error logging academic year migration audit: {e}", exc_info=True)
            return False

    def get_recent_academic_year_migration_audit(self, limit: int = 20) -> List[dict]:
        """Retourne les dernières bascules annuelles journalisées."""
        try:
            self._ensure_academic_year_migration_audit_table()
            safe_limit = max(1, min(int(limit), 100))
            query = f"""
                SELECT
                    a.id,
                    a.actor_identifier,
                    a.actor_role,
                    a.from_academic_year_id,
                    a.to_academic_year_id,
                    a.eligible_only,
                    a.moved_count,
                    a.eligible_count,
                    a.regenerated_full_count,
                    a.moved_student_ids_json,
                    a.created_at,
                    src.year_name AS from_year_name,
                    dst.year_name AS to_year_name
                FROM academic_year_migration_audit a
                LEFT JOIN academic_year src ON src.academic_year_id = a.from_academic_year_id
                LEFT JOIN academic_year dst ON dst.academic_year_id = a.to_academic_year_id
                ORDER BY a.created_at DESC, a.id DESC
                LIMIT {safe_limit}
            """
            return self.db.execute_query(query) or []
        except Exception as e:
            logger.error(f"Error fetching academic year migration audit: {e}")
            return []
    
    def create_student(self, student: Student) -> bool:
        """Crée un nouvel étudiant"""
        try:
            query = """
                INSERT INTO student (student_number, firstname, lastname, email, phone_number, promotion_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                student.student_number,
                student.firstname,
                student.lastname,
                student.email,
                student.phone_number,
                student.promotion_id
            )
            self.db.execute_update(query, params)
            logger.info(f"Student {student.student_number} created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating student: {e}")
            return False
    
    def get_student(self, student_number: str) -> Optional[dict]:
        """Récupère un étudiant par numéro"""
        try:
            query = "SELECT * FROM student WHERE student_number = %s"
            results = self.db.execute_query(query, (student_number,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting student: {e}")
            return None
    
    def get_students_by_promotion(self, promotion_id: int) -> List[dict]:
        """Récupère tous les étudiants d'une promotion"""
        try:
            query = "SELECT * FROM student WHERE promotion_id = %s AND is_active = 1"
            return self.db.execute_query(query, (promotion_id,))
        except Exception as e:
            logger.error(f"Error getting students by promotion: {e}")
            return []
    
    def get_students_by_department(self, department_id: int) -> List[dict]:
        """Récupère tous les étudiants d'un département via les promotions"""
        try:
            query = """
                SELECT s.* FROM student s
                JOIN promotion p ON s.promotion_id = p.id
                WHERE p.department_id = %s AND s.is_active = 1
            """
            return self.db.execute_query(query, (department_id,))
        except Exception as e:
            logger.error(f"Error getting students by department: {e}")
            return []
    
    def deactivate_student(self, student_number: str) -> bool:
        """Désactive un étudiant"""
        try:
            query = "UPDATE student SET is_active = 0 WHERE student_number = %s"
            self.db.execute_update(query, (student_number,))
            logger.info(f"Student {student_number} deactivated")
            return True
        except Exception as e:
            logger.error(f"Error deactivating student: {e}")
            return False

    def update_face_encoding(self, student_id: int, face_encoding: bytes) -> bool:
        """Met à jour l'encodage du visage d'un étudiant"""
        try:
            query = "UPDATE student SET face_encoding = %s WHERE id = %s"
            self.db.execute_update(query, (face_encoding, student_id))
            logger.info(f"Face encoding updated for student {student_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating face encoding: {e}")
            return False

    def get_all_students_with_finance(self) -> List[dict]:
        """Récupère tous les étudiants avec données financières
        
        NOUVELLE ARCHITECTURE: Inclut faculté, département et promotion pour chaque étudiant
        """
        try:
            student_cols = self._get_table_columns("student")
            year_cols = self._get_table_columns("academic_year")

            year_select = ""
            year_join = ""
            if "academic_year_id" in student_cols and year_cols:
                year_name_col = "year_name" if "year_name" in year_cols else "name"
                year_select = f", ay.{year_name_col} AS academic_year_name, s.academic_year_id"
                year_join = "LEFT JOIN academic_year ay ON ay.academic_year_id = s.academic_year_id"

            query = f"""
                SELECT 
                    s.id,
                    s.student_number,
                    s.firstname,
                    s.lastname,
                    s.email,
                    s.phone_number,
                    s.passport_photo_path,
                    s.passport_photo_blob,
                    s.promotion_id,
                    s.is_active,
                    fp.amount_paid,
                    fp.threshold_required,
                    fp.is_eligible,
                    p.name AS promotion_name,
                    p.year AS promotion_year,
                    p.fee_usd AS promotion_fee,
                    p.threshold_amount AS promotion_threshold,
                    d.id AS department_id,
                    d.name AS department_name,
                    d.code AS department_code,
                    f.id AS faculty_id,
                    f.name AS faculty_name,
                    f.code AS faculty_code
                    {year_select}
                FROM student s
                LEFT JOIN finance_profile fp ON fp.student_id = s.id
                LEFT JOIN promotion p ON s.promotion_id = p.id
                LEFT JOIN department d ON p.department_id = d.id
                LEFT JOIN faculty f ON d.faculty_id = f.id
                {year_join}
                WHERE s.is_active = 1
                ORDER BY f.name, d.name, p.name, s.lastname ASC, s.firstname ASC
            """
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error getting students list: {e}")
            return []

    def get_student_with_academics(self, student_id: int) -> Optional[dict]:
        """Récupère un étudiant avec faculté/département/promotion"""
        try:
            student_cols = self._get_table_columns("student")
            year_cols = self._get_table_columns("academic_year")
            year_select = ""
            year_join = ""
            if "academic_year_id" in student_cols and year_cols:
                year_name_col = "year_name" if "year_name" in year_cols else "name"
                year_select = f", ay.{year_name_col} AS academic_year_name, s.academic_year_id"
                year_join = "LEFT JOIN academic_year ay ON ay.academic_year_id = s.academic_year_id"

            query = f"""
                SELECT s.*, p.name AS promotion_name, p.year AS promotion_year,
                       d.name AS department_name, d.code AS department_code,
                       f.name AS faculty_name, f.code AS faculty_code
                       {year_select}
                FROM student s
                JOIN promotion p ON s.promotion_id = p.id
                JOIN department d ON p.department_id = d.id
                JOIN faculty f ON d.faculty_id = f.id
                {year_join}
                WHERE s.id = %s
            """
            results = self.db.execute_query(query, (student_id,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting student details: {e}")
            return None

    def update_student(self, student_id: int, data: dict) -> bool:
        """Met à jour les informations d'un étudiant"""
        try:
            allowed = {
                "student_number",
                "firstname",
                "lastname",
                "email",
                "phone_number",
                "promotion_id",
                "passport_photo_path",
                "passport_photo_blob",
                "academic_year_id",
            }
            fields = []
            params = []
            for key, value in data.items():
                if key in allowed:
                    fields.append(f"{key} = %s")
                    params.append(value)

            if not fields:
                logger.warning(f"No allowed fields to update for student {student_id}")
                return False

            query = f"UPDATE student SET {', '.join(fields)} WHERE id = %s"
            params.append(student_id)
            logger.debug(f"Update query: {query}")
            logger.debug(f"Update params: {params}")
            self.db.execute_update(query, tuple(params))
            logger.info(f"Student {student_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating student {student_id}: {type(e).__name__}: {e}", exc_info=True)
            return False

    def get_promotions(self) -> List[dict]:
        """Récupère les promotions actives"""
        try:
            query = "SELECT id, name, year, fee_usd FROM promotion WHERE is_active = 1 ORDER BY year DESC, name"
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error getting promotions: {e}")
            return []

    def get_promotions_with_fees(self) -> List[dict]:
        """Récupère les promotions avec frais académiques"""
        try:
            query = """
                SELECT p.id,
                       p.name,
                       p.year,
                       p.fee_usd,
                       p.threshold_amount,
                       d.name as department_name,
                       f.name as faculty_name,
                       f.code as faculty_code
                FROM promotion p
                JOIN department d ON p.department_id = d.id
                JOIN faculty f ON d.faculty_id = f.id
                WHERE p.is_active = 1
                ORDER BY f.name, d.name, p.year DESC, p.name
            """
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error getting promotions with fees: {e}")
            return []

    def update_promotion_fee(self, promotion_id: int, fee_usd: Decimal) -> bool:
        """Met à jour les frais académiques d'une promotion"""
        try:
            query = "UPDATE promotion SET fee_usd = %s, updated_at = NOW() WHERE id = %s"
            self.db.execute_update(query, (str(fee_usd), promotion_id))
            logger.info(f"Promotion {promotion_id} fee updated: {fee_usd}")
            return True
        except Exception as e:
            logger.error(f"Error updating promotion fee: {e}")
            return False

    def get_promotion_details(self, promotion_id: int) -> dict:
        """Récupère les détails d'une promotion"""
        try:
            query = """
                SELECT p.id, p.name, p.year, p.fee_usd, p.threshold_amount,
                       d.name as department_name, f.name as faculty_name
                FROM promotion p
                JOIN department d ON p.department_id = d.id
                JOIN faculty f ON d.faculty_id = f.id
                WHERE p.id = %s
            """
            result = self.db.execute_query(query, (promotion_id,))
            return result[0] if result else {}
        except Exception as e:
            logger.error(f"Error getting promotion details: {e}")
            return {}

    def update_promotion_financials(self, promotion_id: int, fee_usd: Decimal, threshold_amount: Decimal) -> bool:
        """Met à jour les frais académiques et le seuil d'une promotion"""
        try:
            query = """
                UPDATE promotion
                SET fee_usd = %s,
                    threshold_amount = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            self.db.execute_update(query, (str(fee_usd), str(threshold_amount), promotion_id))
            logger.info(f"Promotion {promotion_id} financials updated: fee={fee_usd}, threshold={threshold_amount}")
            return True
        except Exception as e:
            logger.error(f"Error updating promotion financials: {e}")
            return False

    def get_faculties(self) -> List[dict]:
        """Récupère les facultés actives"""
        try:
            query = "SELECT id, name, code FROM faculty WHERE is_active = 1 ORDER BY name"
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error getting faculties: {e}")
            return []

    def get_departments_by_faculty(self, faculty_id: int) -> List[dict]:
        """Récupère les départements actifs d'une faculté"""
        try:
            query = """
                SELECT id, name, code
                FROM department
                WHERE faculty_id = %s AND is_active = 1
                ORDER BY name
            """
            return self.db.execute_query(query, (faculty_id,))
        except Exception as e:
            logger.error(f"Error getting departments by faculty: {e}")
            return []

    def get_promotions_by_department(self, department_id: int) -> List[dict]:
        """Récupère les promotions actives d'un département"""
        try:
            query = """
                SELECT id, name, year
                FROM promotion
                WHERE department_id = %s AND is_active = 1
                ORDER BY year DESC, name
            """
            return self.db.execute_query(query, (department_id,))
        except Exception as e:
            logger.error(f"Error getting promotions by department: {e}")
            return []

    def _infer_code(self, value: str, max_len: int = 10) -> str:
        """Infère un code court à partir d'une saisie libre (sigle)."""
        raw = str(value or "").strip()
        if not raw:
            return "CODE"
        # Cherche un sigle déjà présent (ex: G.I, FSI)
        token = re.findall(r"[A-Za-z0-9\.]+", raw)
        token = token[0] if token else raw
        code = re.sub(r"[^A-Za-z0-9]", "", token).upper()
        if not code:
            code = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
        return code[:max_len] if code else "CODE"

    def _extract_year(self, value: str) -> int:
        """Extrait une année (4 chiffres) d'une saisie, sinon année en cours."""
        match = re.search(r"(20\d{2}|19\d{2})", str(value or ""))
        if match:
            return int(match.group(1))
        return datetime.now().year

    def create_faculty(self, name: str, code: Optional[str] = None) -> Optional[int]:
        """Crée une faculté si elle n'existe pas déjà"""
        try:
            code = code or self._infer_code(name)
            query = """
                INSERT INTO faculty (name, code, is_active)
                VALUES (%s, %s, 1)
            """
            self.db.execute_update(query, (name, code))
            result = self.db.execute_query("SELECT id FROM faculty WHERE code = %s", (code,))
            return result[0]["id"] if result else None
        except Exception as e:
            logger.error(f"Error creating faculty: {e}")
            result = self.db.execute_query(
                "SELECT id FROM faculty WHERE code = %s OR name = %s",
                (code, name)
            )
            return result[0]["id"] if result else None

    def create_department(self, name: str, faculty_id: int, code: Optional[str] = None) -> Optional[int]:
        """Crée un département si nécessaire"""
        try:
            code = code or self._infer_code(name)
            query = """
                INSERT INTO department (name, code, faculty_id, is_active)
                VALUES (%s, %s, %s, 1)
            """
            self.db.execute_update(query, (name, code, faculty_id))
            result = self.db.execute_query(
                "SELECT id FROM department WHERE code = %s AND faculty_id = %s",
                (code, faculty_id)
            )
            return result[0]["id"] if result else None
        except Exception as e:
            logger.error(f"Error creating department: {e}")
            result = self.db.execute_query(
                "SELECT id FROM department WHERE (code = %s OR name = %s) AND faculty_id = %s",
                (code, name, faculty_id)
            )
            return result[0]["id"] if result else None

    def create_promotion(self, name: str, department_id: int, year: Optional[int] = None) -> Optional[int]:
        """Crée une promotion si nécessaire"""
        try:
            year_value = int(year) if year else self._extract_year(name)
            query = """
                INSERT INTO promotion (name, year, department_id, is_active)
                VALUES (%s, %s, %s, 1)
            """
            self.db.execute_update(query, (name, year_value, department_id))
            result = self.db.execute_query(
                "SELECT id FROM promotion WHERE name = %s AND department_id = %s AND year = %s",
                (name, department_id, year_value)
            )
            return result[0]["id"] if result else None
        except Exception as e:
            logger.error(f"Error creating promotion: {e}")
            result = self.db.execute_query(
                "SELECT id FROM promotion WHERE name = %s AND department_id = %s",
                (name, department_id)
            )
            return result[0]["id"] if result else None

    def _normalize_key(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value or "").lower().strip())
    
    def _extract_keywords(self, value: str) -> set:
        """Extrait les mots-clés significatifs d'une chaîne"""
        normalized = str(value or "").lower()
        # Remplace les caractères spéciaux par des espaces
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        # Split et filtre les mots courts
        words = {w for w in normalized.split() if len(w) >= 2}
        return words

    def _match_by_normalized(self, items: List[dict], input_value: str, fields: List[str]) -> List[dict]:
        key = self._normalize_key(input_value)
        if not key:
            return []

        matches = []
        
        # 1. Match exact (normalisé)
        for item in items:
            for field in fields:
                if key == self._normalize_key(item.get(field)):
                    matches.append(item)
                    break

        if matches:
            return matches

        # 2. Match partiel (inclusion)
        for item in items:
            for field in fields:
                field_normalized = self._normalize_key(item.get(field))
                if key in field_normalized or field_normalized in key:
                    matches.append(item)
                    break

        if matches:
            return matches

        # 3. Match par mots-clés (au moins 50% des mots en commun)
        input_keywords = self._extract_keywords(input_value)
        if not input_keywords:
            return []
        
        scored_matches = []
        for item in items:
            for field in fields:
                field_keywords = self._extract_keywords(item.get(field))
                if field_keywords:
                    common = input_keywords & field_keywords
                    if common:
                        score = len(common) / max(len(input_keywords), len(field_keywords))
                        if score >= 0.3:  # Au moins 30% de mots en commun
                            scored_matches.append((score, item))
                            break
        
        if scored_matches:
            # Trier par score décroissant
            scored_matches.sort(reverse=True, key=lambda x: x[0])
            return [item for score, item in scored_matches]

        return []

    def find_faculty_by_input(self, input_value: str) -> List[dict]:
        """Recherche une faculté par nom ou code (saisie manuelle)"""
        faculties = self.get_faculties()
        return self._match_by_normalized(faculties, input_value, ["name", "code"])

    def find_department_by_input(self, input_value: str, faculty_id: Optional[int] = None) -> List[dict]:
        """Recherche un département par nom ou code"""
        try:
            if faculty_id:
                departments = self.get_departments_by_faculty(faculty_id)
            else:
                query = """
                    SELECT id, name, code, faculty_id
                    FROM department
                    WHERE is_active = 1
                    ORDER BY name
                """
                departments = self.db.execute_query(query)
            return self._match_by_normalized(departments, input_value, ["name", "code"])
        except Exception as e:
            logger.error(f"Error finding department by input: {e}")
            return []

    def find_promotion_by_input(self, input_value: str, department_id: Optional[int] = None) -> List[dict]:
        """Recherche une promotion par nom et/ou année"""
        try:
            if department_id:
                promotions = self.get_promotions_by_department(department_id)
            else:
                query = """
                    SELECT id, name, year, department_id
                    FROM promotion
                    WHERE is_active = 1
                    ORDER BY year DESC, name
                """
                promotions = self.db.execute_query(query)

            key = self._normalize_key(input_value)
            if not key:
                return []

            matches = []
            
            # 1. Match exact sur nom, nom+année ou variations
            for promo in promotions:
                name = promo.get("name")
                year = promo.get("year")
                if key == self._normalize_key(name):
                    matches.append(promo)
                    continue
                if key == self._normalize_key(f"{name}{year}"):
                    matches.append(promo)
                    continue
                if key == self._normalize_key(f"{name} {year}"):
                    matches.append(promo)
                    continue
                if key == self._normalize_key(f"{name}-{year}"):
                    matches.append(promo)
                    continue

            if matches:
                return matches

            # 2. Match partiel sur nom
            for promo in promotions:
                name = promo.get("name")
                name_normalized = self._normalize_key(name)
                if key in name_normalized or name_normalized in key:
                    matches.append(promo)

            if matches:
                return matches

            # 3. Match par mots-clés
            input_keywords = self._extract_keywords(input_value)
            if not input_keywords:
                return []
            
            scored_matches = []
            for promo in promotions:
                name = promo.get("name")
                year = str(promo.get("year") or "")
                combined = f"{name} {year}"
                field_keywords = self._extract_keywords(combined)
                if field_keywords:
                    common = input_keywords & field_keywords
                    if common:
                        score = len(common) / max(len(input_keywords), len(field_keywords))
                        if score >= 0.3:
                            scored_matches.append((score, promo))
            
            if scored_matches:
                scored_matches.sort(reverse=True, key=lambda x: x[0])
                return [item for score, item in scored_matches]

            return []
        except Exception as e:
            logger.error(f"Error finding promotion by input: {e}")
            return []

    def migrate_students_to_academic_year(
        self,
        from_academic_year_id: int,
        to_academic_year_id: int,
        eligible_only: bool = False,
        dry_run: bool = False,
    ) -> dict:
        """Bascule en lot des étudiants d'une année académique vers une autre.

        Met à jour :
        - student.academic_year_id
        - finance_profile.academic_year_id (si profil existant)

        Args:
            from_academic_year_id: année source
            to_academic_year_id: année cible
            eligible_only: si True, ne migre que les étudiants avec fp.is_eligible = 1
            dry_run: si True, calcule uniquement l'impact sans écrire en base

        Returns:
            dict avec compteurs et ids migrés.
        """
        try:
            if not from_academic_year_id or not to_academic_year_id:
                return {
                    "success": False,
                    "message": "Année source/cible invalide.",
                    "moved_count": 0,
                    "moved_student_ids": [],
                    "eligible_student_ids": [],
                }

            if int(from_academic_year_id) == int(to_academic_year_id):
                return {
                    "success": False,
                    "message": "L'année source et l'année cible sont identiques.",
                    "moved_count": 0,
                    "moved_student_ids": [],
                    "eligible_student_ids": [],
                }

            filters = [
                "COALESCE(s.is_active, 1) = 1",
                "s.academic_year_id = %s",
            ]
            params = [from_academic_year_id]

            if eligible_only:
                filters.append("COALESCE(fp.is_eligible, 0) = 1")

            query_candidates = f"""
                SELECT
                    s.id,
                    COALESCE(fp.is_eligible, 0) AS is_eligible
                FROM student s
                LEFT JOIN finance_profile fp ON fp.student_id = s.id
                WHERE {' AND '.join(filters)}
                ORDER BY s.id
            """
            candidates = self.db.execute_query(query_candidates, tuple(params)) or []

            if not candidates:
                return {
                    "success": True,
                    "message": "Aucun étudiant à migrer.",
                    "moved_count": 0,
                    "moved_student_ids": [],
                    "eligible_student_ids": [],
                    "dry_run": bool(dry_run),
                }

            moved_student_ids = [int(r["id"]) for r in candidates if r.get("id") is not None]
            eligible_student_ids = [int(r["id"]) for r in candidates if int(r.get("is_eligible") or 0) == 1]

            if dry_run:
                return {
                    "success": True,
                    "message": "Prévisualisation calculée.",
                    "moved_count": len(moved_student_ids),
                    "moved_student_ids": moved_student_ids,
                    "eligible_student_ids": eligible_student_ids,
                    "dry_run": True,
                }

            # Écriture transactionnelle en lots pour rester rapide et sûre
            finance_cols = self._get_table_columns("finance_profile")
            has_fp = bool(finance_cols)
            student_cols = self._get_table_columns("student")
            has_student_updated = "updated_at" in student_cols

            connection = self.db.get_connection()
            cursor = connection.cursor()
            try:
                connection.start_transaction()
                chunk_size = 500

                for i in range(0, len(moved_student_ids), chunk_size):
                    chunk = moved_student_ids[i:i + chunk_size]
                    placeholders = ",".join(["%s"] * len(chunk))

                    if has_student_updated:
                        query_update_students = f"""
                            UPDATE student
                            SET academic_year_id = %s,
                                updated_at = NOW()
                            WHERE id IN ({placeholders})
                        """
                        cursor.execute(query_update_students, (to_academic_year_id, *chunk))
                    else:
                        query_update_students = f"""
                            UPDATE student
                            SET academic_year_id = %s
                            WHERE id IN ({placeholders})
                        """
                        cursor.execute(query_update_students, (to_academic_year_id, *chunk))

                    if has_fp:
                        # Réinscription réelle: remettre la situation financière à zéro
                        # et recalculer seuil/frais depuis la promotion courante.
                        set_parts = ["fp.academic_year_id = %s"]
                        params = [to_academic_year_id]

                        if "amount_paid" in finance_cols:
                            set_parts.append("fp.amount_paid = 0")
                        if "is_eligible" in finance_cols:
                            set_parts.append("fp.is_eligible = 0")
                        if "last_payment_date" in finance_cols:
                            set_parts.append("fp.last_payment_date = NULL")
                        if "threshold_required" in finance_cols:
                            set_parts.append("fp.threshold_required = COALESCE(p.threshold_amount, 0)")
                        if "final_fee" in finance_cols:
                            set_parts.append("fp.final_fee = COALESCE(p.fee_usd, 0)")

                        # Invalider toute trace d'ancien code côté profil
                        if "access_code_type" in finance_cols:
                            set_parts.append("fp.access_code_type = NULL")
                        if "access_code_issued_at" in finance_cols:
                            set_parts.append("fp.access_code_issued_at = NULL")
                        if "access_code_expires_at" in finance_cols:
                            set_parts.append("fp.access_code_expires_at = NULL")
                        if "updated_at" in finance_cols:
                            set_parts.append("fp.updated_at = NOW()")

                        query_update_finance = f"""
                            UPDATE finance_profile fp
                            JOIN student s ON s.id = fp.student_id
                            LEFT JOIN promotion p ON p.id = s.promotion_id
                            SET {', '.join(set_parts)}
                            WHERE fp.student_id IN ({placeholders})
                        """
                        cursor.execute(query_update_finance, (*params, *chunk))

                    # Invalider tous les anciens codes d'accès des étudiants migrés.
                    # Règle métier: année cible = nouvelle inscription => nouveaux paiements => nouveaux codes.
                    query_delete_codes = f"""
                        DELETE FROM access_code_history
                        WHERE student_id IN ({placeholders})
                    """
                    cursor.execute(query_delete_codes, tuple(chunk))

                    # Optionnel: supprimer aussi le hash mot de passe dérivé des anciens codes
                    query_clear_pwd = f"""
                        UPDATE student
                        SET password_hash = NULL
                        WHERE id IN ({placeholders})
                    """
                    cursor.execute(query_clear_pwd, tuple(chunk))

                connection.commit()
            except Exception:
                try:
                    connection.rollback()
                except Exception:
                    pass
                raise
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
                try:
                    if connection and connection.is_connected():
                        connection.close()
                except Exception:
                    pass

            logger.info(
                "Academic year migration completed: from=%s to=%s moved=%s eligible=%s",
                from_academic_year_id,
                to_academic_year_id,
                len(moved_student_ids),
                len(eligible_student_ids),
            )

            return {
                "success": True,
                "message": "Migration effectuée.",
                "moved_count": len(moved_student_ids),
                "moved_student_ids": moved_student_ids,
                "eligible_student_ids": eligible_student_ids,
                "dry_run": False,
            }
        except Exception as e:
            logger.error(f"Error migrating students academic year: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Erreur migration: {e}",
                "moved_count": 0,
                "moved_student_ids": [],
                "eligible_student_ids": [],
                "dry_run": bool(dry_run),
            }
