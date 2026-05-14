"""Interface abstraite pour les services de reconnaissance faciale (SOLID - Interface Segregation Principle)"""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class IFaceRecognitionService(ABC):
    """
    Interface pour la reconnaissance faciale
    
    Suit le principe d'inversion de dépendances (Dependency Inversion Principle):
    Les modules de haut niveau ne doivent pas dépendre des modules de bas niveau,
    mais des abstractions.
    """
    
    @abstractmethod
    def register_face(self, image_path: str, student_id: int) -> Optional[np.ndarray]:
        """
        Enregistre le visage d'un étudiant
        
        Args:
            image_path: Chemin vers l'image du visage
            student_id: ID de l'étudiant
            
        Returns:
            Encoding du visage (numpy array) ou None si échec
            
        Raises:
            ValueError: Si les paramètres sont invalides
            FileNotFoundError: Si l'image n'existe pas
        """
        pass
    
    @abstractmethod
    def verify_face(self, image_path: str, stored_encoding: np.ndarray, tolerance: float) -> bool:
        """
        Vérifie un visage contre un encoding stocké
        
        Args:
            image_path: Chemin vers l'image à vérifier
            stored_encoding: Encoding stocké en base (numpy array)
            tolerance: Tolérance de comparaison (0-1, plus bas = plus strict)
            
        Returns:
            True si le visage correspond, False sinon
            
        Raises:
            ValueError: Si les paramètres sont invalides
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si le service est disponible et initialisé
        
        Returns:
            True si le service peut être utilisé
        """
        pass
