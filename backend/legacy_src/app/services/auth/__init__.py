"""
Module d'authentification et reconnaissance faciale
Exports publics suivant le principe d'encapsulation
"""
from app.services.auth.authentication_service import AuthenticationService
from app.services.auth.face_recognition_service import (
    FaceRecognitionService,
    MockFaceRecognitionService
)
from app.services.auth.face_recognition_interface import IFaceRecognitionService
from app.services.auth.face_recognition_config import FACE_CONFIG

__all__ = [
    'AuthenticationService',
    'FaceRecognitionService',
    'MockFaceRecognitionService',
    'IFaceRecognitionService',
    'FACE_CONFIG'
]
