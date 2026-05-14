"""Modèle de base pour tous les modèles métier"""
from datetime import datetime
from typing import Any, Dict


class BaseModel:
    """Classe de base pour tous les modèles"""
    
    def __init__(self):
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le modèle en dictionnaire
        
        Returns:
            Dictionnaire du modèle
        """
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }
    
    def update_timestamp(self):
        """Met à jour le timestamp de modification"""
        self.updated_at = datetime.now()
