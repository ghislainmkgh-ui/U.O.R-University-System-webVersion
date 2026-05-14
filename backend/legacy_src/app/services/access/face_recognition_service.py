"""
Service de Reconnaissance Faciale — côté serveur Python
========================================================
Compare le visage capturé par la caméra IP avec la photo
de référence de l'étudiant stockée en base de données.

Bibliothèques requises :
  pip install face-recognition opencv-python

Sources de photo de référence (par priorité) :
  1. passport_photo_blob : blob binaire stocké en BD  (priorité)
  2. passport_photo_path : chemin absolu vers fichier image  (fallback)

Si aucune photo de référence n'est disponible → accès refusé.
Si face_recognition n'est pas installé → mode dégradé (accès accordé sur code valide uniquement).

CONFIGURATION :
  FACE_RECOGNITION_TOLERANCE dans .env (défaut 0.50)
  Plus la valeur est basse → plus strict (0.4 = strict, 0.6 = permissif)
"""

import logging
import os
import re
import time
from collections import OrderedDict
from datetime import datetime
import numpy as np
import cv2

from core.database.connection import DatabaseConnection
from config.settings import (
    DB_NAME,
    FACE_ENABLE_CLAHE_FALLBACK,
    FACE_MAX_PROCESSING_WIDTH,
    FACE_REFERENCE_CACHE_TTL_SEC,
    FACE_RECOGNITION_TOLERANCE,
    FACE_REJECT_MULTIPLE_FACES,
)

logger = logging.getLogger(__name__)

try:
    import face_recognition as _fr
    FACE_RECOGNITION_AVAILABLE = True
    logger.info("Bibliothèque face_recognition chargée avec succès")
except ImportError:
    _fr = None
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning(
        "face_recognition non installé — reconnaissance faciale désactivée. "
        "Installez avec : pip install face-recognition"
    )


