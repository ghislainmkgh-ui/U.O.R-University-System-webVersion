"""Modèle Promotion"""
from core.models.base_model import BaseModel


class Promotion(BaseModel):
    """Modèle pour les Promotions"""
    
    def __init__(self, name: str, year: int, department_id: int):
        super().__init__()
        self.id: int = None
        self.name: str = name
        self.year: int = year
        self.department_id: int = department_id
        self.is_active: bool = True
