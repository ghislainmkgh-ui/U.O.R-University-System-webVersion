"""Inter-university transfer endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import wraps

import jwt
from django.conf import settings
from django.http import HttpRequest, JsonResponse

from apps.common.decorators import api_methods, elevated_admin_required
from apps.common.legacy import services
from apps.common.responses import json_error, json_ok, parse_json


def _transfer():
    return services()["transfer"]


def _generate_partner_token(university_code: str) -> str:
    now = datetime.utcnow()
    payload = {
        "university_code": university_code,
        "iat": now,
        "exp": now + timedelta(hours=24),
        "aud": "uor-transfer-api",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _partner_token_required(view):
    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return json_error("API token is missing", status=401, code="missing_api_token")
        try:
            payload = jwt.decode(
                header.split(" ", 1)[1].strip(),
                settings.SECRET_KEY,
                algorithms=["HS256"],
                audience="uor-transfer-api",
            )
        except jwt.ExpiredSignatureError:
            return json_error("Token has expired", status=401, code="token_expired")
        except jwt.InvalidTokenError:
            return json_error("Invalid token", status=401, code="invalid_token")
        request.university_code = payload.get("university_code")
        return view(request, *args, **kwargs)

    return wrapper


@api_methods("GET")
def partner_health(request: HttpRequest) -> JsonResponse:
    return json_ok(
        {
            "status": "healthy",
            "service": "U.O.R Transfer API",
            "version": "v1",
            "timestamp": datetime.now().isoformat(),
        }
    )


@api_methods("POST")
def partner_token(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    university_code = str(payload.get("university_code") or "").strip()
    api_key = str(payload.get("api_key") or "").strip()
    if not university_code or not api_key:
        return json_error("university_code et api_key requis", status=400, code="missing_partner_credentials")

    token = _generate_partner_token(university_code)
    return json_ok({"token": token, "expires_in": 86400, "token_type": "Bearer"})


@api_methods("POST")
@_partner_token_required
def partner_receive_transfer(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    for field in ("transfer_metadata", "student_info", "academic_records"):
        if field not in payload:
            return json_error(f"Champ requis manquant: {field}", status=400, code="missing_transfer_field")
    ok, result = _transfer().receive_transfer_request(payload, target_promotion_id=None)
    if not ok:
        return json_error(result, status=400, code="receive_transfer_failed")
    return json_ok(
        {"request_code": result, "message": "Transfer request received and pending review", "status": "PENDING_REVIEW"},
        status=201,
    )


@api_methods("POST")
@_partner_token_required
def partner_send_transfer(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    student_id = int(payload.get("student_id") or 0)
    if not student_id:
        return json_error("student_id requis", status=400, code="missing_student_id")
    package = _transfer().prepare_student_transfer_package(
        student_id=student_id,
        include_documents=bool(payload.get("include_documents", True)),
    )
    if not package:
        return json_error("Package transfert impossible", status=500, code="package_failed")
    return json_ok(
        {
            "transfer_code": package["transfer_metadata"]["transfer_code"],
            "package": package,
            "message": "Transfer package prepared successfully",
        }
    )


@api_methods("GET")
@_partner_token_required
def partner_transfer_status(request: HttpRequest, transfer_code: str) -> JsonResponse:
    columns = _table_columns("transfer_history")
    delivery_status_select = "delivery_status" if "delivery_status" in columns else "NULL AS delivery_status"
    delivery_message_select = "delivery_message" if "delivery_message" in columns else "NULL AS delivery_message"
    rows = _query(
        f"""
        SELECT transfer_code, status, {delivery_status_select}, {delivery_message_select}, updated_at
        FROM transfer_history
        WHERE transfer_code = %s
        LIMIT 1
        """,
        (transfer_code,),
    )
    if not rows:
        return json_error("Transfert introuvable", status=404, code="transfer_not_found")
    return json_ok(rows[0])


@api_methods("GET")
@_partner_token_required
def partner_universities(request: HttpRequest) -> JsonResponse:
    rows = _query(
        """
        SELECT university_name, university_code, country, city, trust_level
        FROM partner_university
        WHERE is_active = TRUE
        ORDER BY university_name
        """
    )
    return json_ok({"count": len(rows), "universities": rows})


@api_methods("GET")
@elevated_admin_required
def pending_requests(request: HttpRequest) -> JsonResponse:
    return json_ok(_transfer().get_pending_transfer_requests() or [])


@api_methods("GET")
@elevated_admin_required
def history(request: HttpRequest) -> JsonResponse:
    limit = _safe_int(request.GET.get("limit"), default=50, minimum=1, maximum=500)
    student_id = request.GET.get("student_id")
    return json_ok(_transfer().get_transfer_history(int(student_id), limit) if student_id else _transfer().get_transfer_history(limit=limit))


@api_methods("POST")
@elevated_admin_required
def initiate_outgoing(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    user = getattr(request, "current_user", {}) or {}
    ok, result = _transfer().initiate_outgoing_transfer(
        student_id=int(payload.get("student_id") or 0),
        destination_university=str(payload.get("destination_university") or "").strip(),
        destination_code=str(payload.get("destination_university_code") or payload.get("destination_code") or "").strip(),
        initiated_by=str(user.get("email") or user.get("username") or "web"),
        include_documents=bool(payload.get("include_documents", True)),
        notes=payload.get("notes"),
    )
    if not ok:
        return json_error(result, status=400, code="outgoing_transfer_failed")
    return json_ok({"transfer_code": result}, status=201)


@api_methods("POST")
@elevated_admin_required
def approve_incoming(request: HttpRequest, request_id: int) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    user = getattr(request, "current_user", {}) or {}
    ok, result = _transfer().approve_incoming_transfer(
        request_id=request_id,
        approved_by=str(user.get("email") or user.get("username") or "web"),
        target_promotion_id=int(payload.get("target_promotion_id") or 0),
        approval_notes=payload.get("approval_notes") or payload.get("notes"),
    )
    if not ok:
        return json_error(result, status=400, code="incoming_approve_failed")
    return json_ok({"student_id": result})


@api_methods("POST")
@elevated_admin_required
def reject_incoming(request: HttpRequest, request_id: int) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    user = getattr(request, "current_user", {}) or {}
    ok = _transfer().reject_incoming_transfer(
        request_id=request_id,
        rejected_by=str(user.get("email") or user.get("username") or "web"),
        rejection_reason=str(payload.get("reason") or payload.get("notes") or ""),
    )
    if not ok:
        return json_error("Rejet impossible", status=400, code="incoming_reject_failed")
    return json_ok({"message": "Demande rejetee"})


@api_methods("GET")
@elevated_admin_required
def partners(request: HttpRequest) -> JsonResponse:
    columns = _table_columns("partner_university")
    api_endpoint_select = "api_endpoint" if "api_endpoint" in columns else "NULL AS api_endpoint"
    api_url_select = "api_url" if "api_url" in columns else "NULL AS api_url"
    rows = _query(
        f"""
        SELECT id, university_name, university_code, country, city, {api_endpoint_select}, {api_url_select},
               trust_level, is_active, contact_email, contact_phone
        FROM partner_university
        ORDER BY university_name
        """
    )
    return json_ok(rows)


@api_methods("GET", "PATCH", "POST")
@elevated_admin_required
def partner_api_url(request: HttpRequest, university_code: str) -> JsonResponse:
    columns = _table_columns("partner_university")
    api_endpoint_select = "api_endpoint" if "api_endpoint" in columns else "NULL AS api_endpoint"
    api_url_select = "api_url" if "api_url" in columns else "NULL AS api_url"
    if request.method == "GET":
        rows = _query(
            f"SELECT university_code, {api_endpoint_select}, {api_url_select} FROM partner_university WHERE university_code = %s LIMIT 1",
            (university_code,),
        )
        return json_ok(rows[0] if rows else {})

    payload, error = parse_json(request)
    if error:
        return error
    api_url = str(payload.get("api_url") or payload.get("api_endpoint") or "").strip()
    if not api_url:
        return json_error("api_url requis", status=400, code="missing_api_url")
    set_parts = []
    params = []
    if "api_url" in columns:
        set_parts.append("api_url = %s")
        params.append(api_url)
    if "api_endpoint" in columns:
        set_parts.append("api_endpoint = %s")
        params.append(api_url)
    if "updated_at" in columns:
        set_parts.append("updated_at = NOW()")
    if not set_parts:
        return json_error("Aucune colonne API disponible sur partner_university", status=400, code="api_column_missing")
    params.append(university_code)
    _execute(
        f"UPDATE partner_university SET {', '.join(set_parts)} WHERE university_code = %s",
        tuple(params),
    )
    return json_ok({"university_code": university_code, "api_url": api_url})


@api_methods("GET")
@elevated_admin_required
def transfer_package(request: HttpRequest, transfer_code: str) -> JsonResponse:
    rows = _query(
        "SELECT transfer_data_json FROM transfer_history WHERE transfer_code = %s LIMIT 1",
        (transfer_code,),
    )
    if not rows or not rows[0].get("transfer_data_json"):
        return json_error("Package introuvable", status=404, code="package_not_found")
    return json_ok({"transfer_code": transfer_code, "package_json": rows[0]["transfer_data_json"]})


def _query(query: str, params: tuple = ()) -> list[dict]:
    db = _transfer().db
    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall() or []
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.close_connection(conn)


def _execute(query: str, params: tuple = ()) -> None:
    db = _transfer().db
    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.close_connection(conn)


def _table_columns(table_name: str) -> set[str]:
    rows = _query(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        """,
        (table_name,),
    )
    return {row.get("COLUMN_NAME") for row in rows if row.get("COLUMN_NAME")}


def _safe_int(value, *, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except Exception:
        return default
