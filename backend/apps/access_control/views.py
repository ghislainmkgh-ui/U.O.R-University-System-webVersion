"""Django views for ESP32 access and admin access logs."""
from __future__ import annotations

from django.http import HttpRequest, JsonResponse

from apps.common.decorators import admin_required, api_methods
from apps.common.legacy import services
from apps.common.responses import json_error, json_ok, parse_json
from apps.common.serialization import add_photo_flags

from .services import get_access_service


@api_methods("GET")
def status(request: HttpRequest) -> JsonResponse:
    return JsonResponse(get_access_service().status(), json_dumps_params={"ensure_ascii": False})


@api_methods("POST")
def validate_code(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    code = str(payload.get("code") or "").strip()
    if not code:
        return json_error("Code manquant", status=400, code="missing_code")
    result = get_access_service().validate_code(code)
    return JsonResponse(result.body, status=result.status_code, json_dumps_params={"ensure_ascii": False})


@api_methods("POST")
def verify_face(request: HttpRequest) -> JsonResponse:
    return verify_code(request)


@api_methods("POST")
def verify_code(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    code = str(payload.get("code") or "").strip()
    if not code:
        return json_error("Code manquant", status=400, code="missing_code")
    client_ip = request.META.get("REMOTE_ADDR") or "unknown"
    result = get_access_service().verify_code(code, client_ip=client_ip)
    return JsonResponse(result.body, status=result.status_code, json_dumps_params={"ensure_ascii": False})


@api_methods("GET")
@admin_required
def access_logs(request: HttpRequest) -> JsonResponse:
    limit = _safe_int(request.GET.get("limit"), default=200, minimum=1, maximum=1000)
    rows = services()["dashboard"].get_access_logs_with_students(limit) or []
    return json_ok([add_photo_flags(row) for row in rows])


def _safe_int(value, *, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except Exception:
        return default

