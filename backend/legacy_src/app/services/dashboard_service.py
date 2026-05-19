"""Service pour charger les données académiques du dashboard - Logique U.O.R"""
import logging
from datetime import datetime, timedelta
from core.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class DashboardService:
    """Service pour récupérer les statistiques académiques selon la structure U.O.R"""
    
    def __init__(self):
        try:
            self.db_connection = DatabaseConnection()
            logger.info("[Dashboard] Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"[Dashboard] Database connection error: {str(e)[:100]}")
            self.db_connection = None
    
    def get_total_students(self) -> int:
        """Récupère le nombre total d'étudiants actifs"""
        if not self.db_connection:
            return 0
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor()
            cursor.execute("SELECT COUNT(*) FROM student WHERE COALESCE(is_active, 1) = 1")
            result = cursor.fetchone()
            cursor.close()
            db.close()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Erreur total_students: {e}")
            return 0
    
    def get_eligible_students(self) -> int:
        """Récupère le nombre d'étudiants éligibles aux examens"""
        if not self.db_connection:
            return 0
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT pf.student_id)
                FROM student e
                LEFT JOIN finance_profile pf ON pf.student_id = e.id
                WHERE COALESCE(e.is_active, 1) = 1 AND COALESCE(pf.is_eligible, 0) = 1
            """)
            result = cursor.fetchone()
            cursor.close()
            db.close()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Erreur eligible_students: {e}")
            return 0
    
    def get_non_eligible_students(self) -> int:
        """Récupère le nombre d'étudiants non éligibles"""
        if not self.db_connection:
            return 0
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT e.id)
                FROM student e
                LEFT JOIN finance_profile pf ON pf.student_id = e.id
                WHERE COALESCE(e.is_active, 1) = 1 AND COALESCE(pf.is_eligible, 0) = 0
            """)
            result = cursor.fetchone()
            cursor.close()
            db.close()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Erreur non_eligible_students: {e}")
            return 0
    
    def get_access_granted(self) -> int:
        """Nombre d'accès accordés (dernières 24h)"""
        if not self.db_connection:
            return 0
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM access_log
                WHERE status = 'GRANTED' AND DATE(created_at) = CURDATE()
            """)
            result = cursor.fetchone()
            cursor.close()
            db.close()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Erreur access_granted: {e}")
            return 0
    
    def get_access_denied(self) -> int:
        """Nombre d'accès refusés (dernières 24h)"""
        if not self.db_connection:
            return 0
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM access_log
                WHERE status <> 'GRANTED' AND DATE(created_at) = CURDATE()
            """)
            result = cursor.fetchone()
            cursor.close()
            db.close()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Erreur access_denied: {e}")
            return 0
    
    def get_revenue_collected(self) -> float:
        """Montant total collecté auprès des étudiants"""
        if not self.db_connection:
            return 0.0
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(pf.amount_paid), 0)
                FROM finance_profile pf
                WHERE pf.amount_paid > 0
            """)
            result = cursor.fetchone()
            cursor.close()
            db.close()
            return float(result[0]) if result else 0.0
        except Exception as e:
            logger.error(f"Erreur revenue: {e}")
            return 0.0
    
    def get_recent_activities(self, limit: int = 8) -> list:
        """Récupère les activités récentes d'accès"""
        if not self.db_connection:
            return []
        try:
            safe_limit = max(1, min(int(limit), 50))
            db = self.db_connection.get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT 
                    CONCAT(e.firstname, ' ', e.lastname) as student_name,
                    e.student_number,
                    CASE WHEN al.status = 'granted' THEN 'Acces accordé'
                         ELSE 'Acces refusé' END as action,
                    al.created_at as timestamp,
                    al.status
                FROM access_log al
                JOIN student e ON al.student_id = e.id
                ORDER BY al.created_at DESC
                LIMIT {safe_limit}
            """)
            results = cursor.fetchall()
            activities = []
            for row in results:
                activities.append({
                    "type": "access",
                    "student": row['student_name'],
                    "id": row['student_number'],
                    "action": row['action'],
                    "timestamp": row['timestamp'],
                    "status": "granted" if row['status'] == 'granted' else "denied"
                })
            cursor.close()
            db.close()
            return activities
        except Exception as e:
            logger.error(f"Erreur recent_activities: {e}")
            return []
    
    def get_degree_of_completion(self) -> dict:
        """Récupère le taux de complétion des profils financiers"""
        if not self.db_connection:
            return {"total": 0, "eligible": 0, "percentage": 0}
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT e.id) as total,
                    SUM(CASE WHEN COALESCE(pf.is_eligible, 0) = 1 THEN 1 ELSE 0 END) as eligible
                FROM student e
                LEFT JOIN finance_profile pf ON pf.student_id = e.id
                WHERE COALESCE(e.is_active, 1) = 1
            """)
            result = cursor.fetchone()
            cursor.close()
            db.close()
            if result and result[0] > 0:
                total = result[0]
                eligible = result[1] or 0
                percentage = (eligible / total) * 100
                return {"total": total, "eligible": eligible, "percentage": percentage}
            return {"total": 0, "eligible": 0, "percentage": 0}
        except Exception as e:
            logger.error(f"Erreur completion: {e}")
            return {"total": 0, "eligible": 0, "percentage": 0}
    
    def get_faculty_stats(self) -> list:
        """Récupère les statistiques par faculté et département"""
        if not self.db_connection:
            return []
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    f.name as faculty_name,
                    d.name as department_name,
                    COUNT(DISTINCT e.id) as total_students,
                    SUM(CASE WHEN pf.is_eligible = 1 THEN 1 ELSE 0 END) as eligible_students
                FROM faculty f
                LEFT JOIN department d ON f.id = d.faculty_id
                LEFT JOIN promotion p ON d.id = p.department_id
                LEFT JOIN student e ON p.id = e.promotion_id AND e.is_active = 1
                LEFT JOIN finance_profile pf ON e.id = pf.student_id
                GROUP BY f.id, f.name, d.id, d.name
                ORDER BY f.name, d.name
            """)
            result = cursor.fetchall() or []
            cursor.close()
            db.close()
            return result
        except Exception as e:
            logger.error(f"Erreur faculty_stats: {e}")
            return []
    
    def get_students_by_payment_status(self) -> dict:
        """Récupère les étudiants par statut de paiement"""
        if not self.db_connection:
            return {"never_paid": 0, "partial_paid": 0, "eligible": 0}
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor()

            # Jamais payé (inclut les étudiants sans finance_profile)
            cursor.execute("""
                SELECT COUNT(DISTINCT s.id)
                FROM student s
                LEFT JOIN finance_profile fp ON fp.student_id = s.id
                WHERE s.is_active = 1 
                AND (fp.amount_paid IS NULL OR fp.amount_paid = 0)
            """)
            never_paid = cursor.fetchone()[0]

            # Partiellement payé
            cursor.execute("""
                SELECT COUNT(DISTINCT s.id)
                FROM student s
                INNER JOIN finance_profile fp ON fp.student_id = s.id
                WHERE s.is_active = 1
                AND fp.amount_paid > 0 
                AND (fp.is_eligible IS NULL OR fp.is_eligible = 0)
            """)
            partial_paid = cursor.fetchone()[0]

            # Éligible
            cursor.execute("""
                SELECT COUNT(DISTINCT s.id)
                FROM student s
                INNER JOIN finance_profile fp ON fp.student_id = s.id
                WHERE s.is_active = 1
                AND fp.is_eligible = 1
            """)
            eligible = cursor.fetchone()[0]

            cursor.close()
            db.close()

            return {
                "never_paid": never_paid,
                "partial_paid": partial_paid,
                "eligible": eligible
            }
        except Exception as e:
            logger.error(f"Erreur payment_status: {e}")
            return {"never_paid": 0, "partial_paid": 0, "eligible": 0}

    def get_students_finance_overview(self, limit: int = 200) -> list:
        """Liste des étudiants avec synthèse financière et photo"""
        if not self.db_connection:
            return []
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT
                    s.id,
                    s.student_number,
                    s.firstname,
                    s.lastname,
                    s.email,
                    f.id AS faculty_id,
                    f.name AS faculty_name,
                    d.id AS department_id,
                    d.name AS department_name,
                    p.id AS promotion_id,
                    p.name AS promotion_name,
                    COALESCE(p.fee_usd, 0) AS promotion_fee,
                    s.passport_photo_path,
                    s.passport_photo_blob,
                    fp.amount_paid,
                    fp.threshold_required,
                    fp.last_payment_date,
                    fp.is_eligible
                FROM student s
                LEFT JOIN promotion p ON p.id = s.promotion_id
                LEFT JOIN department d ON d.id = p.department_id
                LEFT JOIN faculty f ON f.id = d.faculty_id
                LEFT JOIN finance_profile fp ON fp.student_id = s.id
                WHERE s.is_active = 1
                ORDER BY f.name ASC, d.name ASC, p.name ASC, s.lastname ASC, s.firstname ASC, s.student_number ASC
                LIMIT {limit}
            """)
            rows = cursor.fetchall() or []
            cursor.close()
            db.close()
            return rows
        except Exception as e:
            logger.error(f"Erreur finance_overview: {e}")
            return []

    def get_access_logs_with_students(self, limit: int = 200, academic_year_id: int = None) -> list:
        """Liste des logs d'accès avec photo étudiant"""
        if not self.db_connection:
            return []
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor(dictionary=True)
            try:
                safe_limit = max(1, min(5000, int(limit)))
            except Exception:
                safe_limit = 200
            where_clauses = []
            params = []
            if academic_year_id:
                where_clauses.append("s.academic_year_id = %s")
                params.append(int(academic_year_id))
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            cursor.execute(f"""
                SELECT
                    s.id,
                    s.student_number,
                    s.firstname,
                    s.lastname,
                    s.academic_year_id,
                    ay.year_name AS academic_year_name,
                    s.passport_photo_path,
                    s.passport_photo_blob,
                    al.access_point,
                    al.status,
                    al.password_validated,
                    al.face_validated,
                    al.finance_validated,
                    al.created_at
                FROM access_log al
                JOIN student s ON al.student_id = s.id
                LEFT JOIN academic_year ay ON ay.academic_year_id = s.academic_year_id
                {where_sql}
                ORDER BY al.created_at DESC
                LIMIT {safe_limit}
            """, tuple(params))
            rows = cursor.fetchall() or []
            cursor.close()
            db.close()
            return rows
        except Exception as e:
            logger.error(f"Erreur access_logs: {e}")
            return []

    def get_faculty_stats_with_photos(self) -> list:
        """Stats par faculté/département avec photo échantillon"""
        if not self.db_connection:
            return []
        try:
            db = self.db_connection.get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    f.name as faculty_name,
                    d.name as department_name,
                    COUNT(DISTINCT e.id) as total_students,
                    SUM(CASE WHEN pf.is_eligible = 1 THEN 1 ELSE 0 END) as eligible_students,
                    COALESCE(SUM(pf.amount_paid), 0) as revenue,
                    MAX(e.passport_photo_path) as passport_photo_path,
                    MAX(e.passport_photo_blob) as passport_photo_blob
                FROM faculty f
                LEFT JOIN department d ON f.id = d.faculty_id
                LEFT JOIN promotion p ON d.id = p.department_id
                LEFT JOIN student e ON p.id = e.promotion_id AND e.is_active = 1
                LEFT JOIN finance_profile pf ON e.id = pf.student_id
                GROUP BY f.id, f.name, d.id, d.name
                ORDER BY f.name, d.name
            """)
            rows = cursor.fetchall() or []
            cursor.close()
            db.close()
            return rows
        except Exception as e:
            logger.error(f"Erreur faculty_stats_photos: {e}")
            return []
