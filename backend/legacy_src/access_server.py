"""
Serveur d'Accès U.O.R — access_server.py
=========================================
Reçoit les requêtes HTTP POST de l'ESP32 (validation code + reconnaissance faciale).
Lance la reconnaissance faciale via la caméra IP sur signal de l'ESP32.

NOUVELLE ARCHITECTURE (sans ESP32-CAM, sans Arduino) :
  ESP32 (clavier + servo)
      └─ HTTP POST /verify_code {"code": "XXXX"}
              └─ access_server.py (ce fichier)
                      ├─ Valide le code en base de données
                      ├─ Capture une image depuis la caméra IP (RTSP ou HTTP snapshot)
                      ├─ Reconnaissance faciale (face_recognition + OpenCV)
                      └─ Retourne {"access": "granted|denied", "name": "...", "reason": "..."}

DÉMARRAGE :
  python access_server.py
  ou en production :
  python access_server.py --host 0.0.0.0 --port 5050

CONFIGURATION :
  Voir config/settings.py et .env pour IP_CAMERA_URL, IP_CAMERA_SNAPSHOT_URL, etc.
"""

import sys
import os
import json
import logging
import argparse
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ajouter la racine du projet au path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    ESP32_PORT,
    ACCESS_SERVER_HOST,
    FACE_CAPTURE_ATTEMPTS,
    FACE_MIN_MATCH_SUCCESSES,
    FACE_CAPTURE_RETRY_DELAY_MS,
)
from app.services.access.ip_camera_service import IPCameraService
from app.services.access.face_recognition_service import FaceRecognitionService
from core.database.connection import DatabaseConnection

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("access_server")


