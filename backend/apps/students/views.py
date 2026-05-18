"""Student management endpoints."""
from __future__ import annotations

import base64
import mimetypes
import os
import re
from pathlib import Path
from uuid import uuid4

import numpy as np
from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse

from apps.common.decorators import admin_required, api_methods
from apps.common.legacy import services
from apps.common.responses import json_error, json_ok, parse_json
from apps.common.serialization import add_photo_flags, to_jsonable


def _student_service():
    svc = services()["student"]
    ensure = getattr(svc, "ensure_student_identity_columns", None)
    if callable(ensure):
        ensure()
    return svc


def _auth_service():
    return services()["auth"]


def _finance_service():
    return services()["finance"]


def _academic_service():
    return services()["academic"]


@api_methods("GET", "POST")
@admin_required
def students(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        rows = _student_service().get_all_students_with_finance() or []
        return json_ok([_public_student(row) for row in rows])

    payload, error = parse_json(request)
    if error:
        return error
    return _create_student(payload)


@api_methods("GET", "PATCH", "DELETE")
@admin_required
def student_detail(request: HttpRequest, student_id: int) -> JsonResponse:
    svc = _student_service()
    if request.method == "GET":
        student = svc.get_student_with_academics(student_id)
        if not student:
            return json_error("Etudiant introuvable", status=404, code="student_not_found")
        return json_ok(_public_student(student))

    if request.method == "DELETE":
        student = svc.get_student_with_academics(student_id)
        if not student:
            return json_error("Etudiant introuvable", status=404, code="student_not_found")
        ok = svc.deactivate_student(student.get("student_number"))
        if not ok:
            return json_error("Impossible de desactiver l'etudiant", status=400, code="deactivate_failed")
        return json_ok({"message": "Etudiant desactive"})

    payload, error = parse_json(request)
    if error:
        return error

    update_data = _student_update_payload(payload)
    try:
        photo_path, photo_blob, face_encoding = _extract_photo_payload(payload, student_id=student_id)
    except ValueError as exc:
        return json_error(str(exc), status=400, code="invalid_photo")
    if photo_path:
        update_data["passport_photo_path"] = photo_path
        update_data["passport_photo_blob"] = photo_blob

    if not update_data:
        return json_error("Aucune donnee a mettre a jour", status=400, code="empty_update")

    ok = svc.update_student(student_id, update_data)
    if not ok:
        return json_error("Mise a jour impossible", status=400, code="update_failed")
    if face_encoding is not None:
        svc.update_face_encoding(student_id, face_encoding)
    return json_ok(_public_student(svc.get_student_with_academics(student_id)))


@api_methods("POST")
@admin_required
def validate_photo(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    try:
        _validate_photo_payload(payload)
    except ValueError as exc:
        return json_error(str(exc), status=400, code="invalid_photo")
    return json_ok(
        {
            "valid": True,
            "message": "Photo valide. Un seul visage net et compatible avec la reconnaissance faciale a ete detecte.",
        }
    )


@api_methods("GET")
@admin_required
def student_photo(request: HttpRequest, student_id: int):
    from core.database.connection import DatabaseConnection

    rows = DatabaseConnection().execute_query(
        "SELECT passport_photo_path, passport_photo_blob FROM student WHERE id = %s LIMIT 1",
        (student_id,),
    )
    if not rows:
        return json_error("Photo introuvable", status=404, code="photo_not_found")
    row = rows[0]
    blob = row.get("passport_photo_blob")
    if blob:
        return HttpResponse(bytes(blob), content_type="image/jpeg")
    path = row.get("passport_photo_path")
    if path and os.path.exists(path):
        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        return FileResponse(open(path, "rb"), content_type=content_type)
    return json_error("Photo introuvable", status=404, code="photo_not_found")


@api_methods("GET", "POST")
@admin_required
def faculties(request: HttpRequest) -> JsonResponse:
    svc = _student_service()
    if request.method == "GET":
        return json_ok(svc.get_faculties() or [])
    payload, error = parse_json(request)
    if error:
        return error
    name = str(payload.get("name") or "").strip()
    if not name:
        return json_error("Nom de la faculte requis", status=400, code="missing_faculty_name")
    faculty_id = svc.create_faculty(name, payload.get("code"))
    if not faculty_id:
        return json_error("Creation faculte impossible", status=400, code="faculty_create_failed")
    return json_ok({"id": faculty_id}, status=201)


@api_methods("GET", "POST")
@admin_required
def departments(request: HttpRequest) -> JsonResponse:
    svc = _student_service()
    if request.method == "GET":
        faculty_id = request.GET.get("faculty_id")
        if faculty_id:
            return json_ok(svc.get_departments_by_faculty(int(faculty_id)) or [])
        return json_ok([])
    payload, error = parse_json(request)
    if error:
        return error
    name = str(payload.get("name") or "").strip()
    faculty_id = int(payload.get("faculty_id") or 0)
    if not name or not faculty_id:
        return json_error("Nom du departement et faculte requis", status=400, code="missing_department_data")
    department_id = svc.create_department(
        name,
        faculty_id,
        payload.get("code"),
    )
    if not department_id:
        return json_error("Creation departement impossible", status=400, code="department_create_failed")
    return json_ok({"id": department_id}, status=201)


@api_methods("GET", "POST")
@admin_required
def promotions(request: HttpRequest) -> JsonResponse:
    svc = _student_service()
    if request.method == "GET":
        department_id = request.GET.get("department_id")
        if department_id:
            return json_ok(svc.get_promotions_by_department(int(department_id)) or [])
        return json_ok(svc.get_promotions_with_fees() or [])
    payload, error = parse_json(request)
    if error:
        return error
    name = str(payload.get("name") or "").strip()
    department_id = int(payload.get("department_id") or 0)
    if not name or not department_id:
        return json_error("Nom de la promotion et departement requis", status=400, code="missing_promotion_data")
    promotion_id = svc.create_promotion(
        name,
        department_id,
        payload.get("year"),
    )
    if not promotion_id:
        return json_error("Creation promotion impossible", status=400, code="promotion_create_failed")
    return json_ok({"id": promotion_id}, status=201)


def _create_student(payload: dict) -> JsonResponse:
    from core.models.student import Student as LegacyStudent

    payload = _normalize_student_identity_payload(payload)
    active_year = _academic_service().get_active_year()
    if not active_year or not active_year.get("academic_year_id"):
        return json_error(
            "Configurez d'abord une annee academique active avant d'inscrire un etudiant.",
            status=400,
            code="no_active_academic_year",
        )
    payload["academic_year_id"] = active_year.get("academic_year_id")
    required = ["student_number", "firstname", "lastname", "postnom", "email", "promotion_id"]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        labels = {
            "student_number": "matricule",
            "firstname": "prenom",
            "lastname": "nom",
            "postnom": "postnom",
            "email": "email",
            "promotion_id": "promotion",
        }
        return json_error(
            f"Champs requis manquants: {', '.join(labels.get(key, key) for key in missing)}",
            status=400,
            code="missing_fields",
        )

    try:
        photo_path, photo_blob, face_encoding = _extract_photo_payload(payload, student_id=0, require_photo=True)
    except ValueError as exc:
        return json_error(str(exc), status=400, code="invalid_photo")
    student = LegacyStudent(
        student_number=str(payload["student_number"]).strip(),
        firstname=str(payload["firstname"]).strip(),
        lastname=str(payload["lastname"]).strip(),
        postnom=str(payload.get("postnom") or "").strip(),
        email=str(payload["email"]).strip(),
        phone_number=str(payload.get("phone_number") or "").strip() or None,
        promotion_id=int(payload["promotion_id"]),
        passport_photo_path=photo_path,
        passport_photo_blob=photo_blob,
        academic_year_id=payload.get("academic_year_id"),
    )
    student_id = _auth_service().register_student_with_face(student, None, face_encoding)
    if not student_id:
        return json_error(_auth_service().get_last_error() or "Inscription impossible", status=400)

    _finance_service().create_finance_profile(
        student_id,
        payload.get("threshold_required"),
        payload.get("academic_year_id"),
    )
    created = _student_service().get_student_with_academics(student_id)
    return json_ok(_public_student(created or {"id": student_id}), status=201)


def _student_update_payload(payload: dict) -> dict:
    payload = _normalize_student_identity_payload(payload)
    allowed = {
        "student_number",
        "firstname",
        "lastname",
        "postnom",
        "email",
        "phone_number",
        "promotion_id",
        "academic_year_id",
    }
    return {key: value for key, value in payload.items() if key in allowed}


def _normalize_student_identity_payload(payload: dict) -> dict:
    data = dict(payload or {})
    if data.get("prenom") is not None:
        data["firstname"] = str(data.get("prenom") or "").strip()
    if data.get("nom") is not None:
        data["lastname"] = str(data.get("nom") or "").strip()
    if data.get("postnom") is not None:
        data["postnom"] = str(data.get("postnom") or "").strip()
    return data


def _public_student(row: dict) -> dict:
    data = add_photo_flags(row or {})
    lastname = str(data.get("lastname") or "").strip()
    postnom = data.get("postnom")
    if postnom is None:
        lastname, postnom = _split_legacy_lastname(lastname)
    data["nom"] = lastname
    data["postnom"] = str(postnom or "").strip()
    data["prenom"] = str(data.get("firstname") or "").strip()
    data["student_name"] = " ".join(part for part in [data["nom"], data["postnom"], data["prenom"]] if part)
    return data


def _split_legacy_lastname(value: str) -> tuple[str, str]:
    parts = str(value or "").strip().split()
    if len(parts) <= 1:
        return str(value or "").strip(), ""
    return parts[0], " ".join(parts[1:])


def _extract_photo_payload(
    payload: dict,
    *,
    student_id: int,
    require_photo: bool = False,
) -> tuple[str | None, bytes | None, bytes | None]:
    photo_b64 = payload.get("photo_base64")
    if not photo_b64:
        if require_photo:
            raise ValueError(
                "Photo passeport obligatoire. Ajoutez une photo nette, individuelle et compatible avec la reconnaissance faciale."
            )
        return None, None, None

    raw = str(photo_b64)
    if "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        photo_blob = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError("Photo base64 invalide") from exc
    ext = _clean_ext(payload.get("photo_extension") or ".jpg")
    student_number = str(payload.get("student_number") or f"student_{student_id or 'new'}").strip()
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", student_number) or f"student_{student_id or 'new'}"
    storage_dir = Path(settings.LEGACY_STORAGE_ROOT) / "student_photos"
    storage_dir.mkdir(parents=True, exist_ok=True)
    temp_path = storage_dir / f".pending_{safe_name}_{uuid4().hex}{ext}"
    final_path = storage_dir / f"{safe_name}_{uuid4().hex}{ext}"

    try:
        temp_path.write_bytes(photo_blob)
        face_encoding = _validated_face_encoding_from_path(str(temp_path), student_id or 1)
        temp_path.replace(final_path)
    except ValueError:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise ValueError("Impossible de sauvegarder la photo de l'etudiant") from exc

    return str(final_path), photo_blob, face_encoding


def _validate_photo_payload(payload: dict) -> None:
    photo_b64 = payload.get("photo_base64")
    if not photo_b64:
        raise ValueError("Ajoutez une photo avant de lancer la verification.")

    raw = str(photo_b64)
    if "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        photo_blob = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError("Photo invalide. Choisissez une image JPG, PNG ou BMP lisible.") from exc

    ext = _clean_ext(payload.get("photo_extension") or ".jpg")
    storage_dir = Path(settings.LEGACY_STORAGE_ROOT) / "student_photos"
    storage_dir.mkdir(parents=True, exist_ok=True)
    temp_path = storage_dir / f".validation_{uuid4().hex}{ext}"
    try:
        temp_path.write_bytes(photo_blob)
        _validated_face_encoding_from_path(str(temp_path), 1)
    finally:
        temp_path.unlink(missing_ok=True)


def _validated_face_encoding_from_path(photo_path: str, student_id: int) -> bytes:
    try:
        from app.services.auth.face_recognition_service import FaceRecognitionService

        face_service = FaceRecognitionService()
        if not face_service.is_available():
            raise ValueError("Service de reconnaissance faciale indisponible. La photo ne peut pas etre validee.")
        is_valid, validation_message = face_service.validate_passport_photo(photo_path)
        if not is_valid:
            raise ValueError(validation_message)
        encoding = face_service.register_face(photo_path, int(student_id))
        if isinstance(encoding, np.ndarray):
            return encoding.tobytes()
    except ValueError:
        raise
    except RuntimeError as exc:
        raise ValueError("Service de reconnaissance faciale indisponible. La photo ne peut pas etre validee.") from exc
    except Exception as exc:
        raise ValueError("Impossible de valider la photo avec la reconnaissance faciale.") from exc
    raise ValueError("Photo invalide: un visage unique, net et bien cadre est obligatoire.")


def _clean_ext(value: str) -> str:
    ext = str(value or ".jpg").lower().strip()
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext not in {".jpg", ".jpeg", ".png", ".bmp"}:
        raise ValueError("Format photo non supporte. Utilisez JPG, JPEG, PNG ou BMP.")
    return ext
