"""Modèle Département"""
from core.models.base_model import BaseModel


class Department(BaseModel):
    """Modèle pour les Départements"""
    
    def __init__(self, name: str, code: str, faculty_id: int):
        super().__init__()
        self.id: int = None
        self.name: str = name
        self.code: str = code
        self.faculty_id: int = faculty_id
        self.is_active: bool = True