def _ensure_access_log_table() -> None:
    """Assure l'existence de la table access_log utilisée par le dashboard."""
    try:
        db = DatabaseConnection()
        db.execute_update(
            """
            CREATE TABLE IF NOT EXISTS access_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                access_point VARCHAR(100),
                status ENUM('GRANTED', 'DENIED_PASSWORD', 'DENIED_FACE', 'DENIED_FINANCE', 'DENIED_MULTIPLE') NOT NULL,
                password_validated BOOLEAN DEFAULT FALSE,
                face_validated BOOLEAN DEFAULT FALSE,
                finance_validated BOOLEAN DEFAULT FALSE,
                ip_address VARCHAR(50),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_student (student_id),
                INDEX idx_status (status),
                INDEX idx_date (created_at),
                INDEX idx_access_point (access_point)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
    except Exception as e:
        logger.warning(f"Impossible d'assurer access_log: {e}")


def _ensure_face_training_table() -> None:
    """Assure l'existence de la table de photos d'entraînement facial (multi-photos)."""
    try:
        db = DatabaseConnection()
        db.execute_update(
            """
            CREATE TABLE IF NOT EXISTS face_training_photos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                photo_path VARCHAR(512) DEFAULT NULL,
                photo_blob LONGBLOB,
                is_primary BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                quality_score DECIMAL(5,2) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_student (student_id),
                INDEX idx_active (is_active),
                INDEX idx_student_active (student_id, is_active),
                CONSTRAINT fk_face_training_student FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
    except Exception as e:
        logger.warning(f"Impossible d'assurer face_training_photos: {e}")


def _log_access_attempt(
    *,
    student_id: int,
    status: str,
    access_point: str,
    password_validated: bool,
    face_validated: bool,
    finance_validated: bool,
    ip_address: str,
    notes: str | None = None,
) -> None:
    """Journalise une tentative d'accès pour la page Historique d'Accès."""
    if not student_id:
        return
    try:
        db = DatabaseConnection()
        db.execute_update(
            """
            INSERT INTO access_log (
                student_id,
                access_point,
                status,
                password_validated,
                face_validated,
                finance_validated,
                ip_address,
                notes,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                int(student_id),
                access_point,
                status,
                1 if password_validated else 0,
                1 if face_validated else 0,
                1 if finance_validated else 0,
                ip_address,
                notes,
            ),
        )
    except Exception as e:
        logger.warning(f"Échec journalisation access_log (student_id={student_id}): {e}")


# ── Validation code en base de données ───────────────────────────────────────
def _get_student_by_code(code: str) -> dict | None:
    """
    Cherche un code d'accès actif en base de données.
    Retourne le dict étudiant avec ses données de photo si trouvé, sinon None.
    Paramétrise toujours la requête pour éviter les injections SQL.
    """
    try:
        db = DatabaseConnection()

        # Schéma actuel : codes dans access_code_history (pas dans une table access_code)
        # Règle métier:
        # - code full  : valide tant que l'étudiant est dans l'année académique active
        # - code partial / legacy : validité basée sur expires_at
        # On prend la plus récente émission pour ce code.
        results = db.execute_query(
            """
            SELECT
                s.id,
                s.firstname,
                s.lastname,
                s.email,
                s.passport_photo_path,
                s.passport_photo_blob,
                s.academic_year_id,
                ach.access_code,
                ach.access_type,
                ach.expires_at
            FROM access_code_history ach
            JOIN student s ON s.id = ach.student_id
            WHERE ach.access_code = %s
              AND ach.id = (
                  SELECT ach2.id
                  FROM access_code_history ach2
                  WHERE ach2.student_id = ach.student_id
                  ORDER BY ach2.issued_at DESC, ach2.id DESC
                  LIMIT 1
              )
              AND COALESCE(s.is_active, 1) = 1
              AND (
                    (
                        ach.access_type = 'full'
                        AND s.academic_year_id IS NOT NULL
                        AND EXISTS (
                            SELECT 1 FROM academic_year ay
                            WHERE ay.academic_year_id = s.academic_year_id
                              AND ay.is_active = 1
                        )
                    )
                    OR
                    (
                        ach.access_type = 'full'
                        AND s.academic_year_id IS NULL
                        AND (ach.expires_at IS NULL OR DATE(ach.expires_at) >= CURDATE())
                    )
                    OR
                    (
                        COALESCE(ach.access_type, '') <> 'full'
                        AND (ach.expires_at IS NULL OR DATE(ach.expires_at) >= CURDATE())
                    )
                  )
            ORDER BY ach.issued_at DESC, ach.id DESC
            LIMIT 1
            """,
            (code,),
        )
        return results[0] if results else None
    except Exception as e:
        logger.error(f"Erreur validation code BD: {e}")
        return None


# ── Handler HTTP ──────────────────────────────────────────────────────────────
class AccessRequestHandler(BaseHTTPRequestHandler):
    """Traite les requêtes HTTP en provenance de l'ESP32."""

    # Injectés par run_server() avant démarrage
    camera_service: IPCameraService = None
    face_service: FaceRecognitionService = None

    # Silencer les logs HTTP par défaut (on utilise notre logger)
    def log_message(self, fmt, *args):
        logger.info("[ESP32] %s — " + fmt, self.client_address[0], *args)

    # ── Réponses ─────────────────────────────────────────────────────────────
    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── GET /status ───────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path == "/status":
            cam_ok = False
            face_stats = {}
            camera_stats = {}
            try:
                cam_ok = self.camera_service.check_camera()
            except Exception:
                pass

            try:
                if self.face_service and hasattr(self.face_service, "get_runtime_stats"):
                    face_stats = self.face_service.get_runtime_stats()
            except Exception:
                face_stats = {}

            try:
                if self.camera_service and hasattr(self.camera_service, "get_runtime_stats"):
                    camera_stats = self.camera_service.get_runtime_stats()
            except Exception:
                camera_stats = {}

            self._send_json(200, {
                "status":  "online",
                "camera":  "ok" if cam_ok else "unavailable",
                "service": "U.O.R Access Server v2.0",
                "metrics": {
                    "face": face_stats,
                    "camera": camera_stats,
                },
            })
        else:
            self._send_json(404, {"error": "Endpoint non trouvé"})

    # ── POST /validate_code | /verify_face | /verify_code ────────────────────
    def do_POST(self):
        if self.path == "/validate_code":
            self._handle_validate_code()
        elif self.path == "/verify_face":
            self._handle_verify_face()
        elif self.path == "/verify_code":
            self._handle_verify_code()
        else:
            self._send_json(404, {"error": "Endpoint non trouvé"})

    def _read_code_payload(self) -> str | None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            code = str(data.get("code", "")).strip()
        except Exception as e:
            logger.error(f"Payload invalide: {e}")
            self._send_json(400, {"access": "denied", "reason": "Requête invalide"})
            return None

        if not code:
            self._send_json(400, {"access": "denied", "reason": "Code manquant"})
            return None

        return code

    def _respond_invalid_code(self) -> None:
        self._send_json(200, {
            "access": "denied",
            "code_valid": False,
            "reason": "Code invalide ou expiré",
            "message": "Votre code est incorrect.",
        })

    def _validate_code(self, code: str) -> dict | None:
        logger.info(f"Code reçu (longueur {len(code)}) — validation en cours...")
        return _get_student_by_code(code)

    def _handle_validate_code(self):
        code = self._read_code_payload()
        if code is None:
            return

        student = self._validate_code(code)
        if not student:
            logger.warning("Code invalide ou expiré")
            self._respond_invalid_code()
            return

        student_name = f"{student.get('firstname', '')} {student.get('lastname', '')}".strip()
        logger.info("Code valide → %s (id=%s)", student_name, student.get("id"))
        self._send_json(200, {
            "access": "pending_face",
            "code_valid": True,
            "name": student_name,
            "message": "Code valide. Regardez la caméra.",
            "single_entry_only": True,
        })

    def _handle_verify_face(self):
        code = self._read_code_payload()
        if code is None:
            return

        client_ip = self.client_address[0] if self.client_address else "unknown"
        _ensure_access_log_table()

        student = self._validate_code(code)
        if not student:
            logger.warning("Code invalide ou expiré lors de la vérification faciale")
            self._respond_invalid_code()
            return

        self._perform_face_verification(student=student, client_ip=client_ip)

    def _handle_verify_code(self):
        """
        Flux complet d'authentification :
          1. Lire le code envoyé par l'ESP32
          2. Valider le code en base de données
          3. Capturer une image depuis la caméra IP
          4. Effectuer la reconnaissance faciale
          5. Retourner le résultat à l'ESP32
        """
        code = self._read_code_payload()
        if code is None:
            return

        client_ip = self.client_address[0] if self.client_address else "unknown"
        _ensure_access_log_table()

        student = self._validate_code(code)
        if not student:
            logger.warning("Code invalide ou expiré")
            self._respond_invalid_code()
            return

        self._perform_face_verification(student=student, client_ip=client_ip)

    def _perform_face_verification(self, *, student: dict, client_ip: str):
        """Exécute le contrôle facial final et renvoie la réponse HTTP."""

        student_name = f"{student.get('firstname', '')} {student.get('lastname', '')}".strip()
        student_id = int(student.get("id") or 0)
        logger.info(f"Code valide → {student_name} (id={student.get('id')})")

        # 3-4. Captures multiples + reconnaissance (plus robuste en conditions réelles)
        best_confidence = 0.0
        best_capture_meta = {}
        recognized = False
        confidence = 0.0
        had_frame = False
        had_fresh_frame = False
        denied_multiple_faces = False
        recognized_count = 0
        analyzed_count = 0
        stale_skipped_count = 0
        last_analysis = {}

        logger.info(
            "Lancement reconnaissance faciale pour %s avec %s capture(s) utiles...",
            student_name,
            FACE_CAPTURE_ATTEMPTS,
        )

        # Les frames stale ne doivent pas consommer tout le budget d'analyses.
        max_capture_calls = FACE_CAPTURE_ATTEMPTS + 3
        capture_call = 0
        required_matches_runtime = max(1, min(FACE_MIN_MATCH_SUCCESSES, FACE_CAPTURE_ATTEMPTS))

        while analyzed_count < FACE_CAPTURE_ATTEMPTS and capture_call < max_capture_calls:
            capture_call += 1
            logger.info(
                "Capture image caméra IP... appel %s/%s (analysées=%s/%s)",
                capture_call,
                max_capture_calls,
                analyzed_count,
                FACE_CAPTURE_ATTEMPTS,
            )
            frame = self.camera_service.capture_frame()
            capture_meta = self.camera_service.get_last_capture_meta()

            if capture_meta.get("discovery_message"):
                logger.info(capture_meta["discovery_message"])

            if frame is None:
                logger.warning("Capture caméra IP échouée à l'appel %s", capture_call)
            else:
                had_frame = True
                frame_stale = bool(capture_meta.get("frame_stale"))
                if frame_stale:
                    stale_skipped_count += 1
                    logger.warning(
                        "Frame potentiellement figée ignorée (appel %s/%s, stale=%s)",
                        capture_call,
                        max_capture_calls,
                        stale_skipped_count,
                    )
                    if FACE_CAPTURE_RETRY_DELAY_MS > 0:
                        time.sleep(FACE_CAPTURE_RETRY_DELAY_MS / 1000.0)
                    continue

                had_fresh_frame = True

                analysis = self.face_service.analyze_student(
                    frame=frame,
                    student=student,
                )
                last_analysis = dict(analysis or {})
                recognized = bool(analysis.get("recognized"))
                confidence = float(analysis.get("confidence") or 0.0)
                analyzed_count += 1
                if confidence >= best_confidence:
                    best_confidence = float(confidence)
                    best_capture_meta = dict(capture_meta or {})

                if analysis.get("multiple_faces_detected"):
                    denied_multiple_faces = True
                    logger.warning("Accès bloqué: plusieurs visages détectés à l'appel %s", capture_call)
                    break

                if recognized:
                    recognized_count += 1
                    logger.info(
                        "Visage reconnu à l'appel %s (matches=%s/%s)",
                        capture_call,
                        recognized_count,
                        required_matches_runtime,
                    )

                    if recognized_count >= required_matches_runtime:
                        logger.info("Seuil requis atteint, arrêt anticipé de la vérification faciale")
                        break

            # Petite pause pour laisser l'utilisateur se repositionner
            if analyzed_count < FACE_CAPTURE_ATTEMPTS and FACE_CAPTURE_RETRY_DELAY_MS > 0:
                time.sleep(FACE_CAPTURE_RETRY_DELAY_MS / 1000.0)

        logger.info(
            "Fin captures: analysées=%s/%s, matches=%s, stale_ignorées=%s, appels=%s",
            analyzed_count,
            FACE_CAPTURE_ATTEMPTS,
            recognized_count,
            stale_skipped_count,
            capture_call,
        )

        if not best_capture_meta:
            best_capture_meta = capture_meta if 'capture_meta' in locals() else {}

        # Si aucune image exploitable n'a pu être capturée
        if not had_frame:
            logger.error("Capture caméra IP échouée sur toutes les tentatives")
            _log_access_attempt(
                student_id=student_id,
                status="DENIED_MULTIPLE",
                access_point="ESP32_HTTP",
                password_validated=True,
                face_validated=False,
                finance_validated=True,
                ip_address=client_ip,
                notes="camera_unavailable",
            )
            self._send_json(200, {
                "access": "denied",
                "reason": "Caméra IP non disponible — réessayez",
                "camera": best_capture_meta,
            })
            return

        if had_frame and not had_fresh_frame:
            logger.warning("Toutes les captures semblaient figées (FTP snapshot non renouvelé)")
            _log_access_attempt(
                student_id=student_id,
                status="DENIED_MULTIPLE",
                access_point="ESP32_HTTP",
                password_validated=True,
                face_validated=False,
                finance_validated=True,
                ip_address=client_ip,
                notes="camera_stale_frames",
            )
            self._send_json(200, {
                "access": "denied",
                "reason": "Flux caméra non temps réel (image figée)",
                "message": "La caméra renvoie la même image. Vérifiez la source snapshot temps réel.",
                "camera": best_capture_meta,
            })
            return

        if denied_multiple_faces:
            _log_access_attempt(
                student_id=student_id,
                status="DENIED_MULTIPLE",
                access_point="ESP32_HTTP",
                password_validated=True,
                face_validated=False,
                finance_validated=True,
                ip_address=client_ip,
                notes="multiple_faces_detected",
            )
            self._send_json(200, {
                "access": "denied",
                "reason": "Plusieurs personnes détectées. Entrée réservée à une seule personne.",
                "name": student_name,
                "single_entry_only": True,
                "camera": best_capture_meta,
            })
            return

        required_matches = max(1, min(FACE_MIN_MATCH_SUCCESSES, FACE_CAPTURE_ATTEMPTS))
        recognized = bool(recognized_count >= required_matches)
        confidence = best_confidence

        # 5. Retourner résultat
        if recognized:
            logger.info(f"✓ Visage reconnu : {student_name} (confiance {confidence:.2f})")
            _log_access_attempt(
                student_id=student_id,
                status="GRANTED",
                access_point="ESP32_HTTP",
                password_validated=True,
                face_validated=True,
                finance_validated=True,
                ip_address=client_ip,
                notes=(
                    f"confidence={confidence:.3f}; matches={recognized_count}/{FACE_CAPTURE_ATTEMPTS}; "
                    f"required={required_matches}; analyzed={analyzed_count}"
                ),
            )
            self._send_json(200, {
                "access":     "granted",
                "name":       student_name,
                "confidence": round(confidence, 3),
                "matches": recognized_count,
                "captures": FACE_CAPTURE_ATTEMPTS,
                "required_matches": required_matches,
                "single_entry_only": True,
                "message": "Accès accordé. Entrez seul, s'il vous plaît.",
                "camera":     best_capture_meta,
            })
        else:
            logger.warning(
                f"✗ Visage NON reconnu pour {student_name} "
                f"(matches={recognized_count}/{FACE_CAPTURE_ATTEMPTS}, requises={required_matches}, "
                f"meilleure confiance {best_confidence:.2f})"
            )
            _log_access_attempt(
                student_id=student_id,
                status="DENIED_FACE",
                access_point="ESP32_HTTP",
                password_validated=True,
                face_validated=False,
                finance_validated=True,
                ip_address=client_ip,
                notes=(
                    f"best_confidence={best_confidence:.3f}; matches={recognized_count}/{FACE_CAPTURE_ATTEMPTS}; "
                    f"required={required_matches}; analyzed={analyzed_count}"
                ),
            )
            self._send_json(200, {
                "access": "denied",
                "reason": "Visage non reconnu",
                "name":   student_name,
                "message": (
                    f"Validation insuffisante sur {recognized_count}/{FACE_CAPTURE_ATTEMPTS} capture(s). "
                    f"Minimum requis: {required_matches}."
                ),
                "matches": recognized_count,
                "captures": FACE_CAPTURE_ATTEMPTS,
                "required_matches": required_matches,
                "camera": best_capture_meta,
            })


# ── Démarrage serveur ─────────────────────────────────────────────────────────
def run_server(host: str = None, port: int = None):
    host = host or ACCESS_SERVER_HOST
    port = port or ESP32_PORT

    # Initialiser les services une fois (partagés entre les requêtes)
    _ensure_access_log_table()
    _ensure_face_training_table()
    camera_svc = IPCameraService()
    face_svc   = FaceRecognitionService()

    AccessRequestHandler.camera_service = camera_svc
    AccessRequestHandler.face_service   = face_svc

    server = HTTPServer((host, port), AccessRequestHandler)

    logger.info("=" * 60)
    logger.info("  U.O.R — Serveur d'Accès démarré")
    logger.info(f"  Écoute sur : http://{host}:{port}")
    logger.info(f"  Endpoint   : POST /verify_code")
    logger.info("  Nouveau flux: POST /validate_code puis POST /verify_face")
    logger.info(f"  Santé      : GET  /status")
    logger.info("=" * 60)
    logger.info(f"Caméra IP : {camera_svc.snapshot_url or camera_svc.rtsp_url or 'non configurée'}")
    logger.info("En attente de requêtes de l'ESP32...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Arrêt du serveur (Ctrl+C)")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="U.O.R — Serveur d'accès ESP32")
    parser.add_argument("--host", default=None, help="Interface d'écoute (défaut: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port (défaut: 5050)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
