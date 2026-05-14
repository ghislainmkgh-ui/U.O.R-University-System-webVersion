"""
Service de reconnaissance faciale avec architecture SOLID
Respecte les principes: SRP, OCP, LSP, ISP, DIP
"""
import logging
import os
import numpy as np
from PIL import Image, ImageStat
from pathlib import Path
from typing import Optional
from app.services.auth.face_recognition_interface import IFaceRecognitionService
from app.services.auth.face_recognition_config import FACE_CONFIG

logger = logging.getLogger(__name__)


class FaceRecognitionService(IFaceRecognitionService):
    """
    Implémentation de la reconnaissance faciale avec face_recognition
    
    Principes appliqués:
    - SRP: Une seule responsabilité - gérer la reconnaissance faciale
    - OCP: Ouvert à l'extension (via interface), fermé à la modification
    - LSP: Substitution de Liskov via l'interface IFaceRecognitionService
    - ISP: Interface ségrégée avec méthodes spécifiques
    - DIP: Dépend de l'abstraction IFaceRecognitionService
    """
    
    def __init__(self, config=FACE_CONFIG):
        """
        Initialise le service de reconnaissance faciale
        
        Args:
            config: Configuration du service (injection de dépendance)
        """
        self._config = config
        self._face_recognition = None
        self._initialized = False
        self._initialize_library()
    
    def _initialize_library(self) -> None:
        """Initialise la bibliothèque face_recognition (méthode privée)"""
        try:
            import face_recognition
            self._face_recognition = face_recognition
            self._initialized = True
            logger.info("Face recognition library initialized successfully")
        except ImportError as e:
            logger.warning(
                "face_recognition library not installed. "
                "Install with: pip install face-recognition"
            )
            logger.debug(f"Import error details: {e}")
            self._initialized = False
    
    def is_available(self) -> bool:
        """
        Vérifie si le service est disponible
        
        Returns:
            True si la bibliothèque est chargée et prête
        """
        return self._initialized and self._face_recognition is not None
    
    def register_face(self, image_path: str, student_id: int) -> Optional[np.ndarray]:
        """
        Enregistre le visage d'un étudiant avec validation complète
        
        Args:
            image_path: Chemin vers l'image du visage
            student_id: ID de l'étudiant
            
        Returns:
            Encoding du visage (numpy array) ou None si échec
            
        Raises:
            ValueError: Si les paramètres sont invalides
            FileNotFoundError: Si l'image n'existe pas
            RuntimeError: Si le service n'est pas disponible
        """
        # Validation des entrées (SOLID - validation précoce)
        self._validate_service_availability()
        self._validate_image_path(image_path)
        self._validate_student_id(student_id)
        
        try:
            # Chargement de l'image
            image = self._face_recognition.load_image_file(image_path)
            
            # Détection des visages
            face_encodings = self._face_recognition.face_encodings(image)
            
            # Validation du nombre de visages détectés
            if not face_encodings:
                logger.warning(f"No face detected in image for student {student_id}")
                return None
            
            if len(face_encodings) > self._config.MAX_FACES_PER_IMAGE:
                logger.warning(
                    f"Multiple faces detected ({len(face_encodings)}) for student {student_id}. "
                    f"Expected max: {self._config.MAX_FACES_PER_IMAGE}."
                )
                return None
            
            # Extraction du premier visage
            face_encoding = face_encodings[0]
            
            # Validation de l'encoding
            if not self._validate_face_encoding(face_encoding):
                logger.error(f"Invalid face encoding generated for student {student_id}")
                return None
            
            logger.info(f"Face successfully registered for student {student_id}")
            return face_encoding
            
        except FileNotFoundError:
            logger.error(f"Image file not found: {image_path}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during face registration for student {student_id}: {e}")
            return None
    
    def verify_face(
        self, 
        image_path: str, 
        stored_encoding: np.ndarray, 
        tolerance: float = None
    ) -> bool:
        """
        Vérifie un visage contre un encoding stocké avec sécurité renforcée
        
        Args:
            image_path: Chemin vers l'image à vérifier
            stored_encoding: Encoding stocké en base (numpy array)
            tolerance: Tolérance de comparaison (utilise la config par défaut si None)
            
        Returns:
            True si le visage correspond, False sinon
            
        Raises:
            ValueError: Si les paramètres sont invalides
            RuntimeError: Si le service n'est pas disponible
        """
        # Utiliser la tolérance de sécurité par défaut si non spécifiée
        if tolerance is None:
            tolerance = self._config.SECURITY_HIGH_TOLERANCE
        
        # Validation des entrées
        self._validate_service_availability()
        self._validate_image_path(image_path)
        self._validate_tolerance(tolerance)
        
        if stored_encoding is None:
            logger.error("Stored encoding is None - cannot verify")
            return False
        
        if not self._validate_face_encoding(stored_encoding):
            logger.error("Invalid stored encoding format")
            return False
        
        try:
            # Chargement de l'image de vérification
            image = self._face_recognition.load_image_file(image_path)
            
            # Détection des visages
            face_encodings = self._face_recognition.face_encodings(image)
            
            if not face_encodings:
                logger.warning(f"No face detected in verification image: {image_path}")
                return False
            
            if len(face_encodings) > 1:
                logger.warning(
                    f"Multiple faces detected in verification image. "
                    f"Using only the first face."
                )
            
            # Comparaison avec le visage stocké
            current_encoding = face_encodings[0]
            matches = self._face_recognition.compare_faces(
                [stored_encoding],
                current_encoding,
                tolerance=tolerance
            )
            
            # Calcul de la distance pour logging (optionnel mais utile)
            face_distance = self._face_recognition.face_distance(
                [stored_encoding],
                current_encoding
            )[0]
            
            result = matches[0] if matches else False
            logger.info(
                f"Face verification result: {result} "
                f"(distance: {face_distance:.4f}, tolerance: {tolerance})"
            )
            
            return result
            
        except FileNotFoundError:
            logger.error(f"Verification image not found: {image_path}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during face verification: {e}")
            return False

    def validate_passport_photo(self, image_path: str) -> tuple[bool, str]:
        """Valide la qualité d'une photo passeport (centrage, luminosité, netteté)."""
        try:
            self._validate_service_availability()
            self._validate_image_path(image_path)

            image = Image.open(image_path)
            width, height = image.size

            # Luminosité & contraste simples
            gray = image.convert("L")
            stats = ImageStat.Stat(gray)
            brightness = stats.mean[0]
            contrast = stats.stddev[0]
            if brightness < 60 or brightness > 200:
                return False, "Photo trop sombre ou trop claire. Utilisez un bon éclairage."
            if contrast < 20:
                return False, "Contraste trop faible. Photo floue ou mal éclairée."

            # Netteté (variance du Laplacien approximé)
            gray_np = np.array(gray, dtype=np.float32)
            laplacian = (
                -1 * gray_np[:-2, 1:-1]
                -1 * gray_np[2:, 1:-1]
                -1 * gray_np[1:-1, :-2]
                -1 * gray_np[1:-1, 2:]
                +4 * gray_np[1:-1, 1:-1]
            )
            sharpness = laplacian.var()
            if sharpness < 50:
                return False, "Photo trop floue. Utilisez une image nette et bien cadrée."

            # Centrage visage
            image_np = np.array(image)
            face_locations = self._face_recognition.face_locations(image_np)
            if not face_locations:
                return False, "Aucun visage détecté sur la photo."
            if len(face_locations) > 1:
                return False, "Plusieurs visages détectés. Utilisez une photo individuelle."

            top, right, bottom, left = face_locations[0]
            face_center_x = (left + right) / 2
            face_center_y = (top + bottom) / 2
            img_center_x = width / 2
            img_center_y = height / 2

            if abs(face_center_x - img_center_x) > width * 0.15 or abs(face_center_y - img_center_y) > height * 0.15:
                return False, "Visage mal centré. Utilisez une photo passeport bien cadrée."

            return True, "OK"
        except Exception as e:
            logger.error(f"Photo quality validation error: {e}")
            return False, "Impossible de valider la qualité de la photo."
    
    # ============= Méthodes de validation privées (SRP) =============
    
    def _validate_service_availability(self) -> None:
        """Valide que le service est disponible"""
        if not self.is_available():
            raise RuntimeError(
                "Face recognition service not available. "
                "Ensure face_recognition library is installed."
            )
    
    def _validate_image_path(self, image_path: str) -> None:
        """Valide le chemin de l'image"""
        if not image_path or not isinstance(image_path, str):
            raise ValueError("Invalid image path: must be a non-empty string")
        
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {image_path}")
        
        # Vérifier l'extension
        if path.suffix.lower() not in self._config.ACCEPTED_IMAGE_FORMATS:
            raise ValueError(
                f"Invalid image format: {path.suffix}. "
                f"Accepted formats: {self._config.ACCEPTED_IMAGE_FORMATS}"
            )
        
        # Vérifier la taille du fichier
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self._config.MAX_IMAGE_SIZE_MB:
            raise ValueError(
                f"Image file too large: {file_size_mb:.2f}MB. "
                f"Maximum allowed: {self._config.MAX_IMAGE_SIZE_MB}MB"
            )
    
    def _validate_student_id(self, student_id: int) -> None:
        """Valide l'ID de l'étudiant"""
        if not isinstance(student_id, int) or student_id <= 0:
            raise ValueError(f"Invalid student ID: {student_id}. Must be a positive integer")
    
    def _validate_tolerance(self, tolerance: float) -> None:
        """Valide la tolérance de comparaison"""
        if not isinstance(tolerance, (int, float)):
            raise ValueError(f"Invalid tolerance type: {type(tolerance)}. Must be numeric")
        
        if not 0.0 <= tolerance <= 1.0:
            raise ValueError(f"Invalid tolerance value: {tolerance}. Must be between 0.0 and 1.0")
    
    def _validate_face_encoding(self, encoding: np.ndarray) -> bool:
        """
        Valide un encoding de visage
        
        Args:
            encoding: Encoding à valider
            
        Returns:
            True si l'encoding est valide
        """
        if encoding is None:
            return False
        
        if not isinstance(encoding, np.ndarray):
            logger.error(f"Invalid encoding type: {type(encoding)}. Expected numpy.ndarray")
            return False
        
        # Un encoding face_recognition standard a 128 dimensions
        if encoding.shape != (128,):
            logger.error(f"Invalid encoding shape: {encoding.shape}. Expected (128,)")
            return False
        
        # Vérifier que l'encoding contient des valeurs numériques valides
        if not np.all(np.isfinite(encoding)):
            logger.error("Encoding contains non-finite values (NaN or Inf)")
            return False
        
        return True
    
    def __repr__(self) -> str:
        """Représentation string du service"""
        status = "available" if self.is_available() else "unavailable"
        return f"FaceRecognitionService(status={status})"


class MockFaceRecognitionService(IFaceRecognitionService):
    """
    Mock du service de reconnaissance faciale pour les tests
    
    Principe: Liskov Substitution - peut remplacer FaceRecognitionService
    """
    
    def __init__(self, always_match: bool = True):
        """
        Initialise le mock
        
        Args:
            always_match: Si True, verify_face retourne toujours True
        """
        self._always_match = always_match
        logger.info("Mock face recognition service initialized")
    
    def is_available(self) -> bool:
        """Le mock est toujours disponible"""
        return True
    
    def register_face(self, image_path: str, student_id: int) -> Optional[np.ndarray]:
        """Retourne un encoding factice"""
        logger.info(f"Mock: Registering face for student {student_id}")
        return np.random.rand(128)  # Encoding factice de 128 dimensions
    
    def verify_face(
        self, 
        image_path: str, 
        stored_encoding: np.ndarray, 
        tolerance: float = 0.6
    ) -> bool:
        """Retourne le résultat configuré"""
        logger.info(f"Mock: Verifying face (result: {self._always_match})")
        return self._always_match
