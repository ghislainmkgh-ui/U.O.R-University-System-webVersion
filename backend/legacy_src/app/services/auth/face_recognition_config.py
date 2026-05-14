"""Configuration pour le service de reconnaissance faciale (SOLID - Single Responsibility Principle)"""
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class FaceRecognitionConfig:
    """
    Configuration immuable pour la reconnaissance faciale
    
    Utilise dataclass avec frozen=True pour l'immutabilité (principe Open/Closed)
    """
    
    # Tolérance par défaut (0.0 = très strict, 1.0 = très permissif)
    DEFAULT_TOLERANCE: Final[float] = 0.6
    
    # Tolérance de sécurité élevée pour l'accès aux examens
    SECURITY_HIGH_TOLERANCE: Final[float] = 0.5
    
    # Tolérance permissive pour l'enregistrement initial
    REGISTRATION_TOLERANCE: Final[float] = 0.7
    
    # Nombre maximum de visages à détecter dans une image
    MAX_FACES_PER_IMAGE: Final[int] = 1
    
    # Formats d'image acceptés
    ACCEPTED_IMAGE_FORMATS: Final[tuple] = ('.jpg', '.jpeg', '.png', '.bmp')
    
    # Taille maximale de l'image en MB
    MAX_IMAGE_SIZE_MB: Final[int] = 10


# Instance singleton de configuration
FACE_CONFIG = FaceRecognitionConfig()
