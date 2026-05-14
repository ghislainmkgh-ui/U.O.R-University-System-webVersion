"""Modèle Journal d'Accès (Audit)"""
from core.models.base_model import BaseModel
from enum import Enum


class AccessStatus(Enum):
    """Statuts d'accès possibles"""
    GRANTED = "granted"
    DENIED_PASSWORD = "denied_password"
    DENIED_FACE = "denied_face"
    DENIED_FINANCE = "denied_finance"
    DENIED_MULTIPLE = "denied_multiple"


class AccessLog(BaseModel):
    """Modèle pour les journaux d'accès"""
    
    def __init__(self, student_id: int, access_point: str, status: AccessStatus):
        super().__init__()
        self.id: int = None
        self.student_id: int = student_id
        self.access_point: str = access_point  # Nom de la porte/terminal
        self.status: AccessStatus = status
        self.password_validated: bool = False
        self.face_validated: bool = False
        self.finance_validated: bool = False
        self.ip_address: str = None
        self.notes: str = None
