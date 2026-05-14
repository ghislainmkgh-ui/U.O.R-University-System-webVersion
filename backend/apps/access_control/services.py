"""Access-control service used by Django and the ESP32 compatibility routes."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from apps.common.legacy import ensure_legacy_path

ensure_legacy_path()

from access_server import (  # noqa: E402
    _ensure_access_log_table,
    _ensure_face_training_table,
    _get_student_by_code,
    _log_access_attempt,
)
from app.services.access.face_recognition_service import FaceRecognitionService  # noqa: E402
from app.services.access.ip_camera_service import IPCameraService  # noqa: E402
from config.settings import (  # noqa: E402
    FACE_CAPTURE_ATTEMPTS,
    FACE_CAPTURE_RETRY_DELAY_MS,
    FACE_MIN_MATCH_SUCCESSES,
)


@dataclass
class AccessResult:
    status_code: int
    body: dict


class AccessVerificationService:
    """Runs code validation and facial verification for door access."""

    def __init__(self):
        _ensure_access_log_table()
        _ensure_face_training_table()
        self.camera_service = IPCameraService()
        self.face_service = FaceRecognitionService()

    def status(self) -> dict:
        cam_ok = False
        try:
            cam_ok = self.camera_service.check_camera()
        except Exception:
            cam_ok = False
        return {
            "status": "online",
            "camera": "ok" if cam_ok else "unavailable",
            "service": "U.O.R Django Access Backend",
            "metrics": {
                "face": self.face_service.get_runtime_stats(),
                "camera": self.camera_service.get_runtime_stats(),
            },
        }

    def validate_code(self, code: str) -> AccessResult:
        student = self._student_by_code(code)
        if not student:
            return self._invalid_code()
        return AccessResult(
            200,
            {
                "access": "pending_face",
                "code_valid": True,
                "name": self._student_name(student),
                "message": "Code valide. Regardez la camera.",
                "single_entry_only": True,
            },
        )

    def verify_code(self, code: str, *, client_ip: str = "unknown") -> AccessResult:
        student = self._student_by_code(code)
        if not student:
            return self._invalid_code()
        return self._perform_face_verification(student, client_ip=client_ip)

    def _student_by_code(self, code: str) -> dict | None:
        code = str(code or "").strip()
        if not code:
            return None
        return _get_student_by_code(code)

    def _perform_face_verification(self, student: dict, *, client_ip: str) -> AccessResult:
        student_id = int(student.get("id") or 0)
        student_name = self._student_name(student)
        required = max(1, min(FACE_MIN_MATCH_SUCCESSES, FACE_CAPTURE_ATTEMPTS))
        max_capture_calls = FACE_CAPTURE_ATTEMPTS + 3

        best_confidence = 0.0
        best_capture_meta = {}
        analyzed_count = 0
        capture_call = 0
        recognized_count = 0
        stale_skipped_count = 0
        had_frame = False
        had_fresh_frame = False
        denied_multiple_faces = False

        while analyzed_count < FACE_CAPTURE_ATTEMPTS and capture_call < max_capture_calls:
            capture_call += 1
            frame = self.camera_service.capture_frame()
            capture_meta = self.camera_service.get_last_capture_meta()

            if frame is None:
                pass
            else:
                had_frame = True
                if bool(capture_meta.get("frame_stale")):
                    stale_skipped_count += 1
                    self._pause_between_captures()
                    continue

                had_fresh_frame = True
                analysis = self.face_service.analyze_student(frame=frame, student=student) or {}
                analyzed_count += 1
                confidence = float(analysis.get("confidence") or 0.0)
                if confidence >= best_confidence:
                    best_confidence = confidence
                    best_capture_meta = dict(capture_meta or {})

                if analysis.get("multiple_faces_detected"):
                    denied_multiple_faces = True
                    break
                if analysis.get("recognized"):
                    recognized_count += 1
                    if recognized_count >= required:
                        break

            self._pause_between_captures()

        if not best_capture_meta:
            best_capture_meta = self.camera_service.get_last_capture_meta()

        if not had_frame:
            self._log(student_id, "DENIED_MULTIPLE", client_ip, "camera_unavailable")
            return AccessResult(200, {"access": "denied", "reason": "Camera IP non disponible", "camera": best_capture_meta})

        if had_frame and not had_fresh_frame:
            self._log(student_id, "DENIED_MULTIPLE", client_ip, "camera_stale_frames")
            return AccessResult(
                200,
                {
                    "access": "denied",
                    "reason": "Flux camera non temps reel",
                    "message": "La camera renvoie la meme image. Verifiez la source.",
                    "camera": best_capture_meta,
                    "stale_skipped": stale_skipped_count,
                },
            )

        if denied_multiple_faces:
            self._log(student_id, "DENIED_MULTIPLE", client_ip, "multiple_faces_detected")
            return AccessResult(
                200,
                {
                    "access": "denied",
                    "reason": "Plusieurs personnes detectees. Entree reservee a une seule personne.",
                    "name": student_name,
                    "single_entry_only": True,
                    "camera": best_capture_meta,
                },
            )

        if recognized_count >= required:
            self._log(
                student_id,
                "GRANTED",
                client_ip,
                f"confidence={best_confidence:.3f}; matches={recognized_count}/{FACE_CAPTURE_ATTEMPTS}",
                face_validated=True,
            )
            return AccessResult(
                200,
                {
                    "access": "granted",
                    "name": student_name,
                    "confidence": round(best_confidence, 3),
                    "matches": recognized_count,
                    "captures": FACE_CAPTURE_ATTEMPTS,
                    "required_matches": required,
                    "single_entry_only": True,
                    "message": "Acces accorde. Entrez seul, s'il vous plait.",
                    "camera": best_capture_meta,
                },
            )

        self._log(
            student_id,
            "DENIED_FACE",
            client_ip,
            f"best_confidence={best_confidence:.3f}; matches={recognized_count}/{FACE_CAPTURE_ATTEMPTS}",
        )
        return AccessResult(
            200,
            {
                "access": "denied",
                "reason": "Visage non reconnu",
                "name": student_name,
                "matches": recognized_count,
                "captures": FACE_CAPTURE_ATTEMPTS,
                "required_matches": required,
                "camera": best_capture_meta,
            },
        )

    def _log(
        self,
        student_id: int,
        status: str,
        client_ip: str,
        notes: str,
        *,
        face_validated: bool = False,
    ) -> None:
        _log_access_attempt(
            student_id=student_id,
            status=status,
            access_point="DJANGO_HTTP",
            password_validated=True,
            face_validated=face_validated,
            finance_validated=True,
            ip_address=client_ip,
            notes=notes,
        )

    @staticmethod
    def _pause_between_captures() -> None:
        if FACE_CAPTURE_RETRY_DELAY_MS > 0:
            time.sleep(FACE_CAPTURE_RETRY_DELAY_MS / 1000.0)

    @staticmethod
    def _student_name(student: dict) -> str:
        return f"{student.get('firstname', '')} {student.get('lastname', '')}".strip()

    @staticmethod
    def _invalid_code() -> AccessResult:
        return AccessResult(
            200,
            {
                "access": "denied",
                "code_valid": False,
                "reason": "Code invalide ou expire",
                "message": "Votre code est incorrect.",
            },
        )


_service_lock = threading.Lock()
_service: AccessVerificationService | None = None


def get_access_service() -> AccessVerificationService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = AccessVerificationService()
    return _service

