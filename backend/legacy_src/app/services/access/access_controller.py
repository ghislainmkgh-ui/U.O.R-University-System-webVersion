"""Service de contrôle d'accès (logique principale)"""
import logging
from enum import Enum
from datetime import datetime
import numpy as np
from core.database.connection import DatabaseConnection
from core.models.access_log import AccessStatus, AccessLog
from app.services.auth.authentication_service import AuthenticationService
from app.services.auth.face_recognition_service import FaceRecognitionService
from app.services.finance.finance_service import FinanceService

logger = logging.getLogger(__name__)


class AccessController:
    """Service pour contrôler l'accès aux salles d'examen"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.auth_service = AuthenticationService()
        self.face_service = FaceRecognitionService()
        self.finance_service = FinanceService()
    
    def verify_access(self, student_number: str, password: str, 
                     face_image_path: str, access_point: str) -> dict:
        """
        Vérifie l'accès complet d'un étudiant (3 conditions)
        
        Args:
            student_number: Numéro d'étudiant
            password: Mot de passe saisi
            face_image_path: Chemin vers l'image du visage
            access_point: Nome du point d'accès (porte, terminal, etc.)
            
        Returns:
            Dictionnaire avec le résultat d'accès
        """
        result = {
            "access_granted": False,
            "reason": "Unknown error",
            "password_valid": False,
            "face_valid": False,
            "finance_valid": False,
            "student_id": None
        }
        
        try:
            # 1. Vérifier le mot de passe
            student = self.auth_service.authenticate_student(student_number, password)
            if not student:
                result["reason"] = "Invalid password"
                self._log_access(None, access_point, AccessStatus.DENIED_PASSWORD)
                return result
            
            result["password_valid"] = True
            result["student_id"] = student['id']
            
            # 2. Vérifier le visage
            student_face = self.db.execute_query(
                "SELECT face_encoding FROM student WHERE id = %s",
                (student['id'],)
            )
            if student_face and student_face[0].get('face_encoding'):
                stored_bytes = student_face[0]['face_encoding']
                stored_encoding = np.frombuffer(stored_bytes, dtype=np.float64)
                if not self.face_service.verify_face(face_image_path, stored_encoding):
                    result["reason"] = "Face recognition failed"
                    self._log_access(student['id'], access_point, AccessStatus.DENIED_FACE)
                    return result
            
            result["face_valid"] = True
            
            # 3. Vérifier le seuil financier
            if not self.finance_service.is_threshold_reached(student['id']):
                result["reason"] = "Financial threshold not reached"
                self._log_access(student['id'], access_point, AccessStatus.DENIED_FINANCE)
                return result
            
            result["finance_valid"] = True
            result["access_granted"] = True
            result["reason"] = "Access granted"
            
            # Enregistrer le succès
            self._log_access(student['id'], access_point, AccessStatus.GRANTED)
            logger.info(f"Access granted to student {student_number} at {access_point}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying access: {e}")
            result["reason"] = f"System error: {str(e)}"
            return result
    
    def _log_access(self, student_id: int, access_point: str, status: AccessStatus):
        """Enregistre une tentative d'accès dans les logs"""
        try:
            query = """
                INSERT INTO AccessLog (student_id, access_point, status, created_at)
                VALUES (%s, %s, %s, %s)
            """
            params = (student_id, access_point, status.value, datetime.now())
            self.db.execute_update(query, params)
        except Exception as e:
            logger.error(f"Error logging access: {e}")
    
    def get_access_logs(self, student_id: int = None, limit: int = 100) -> list:
        """Récupère les logs d'accès"""
        try:
            if student_id:
                query = """
                    SELECT * FROM AccessLog 
                    WHERE student_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                return self.db.execute_query(query, (student_id, limit))
            else:
                query = """
                    SELECT * FROM AccessLog
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                return self.db.execute_query(query, (limit,))
        except Exception as e:
            logger.error(f"Error getting access logs: {e}")
            return []
