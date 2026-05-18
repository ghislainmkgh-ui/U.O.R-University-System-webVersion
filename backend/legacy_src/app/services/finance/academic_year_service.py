"""Service de gestion de l'année académique et périodes d'examens"""
import logging
from datetime import datetime, date
from typing import Optional, List
from core.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class AcademicYearService:
    """Service pour configurer les seuils et périodes d'examens"""

    def __init__(self):
        self.db = DatabaseConnection()

    def get_active_year(self) -> Optional[dict]:
        """Retourne l'année académique active"""
        try:
            self._ensure_year_columns()
            try:
                query = "SELECT * FROM academic_year WHERE is_active = 1 ORDER BY start_date DESC LIMIT 1"
                rows = self.db.execute_query(query)
                return rows[0] if rows else None
            except Exception:
                query = "SELECT * FROM academic_year WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"
                rows = self.db.execute_query(query)
                return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Error getting active academic year: {e}")
            return None

    def get_years(self) -> List[dict]:
        """Retourne la liste des années académiques"""
        try:
            self._ensure_year_columns()
            try:
                query = """
                    SELECT academic_year_id,
                           year_name,
                           start_date,
                           end_date,
                           threshold_amount,
                           final_fee,
                           partial_valid_days,
                           is_active,
                           created_at,
                           updated_at
                    FROM academic_year
                    ORDER BY year_name DESC
                """
                rows = self.db.execute_query(query)
                return rows or []
            except Exception:
                query = """
                    SELECT academic_year_id,
                           name,
                           start_date,
                           end_date,
                           threshold_amount,
                           final_fee,
                           partial_valid_days,
                           is_active,
                           created_at,
                           updated_at
                    FROM academic_year
                    ORDER BY name DESC
                """
                rows = self.db.execute_query(query)
                # Normaliser vers year_name pour l'UI
                normalized = []
                for row in rows or []:
                    normalized.append({
                        "academic_year_id": row.get("academic_year_id"),
                        "year_name": row.get("name"),
                        "start_date": row.get("start_date"),
                        "end_date": row.get("end_date"),
                        "threshold_amount": row.get("threshold_amount"),
                        "final_fee": row.get("final_fee"),
                        "partial_valid_days": row.get("partial_valid_days"),
                        "is_active": row.get("is_active"),
                        "created_at": row.get("created_at"),
                        "updated_at": row.get("updated_at"),
                    })
                return normalized
        except Exception as e:
            logger.error(f"Error getting academic years: {e}")
            return []

    def get_years_financials(self) -> List[dict]:
        """Retourne les années académiques avec seuils/frais"""
        try:
            self._ensure_year_columns()
            try:
                query = """
                    SELECT academic_year_id,
                           year_name,
                           start_date,
                           end_date,
                           threshold_amount,
                           final_fee,
                           partial_valid_days,
                           is_active,
                           created_at,
                           updated_at
                    FROM academic_year
                    ORDER BY year_name DESC
                """
                return self.db.execute_query(query) or []
            except Exception:
                query = """
                    SELECT academic_year_id,
                           name,
                           start_date,
                           end_date,
                           threshold_amount,
                           final_fee,
                           partial_valid_days,
                           is_active,
                           created_at,
                           updated_at
                    FROM academic_year
                    ORDER BY name DESC
                """
                rows = self.db.execute_query(query) or []
                normalized = []
                for row in rows:
                    normalized.append({
                        "academic_year_id": row.get("academic_year_id"),
                        "year_name": row.get("name"),
                        "start_date": row.get("start_date"),
                        "end_date": row.get("end_date"),
                        "threshold_amount": row.get("threshold_amount"),
                        "final_fee": row.get("final_fee"),
                        "partial_valid_days": row.get("partial_valid_days"),
                        "is_active": row.get("is_active"),
                        "created_at": row.get("created_at"),
                        "updated_at": row.get("updated_at"),
                    })
                return normalized
        except Exception as e:
            logger.error(f"Error getting academic years financials: {e}")
            return []

    def get_year_by_id(self, academic_year_id: int) -> Optional[dict]:
        """Retourne une année académique par ID"""
        try:
            self._ensure_year_columns()
            query = "SELECT * FROM academic_year WHERE academic_year_id = %s"
            rows = self.db.execute_query(query, (academic_year_id,))
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Error getting academic year by id: {e}")
            return None

    def create_year(self, name: str, start_date: date, end_date: date,
                    threshold_amount: float, final_fee: float, partial_valid_days: int) -> bool:
        """Crée une nouvelle année académique et l'active"""
        try:
            self.db.execute_update("UPDATE academic_year SET is_active = 0 WHERE is_active = 1")
            query = """
                INSERT INTO academic_year (name, start_date, end_date, threshold_amount, final_fee, partial_valid_days, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.db.execute_update(query, (
                name, start_date, end_date, threshold_amount, final_fee, partial_valid_days, 1
            ))
            return True
        except Exception as e:
            logger.error(f"Error creating academic year: {e}")
            return False

    def create_year_simple(self, year_name: str, threshold_amount: float = 300.0, 
                          final_fee: float = 500.0, partial_valid_days: int = 30,
                          is_active: bool = True, start_date: date = None,
                          end_date: date = None) -> Optional[int]:
        """Crée une nouvelle année académique avec paramètres par défaut et retourne l'ID"""
        try:
            # Pour MySQL, on doit faire les requêtes séparément mais dans la même session
            self._ensure_year_columns()
            connection = self.db.get_connection()
            try:
                cursor = connection.cursor(dictionary=True)
                if is_active:
                    cursor.execute("UPDATE academic_year SET is_active = 0 WHERE is_active = 1")
                
                # Exécuter l'INSERT
                insert_cmd = "INSERT INTO academic_year (year_name, start_date, end_date, threshold_amount, final_fee, partial_valid_days, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(insert_cmd, (year_name, start_date, end_date, str(threshold_amount), str(final_fee), partial_valid_days, 1 if is_active else 0))
                connection.commit()
                
                # Récupérer l'ID inséré dans la MÊME session
                cursor.execute("SELECT LAST_INSERT_ID() as year_id")
                result = cursor.fetchall()
                
                if result and result[0].get('year_id'):
                    year_id = result[0]['year_id']
                    logger.info(f"Academic year '{year_name}' created with ID {year_id}")
                    return year_id
                
                # Fallback: chercher par le nom de l'année
                cursor.execute("SELECT academic_year_id FROM academic_year WHERE year_name = %s", (year_name,))
                result = cursor.fetchall()
                if result:
                    return result[0]['academic_year_id']
                    
                return None
            finally:
                cursor.close()
                if connection.is_connected():
                    connection.close()
                    
        except Exception as e:
            logger.error(f"Error creating academic year '{year_name}': {e}")
            return None

    def update_year_metadata(
        self,
        academic_year_id: int,
        year_name: str = None,
        is_active: Optional[bool] = None,
        start_date: date = None,
        end_date: date = None,
        start_date_provided: bool = False,
        end_date_provided: bool = False,
    ) -> bool:
        """Met a jour le nom et le statut actif d'une annee academique."""
        try:
            self._ensure_year_columns()
            columns = self._get_table_columns("academic_year")
            name_column = "year_name" if "year_name" in columns else "name"
            fields = []
            params = []

            if year_name is not None:
                fields.append(f"{name_column} = %s")
                params.append(year_name)

            if start_date_provided and "start_date" in columns:
                fields.append("start_date = %s")
                params.append(start_date)

            if end_date_provided and "end_date" in columns:
                fields.append("end_date = %s")
                params.append(end_date)

            if is_active is not None:
                if is_active:
                    self.db.execute_update(
                        "UPDATE academic_year SET is_active = 0 WHERE academic_year_id <> %s",
                        (academic_year_id,),
                    )
                fields.append("is_active = %s")
                params.append(1 if is_active else 0)

            if "updated_at" in columns:
                fields.append("updated_at = %s")
                params.append(datetime.now())

            if not fields:
                return True

            query = f"UPDATE academic_year SET {', '.join(fields)} WHERE academic_year_id = %s"
            params.append(academic_year_id)
            self.db.execute_update(query, tuple(params))
            return True
        except Exception as e:
            logger.error(f"Error updating academic year {academic_year_id}: {e}")
            return False

    def _ensure_year_columns(self) -> None:
        columns = self._get_table_columns("academic_year")
        try:
            if "start_date" not in columns:
                anchor = "year_name" if "year_name" in columns else "name"
                self.db.execute_update(f"ALTER TABLE academic_year ADD COLUMN start_date DATE NULL AFTER {anchor}")
            if "end_date" not in columns:
                self.db.execute_update("ALTER TABLE academic_year ADD COLUMN end_date DATE NULL AFTER start_date")
        except Exception as e:
            logger.warning(f"Unable to ensure academic year date columns: {e}")

    def _get_table_columns(self, table_name: str) -> set:
        try:
            rows = self.db.execute_query(f"SHOW COLUMNS FROM {table_name}") or []
            return {row.get("Field") for row in rows if row.get("Field")}
        except Exception as e:
            logger.warning(f"Unable to inspect table {table_name}: {e}")
            return set()

    def add_exam_period(self, academic_year_id: int, name: str, start_date: date, end_date: date) -> bool:
        """Ajoute une période d'examen"""
        try:
            query = """
                INSERT INTO exam_period (academic_year_id, period_name, start_date, end_date)
                VALUES (%s, %s, %s, %s)
            """
            self.db.execute_update(query, (academic_year_id, name, start_date, end_date))
            logger.info(f"Exam period '{name}' added for year {academic_year_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding exam period: {e}")
            return False

    def get_exam_periods(self, academic_year_id: int) -> List[dict]:
        """Liste des périodes d'examen"""
        try:
            query = """
                SELECT * FROM exam_period
                WHERE academic_year_id = %s
                ORDER BY start_date ASC
            """
            return self.db.execute_query(query, (academic_year_id,))
        except Exception as e:
            logger.error(f"Error getting exam periods: {e}")
            return []

    def delete_exam_period(self, period_id: int) -> bool:
        """Supprime une période d'examen"""
        try:
            query = "DELETE FROM exam_period WHERE exam_period_id = %s"
            self.db.execute_update(query, (period_id,))
            logger.info(f"Exam period {period_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting exam period: {e}")
            return False

    def is_within_exam_period(self, academic_year_id: int, when: Optional[datetime] = None) -> bool:
        """Vérifie si la date courante est dans une période d'examen"""
        try:
            when = when or datetime.now()
            query = """
                SELECT COUNT(*) as cnt
                FROM exam_period
                WHERE academic_year_id = %s
                  AND %s BETWEEN start_date AND end_date
            """
            rows = self.db.execute_query(query, (academic_year_id, when))
            return bool(rows and rows[0].get("cnt"))
        except Exception as e:
            logger.error(f"Error checking exam period: {e}")
            return False
