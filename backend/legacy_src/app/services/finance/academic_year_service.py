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
            try:
                query = "SELECT academic_year_id, year_name FROM academic_year ORDER BY year_name DESC"
                rows = self.db.execute_query(query)
                return rows or []
            except Exception:
                query = "SELECT academic_year_id, name FROM academic_year ORDER BY name DESC"
                rows = self.db.execute_query(query)
                # Normaliser vers year_name pour l'UI
                normalized = []
                for row in rows or []:
                    normalized.append({
                        "academic_year_id": row.get("academic_year_id"),
                        "year_name": row.get("name")
                    })
                return normalized
        except Exception as e:
            logger.error(f"Error getting academic years: {e}")
            return []

    def get_years_financials(self) -> List[dict]:
        """Retourne les années académiques avec seuils/frais"""
        try:
            try:
                query = """
                    SELECT academic_year_id, year_name, threshold_amount, final_fee
                    FROM academic_year
                    ORDER BY year_name DESC
                """
                return self.db.execute_query(query) or []
            except Exception:
                query = """
                    SELECT academic_year_id, name, threshold_amount, final_fee
                    FROM academic_year
                    ORDER BY name DESC
                """
                rows = self.db.execute_query(query) or []
                normalized = []
                for row in rows:
                    normalized.append({
                        "academic_year_id": row.get("academic_year_id"),
                        "year_name": row.get("name"),
                        "threshold_amount": row.get("threshold_amount"),
                        "final_fee": row.get("final_fee")
                    })
                return normalized
        except Exception as e:
            logger.error(f"Error getting academic years financials: {e}")
            return []

    def get_year_by_id(self, academic_year_id: int) -> Optional[dict]:
        """Retourne une année académique par ID"""
        try:
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
                          final_fee: float = 500.0, partial_valid_days: int = 30) -> Optional[int]:
        """Crée une nouvelle année académique avec paramètres par défaut et retourne l'ID"""
        try:
            # Combiner INSERT et SELECT dans la même transaction
            insert_query = """
                INSERT INTO academic_year (year_name, threshold_amount, final_fee, partial_valid_days, is_active)
                VALUES (%s, %s, %s, %s, 1);
                SELECT LAST_INSERT_ID() as year_id;
            """
            
            # Pour MySQL, on doit faire les requêtes séparément mais dans la même session
            connection = self.db.get_connection()
            try:
                cursor = connection.cursor(dictionary=True)
                
                # Exécuter l'INSERT
                insert_cmd = "INSERT INTO academic_year (year_name, threshold_amount, final_fee, partial_valid_days, is_active) VALUES (%s, %s, %s, %s, 1)"
                cursor.execute(insert_cmd, (year_name, str(threshold_amount), str(final_fee), partial_valid_days))
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