class FaceRecognitionService:
    """
    Identifie un étudiant par comparaison faciale entre :
      - La frame capturée par la caméra IP (image live)
      - La photo de référence de l'étudiant (BD ou fichier)
    """

    def __init__(self, tolerance: float = None):
        from config.settings import LOG_DIR
        self.tolerance = tolerance if tolerance is not None else FACE_RECOGNITION_TOLERANCE
        # IMPORTANT performance/disque:
        # - désactivé par défaut en production (pas d'écritures JPEG massives)
        # - activable explicitement pour diagnostic ponctuel
        self.debug_save_frames = os.getenv("FACE_DEBUG_SAVE_FRAMES", "False").lower() == "true"
        self.debug_min_interval_sec = max(0, int(os.getenv("FACE_DEBUG_MIN_INTERVAL_SEC", "60")))
        self.debug_dir = os.getenv("FACE_DEBUG_DIR", os.path.join(LOG_DIR, "face_debug"))
        self.max_processing_width = FACE_MAX_PROCESSING_WIDTH
        self.reference_cache_ttl_sec = FACE_REFERENCE_CACHE_TTL_SEC
        self.reference_cache_max_students = max(50, int(os.getenv("FACE_REFERENCE_CACHE_MAX_STUDENTS", "5000")))
        self.enable_clahe_fallback = FACE_ENABLE_CLAHE_FALLBACK
        self._reference_cache: OrderedDict[int, dict] = OrderedDict()
        self._face_training_table_available: bool | None = None
        self._last_debug_save_ts: dict[str, float] = {}
        self._stats = {
            "analyses": 0,
            "recognized": 0,
            "no_face": 0,
            "multiple_faces": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_evictions": 0,
        }
        logger.info(
            f"FaceRecognitionService initialisé — "
            f"tolérance={self.tolerance} "
            f"(face_recognition: {'DISPONIBLE' if FACE_RECOGNITION_AVAILABLE else 'NON DISPONIBLE'})"
        )

    def get_runtime_stats(self) -> dict:
        return {
            **self._stats,
            "cache_size": len(self._reference_cache),
            "cache_ttl_sec": self.reference_cache_ttl_sec,
            "cache_max_students": self.reference_cache_max_students,
            "tolerance": self.tolerance,
        }

    # ── API publique ──────────────────────────────────────────────────────────

    def identify_student(
        self,
        frame: np.ndarray,
        student: dict,
    ) -> tuple[bool, float]:
        analysis = self.analyze_student(frame=frame, student=student)
        return bool(analysis["recognized"]), float(analysis["confidence"])

    def analyze_student(
        self,
        frame: np.ndarray,
        student: dict,
    ) -> dict:
        """
        Compare le visage dans `frame` avec la photo de référence de l'étudiant.

        Args:
            frame:    Image BGR numpy array capturée par la caméra IP.
            student:  Dict contenant passport_photo_blob et/ou passport_photo_path.

        Returns:
            dict avec recognized/confidence/reason/multiple_faces_detected/face_detected.
        """
        if not FACE_RECOGNITION_AVAILABLE:
            logger.warning(
                "face_recognition non disponible — accès accordé sur code valide uniquement (mode dégradé)"
            )
            return {
                "recognized": True,
                "confidence": 1.0,
                "reason": "face_recognition_unavailable",
                "multiple_faces_detected": False,
                "face_detected": True,
            }

        self._stats["analyses"] += 1

        # Obtenir les encodages faciaux de référence (photo principale + photos d'entraînement)
        ref_encodings = self._get_reference_encodings(student)
        reference_count = len(ref_encodings)
        if reference_count == 0:
            student_id = student.get("id", "?")
            logger.warning(
                f"Aucune photo de référence pour étudiant id={student_id} — accès refusé"
            )
            return {
                "recognized": False,
                "confidence": 0.0,
                "reason": "no_reference_photo",
                "multiple_faces_detected": False,
                "face_detected": False,
            }

        # Convertir BGR → RGB (face_recognition utilise RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        capture_analysis = self._extract_capture_analysis(rgb_frame)
        captured_encoding = capture_analysis.get("encoding")
        if capture_analysis.get("multiple_faces_detected"):
            self._stats["multiple_faces"] += 1
            self._save_debug_frame(frame, student, reason="multiple_faces_detected")
            logger.warning("Plusieurs visages détectés dans la frame live — accès refusé")
            return {
                "recognized": False,
                "confidence": 0.0,
                "reason": "multiple_faces",
                "multiple_faces_detected": True,
                "face_detected": True,
            }

        if captured_encoding is None:
            self._stats["no_face"] += 1
            self._save_debug_frame(frame, student, reason="no_face_detected")
            logger.warning("Aucun visage détecté dans la frame de la caméra IP")
            return {
                "recognized": False,
                "confidence": 0.0,
                "reason": "no_face_detected",
                "multiple_faces_detected": False,
                "face_detected": False,
            }

        # Calculer la meilleure distance sur toutes les photos de référence
        distances = _fr.face_distance(ref_encodings, captured_encoding)
        if distances is None or len(distances) == 0:
            return {
                "recognized": False,
                "confidence": 0.0,
                "reason": "distance_compute_failed",
                "multiple_faces_detected": False,
                "face_detected": True,
            }

        min_distance = float(np.min(distances))
        recognized = bool(min_distance <= self.tolerance)
        confidence = float(max(0.0, 1.0 - min_distance))

        # Note: Ici, on compare une capture live aux photos de référence du MÊME étudiant.
        # Un filtre d'ambiguïté inter-identités n'est pas pertinent à ce niveau et crée des faux refus.
        is_ambiguous = False

        logger.info(
            f"Résultat reconnaissance: distance_min={min_distance:.3f} / tolérance={self.tolerance} "
            f"→ {'✓ RECONNU' if recognized else '✗ NON RECONNU'}  (confiance={confidence:.2f})"
        )

        if recognized:
            self._stats["recognized"] += 1

        if not recognized:
            self._save_debug_frame(frame, student, reason=f"distance_{min_distance:.3f}")

        return {
            "recognized": recognized,
            "confidence": confidence,
            "reason": "recognized" if recognized else "face_mismatch",
            "multiple_faces_detected": False,
            "face_detected": True,
        }

    # ── Méthodes privées ──────────────────────────────────────────────────────

    def _get_reference_encodings(self, student: dict) -> list[np.ndarray]:
        """Charge les encodages de référence (photo principale + photos d'entraînement)."""
        student_id = int(student.get("id") or 0)
        cached = self._get_cached_references(student_id)
        if cached is not None:
            return cached

        encodings: list[np.ndarray] = []

        # Photo principale (legacy)
        blob = student.get("passport_photo_blob")
        if blob:
            encoded = self._encode_from_bytes(bytes(blob), source="blob BD")
            if encoded is not None:
                encodings.append(encoded)

        # Photo principale via chemin fichier (fallback)
        path = student.get("passport_photo_path")
        if path:
            encoded = self._encode_from_file(path)
            if encoded is not None:
                encodings.append(encoded)

        # Photos d'entraînement supplémentaires
        if student_id > 0 and self._training_table_available():
            for photo in self._fetch_training_photos(student_id):
                encoded = None
                if photo.get("photo_blob"):
                    encoded = self._encode_from_bytes(bytes(photo["photo_blob"]), source="training_blob")
                elif photo.get("photo_path"):
                    encoded = self._encode_from_file(str(photo["photo_path"]))

                if encoded is not None:
                    encodings.append(encoded)

        if student_id > 0:
            # LRU: rafraîchir la position si déjà présent
            if student_id in self._reference_cache:
                self._reference_cache.pop(student_id, None)

            self._reference_cache[student_id] = {
                "ts": time.time(),
                "encodings": encodings,
            }

            # Borne mémoire: éjecter les plus anciens au-delà de la limite
            while len(self._reference_cache) > self.reference_cache_max_students:
                self._reference_cache.popitem(last=False)
                self._stats["cache_evictions"] += 1

        return encodings

    def _get_cached_references(self, student_id: int) -> list[np.ndarray] | None:
        if student_id <= 0:
            return None

        payload = self._reference_cache.get(student_id)
        if not payload:
            self._stats["cache_misses"] += 1
            return None

        ts = float(payload.get("ts") or 0)
        if (time.time() - ts) > self.reference_cache_ttl_sec:
            self._reference_cache.pop(student_id, None)
            self._stats["cache_misses"] += 1
            return None

        # LRU: entrée récemment utilisée
        try:
            self._reference_cache.move_to_end(student_id, last=True)
        except Exception:
            pass

        self._stats["cache_hits"] += 1
        refs = payload.get("encodings") or []
        return refs if isinstance(refs, list) else None

    def _training_table_available(self) -> bool:
        if self._face_training_table_available is not None:
            return self._face_training_table_available

        try:
            db = DatabaseConnection()
            rows = db.execute_query(
                """
                SELECT COUNT(*) AS c
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = 'face_training_photos'
                """,
                (DB_NAME,),
            )
            self._face_training_table_available = bool(rows and int(rows[0].get("c") or 0) > 0)
        except Exception as e:
            logger.debug("Vérification table face_training_photos impossible: %s", e)
            self._face_training_table_available = False

        return self._face_training_table_available

    def _fetch_training_photos(self, student_id: int) -> list[dict]:
        try:
            db = DatabaseConnection()
            return db.execute_query(
                """
                SELECT photo_blob, photo_path
                FROM face_training_photos
                WHERE student_id = %s
                  AND is_active = 1
                ORDER BY is_primary DESC, id ASC
                LIMIT 12
                """,
                (student_id,),
            ) or []
        except Exception as e:
            logger.debug("Lecture photos d'entraînement échouée (student_id=%s): %s", student_id, e)
            return []

    def _encode_from_bytes(self, data: bytes, source: str = "blob") -> np.ndarray | None:
        """Encode un visage depuis des données binaires (JPEG, PNG…)."""
        try:
            img_array = np.frombuffer(data, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                logger.error(f"Décodage image {source} échoué (format non supporté)")
                return None
            return self._encode_image(img, source=source)
        except Exception as e:
            logger.error(f"Erreur encodage depuis {source}: {e}")
            return None

    def _encode_from_file(self, path: str) -> np.ndarray | None:
        """Encode un visage depuis un fichier image."""
        try:
            img = cv2.imread(path)
            if img is None:
                logger.error(f"Fichier image introuvable ou illisible: {path}")
                return None
            return self._encode_image(img, source=f"fichier:{path}")
        except Exception as e:
            logger.error(f"Erreur lecture fichier image '{path}': {e}")
            return None

    def _encode_image(self, img_bgr: np.ndarray, source: str) -> np.ndarray | None:
        """Retourne l'encodage 128D du visage trouvé dans une image BGR."""
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            locations = self._detect_faces_with_fallback(rgb)
            if not locations:
                logger.warning(f"Aucun visage trouvé dans la photo de référence ({source})")
                return None
            location = self._largest_face(locations)
            encodings = _fr.face_encodings(rgb, [location])
            if not encodings:
                return None
            return encodings[0]
        except Exception as e:
            logger.error(f"Erreur encodage image ({source}): {e}")
            return None

    @staticmethod
    def _largest_face(face_locations: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
        """Retourne le visage de plus grande surface (top, right, bottom, left)."""
        return max(face_locations, key=lambda f: max(1, (f[2] - f[0]) * (f[1] - f[3])))

    def _resize_for_speed(self, rgb_img: np.ndarray) -> tuple[np.ndarray, float]:
        """Réduit la résolution d'analyse pour accélérer la détection sans perte notable."""
        try:
            h, w = rgb_img.shape[:2]
            if w <= self.max_processing_width:
                return rgb_img, 1.0

            scale = self.max_processing_width / float(max(1, w))
            new_h = max(1, int(h * scale))
            resized = cv2.resize(rgb_img, (self.max_processing_width, new_h), interpolation=cv2.INTER_AREA)
            return resized, scale
        except Exception:
            return rgb_img, 1.0

    def _detect_faces_with_fallback(self, rgb_img: np.ndarray) -> list:
        """Détection de visage robuste avec plusieurs stratégies légères."""
        # 1) Détection standard
        locations = _fr.face_locations(rgb_img, model="hog")
        if locations:
            return locations

        # 2) Détection avec upsample
        locations = _fr.face_locations(rgb_img, number_of_times_to_upsample=1, model="hog")
        if locations:
            logger.info("Visage détecté après upsample x1")
            return locations

        # 3) Amélioration contraste (CLAHE) + upsample
        try:
            gray = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
            locations = _fr.face_locations(enhanced_rgb, number_of_times_to_upsample=1, model="hog")
            if locations:
                logger.info("Visage détecté après CLAHE + upsample")
                return locations
        except Exception as e:
            logger.debug(f"Fallback CLAHE échoué: {e}")

        # 4) Agrandissement image (utile pour visage trop petit)
        try:
            h, w = rgb_img.shape[:2]
            if min(h, w) < 900:
                scaled = cv2.resize(rgb_img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
                locations = _fr.face_locations(scaled, number_of_times_to_upsample=1, model="hog")
                if locations:
                    logger.info("Visage détecté après resize x1.5")
                    # Ramener les coordonnées à l'échelle originale
                    normalized = []
                    for top, right, bottom, left in locations:
                        normalized.append((int(top / 1.5), int(right / 1.5), int(bottom / 1.5), int(left / 1.5)))
                    return normalized
        except Exception as e:
            logger.debug(f"Fallback resize échoué: {e}")

        return []

    def _count_faces_security(self, rgb_img: np.ndarray) -> int:
        """Compte les visages visibles pour le contrôle anti-fraude avant ouverture."""
        detected_counts: list[int] = []

        for upsample in (0, 1):
            try:
                locations = _fr.face_locations(
                    rgb_img,
                    number_of_times_to_upsample=upsample,
                    model="hog",
                )
                detected_counts.append(len(locations or []))
            except Exception as e:
                logger.debug(f"Comptage sécurité échoué (upsample={upsample}): {e}")

        return max(detected_counts or [0])

    def _extract_capture_analysis(self, rgb_img: np.ndarray) -> dict:
        """Retourne l'analyse live: encodage, présence visage, visages multiples."""
        candidate, _ = self._resize_for_speed(rgb_img)

        # Pipeline rapide par défaut: original (upsample 0 puis 1)
        for upsample in (0, 1):
            try:
                locations = _fr.face_locations(
                    candidate,
                    number_of_times_to_upsample=upsample,
                    model="hog",
                )
            except Exception as e:
                logger.debug(f"Détection échouée (fast, upsample={upsample}): {e}")
                continue

            if not locations:
                continue

            if FACE_REJECT_MULTIPLE_FACES and len(locations) > 1:
                return {
                    "encoding": None,
                    "multiple_faces_detected": True,
                }

            location = self._largest_face(locations)
            try:
                encodings = _fr.face_encodings(candidate, [location])
                if encodings:
                    return {
                        "encoding": encodings[0],
                        "multiple_faces_detected": False,
                    }
            except Exception as e:
                logger.debug(f"Encodage échoué (fast, upsample={upsample}): {e}")

        # Fallback ciblé en faible lumière (optionnel)
        if self.enable_clahe_fallback:
            try:
                gray = cv2.cvtColor(candidate, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
                locations = _fr.face_locations(enhanced_rgb, number_of_times_to_upsample=0, model="hog")
                if locations:
                    if FACE_REJECT_MULTIPLE_FACES and len(locations) > 1:
                        return {
                            "encoding": None,
                            "multiple_faces_detected": True,
                        }

                    encodings = _fr.face_encodings(enhanced_rgb, [self._largest_face(locations)])
                    if encodings:
                        return {
                            "encoding": encodings[0],
                            "multiple_faces_detected": False,
                        }
            except Exception as e:
                logger.debug(f"Fallback CLAHE échoué: {e}")

        return {
            "encoding": None,
            "multiple_faces_detected": False,
        }

    def _save_debug_frame(self, frame_bgr: np.ndarray, student: dict, reason: str) -> None:
        """Sauvegarde l'image live en debug lorsqu'une reconnaissance échoue."""
        if not self.debug_save_frames:
            return

        try:
            # Rate-limit anti-surcharge disque
            student_id = str(student.get("id", "unknown"))
            key = f"{student_id}:{reason}"
            now = time.time()
            last_ts = float(self._last_debug_save_ts.get(key) or 0.0)
            if (now - last_ts) < self.debug_min_interval_sec:
                return

            os.makedirs(self.debug_dir, exist_ok=True)

            fullname = f"{student.get('firstname', '')}_{student.get('lastname', '')}".strip("_")
            fullname = re.sub(r"[^A-Za-z0-9_\-]", "", fullname) or "unknown"
            safe_reason = re.sub(r"[^A-Za-z0-9_\-\.]", "", str(reason or "failed"))
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

            filename = f"face_fail_{student_id}_{fullname}_{safe_reason}_{ts}.jpg"
            path = os.path.join(self.debug_dir, filename)
            ok = cv2.imwrite(path, frame_bgr)
            if ok:
                self._last_debug_save_ts[key] = now
                logger.info(f"Debug frame sauvegardée: {path}")
            else:
                logger.warning("Échec sauvegarde debug frame (cv2.imwrite=false)")
        except Exception as e:
            logger.warning(f"Impossible de sauvegarder la debug frame: {e}")
