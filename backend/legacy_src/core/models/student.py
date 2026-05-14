"""Modèle Étudiant"""
from core.models.base_model import BaseModel


class Student(BaseModel):
    """Modèle pour les Étudiants"""
    
    def __init__(self, student_number: str, firstname: str, lastname: str, 
                 email: str, promotion_id: int, phone_number: str = None,
                 passport_photo_path: str = None, passport_photo_blob: bytes = None,
                 academic_year_id: int = None):
        super().__init__()
        self.id: int = None
        self.student_number: str = student_number
        self.firstname: str = firstname
        self.lastname: str = lastname
        self.email: str = email
        self.phone_number: str = phone_number
        self.promotion_id: int = promotion_id
        self.passport_photo_path: str = passport_photo_path
        self.passport_photo_blob: bytes = passport_photo_blob
        self.academic_year_id: int = academic_year_id
        self.password_hash: str = None
        self.face_encoding: bytes = None
        self.is_active: bool = True
    
    @property
    def fullname(self) -> str:
        """Retourne le nom complet de l'étudiant"""
        return f"{self.firstname} {self.lastname}"
