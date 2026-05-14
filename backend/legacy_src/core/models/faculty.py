"""Modèle Faculté"""
from core.models.base_model import BaseModel


class Faculty(BaseModel):
    """Modèle pour les Facultés"""
    
    def __init__(self, name: str, code: str, description: str = ""):
        super().__init__()
        self.id: int = None
        self.name: str = name
        self.code: str = code
        self.description: str = description
        self.is_active: bool = True
