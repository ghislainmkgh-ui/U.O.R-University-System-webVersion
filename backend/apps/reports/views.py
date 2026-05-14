from __future__ import annotations

from django.http import HttpRequest, JsonResponse

from apps.common.decorators import admin_required, api_methods
from apps.common.legacy import services
from apps.common.responses import json_ok
from apps.common.serialization import add_photo_flags

from .exports import csv_response, wants_csv


def _dashboard():
    return services()["dashboard"]


def _students():
    return services()["student"]


@api_methods("GET")
@admin_required
def summary(request: HttpRequest) -> JsonResponse:
    dashboard = _dashboard()
    return json_ok(
        {
            "total_students": dashboard.get_total_students(),
            "eligible_students": dashboard.get_eligible_students(),
            "non_eligible_students": dashboard.get_non_eligible_students(),
            "access_granted_today": dashboard.get_access_granted(),
            "access_denied_today": dashboard.get_access_denied(),
            "revenue": dashboard.get_revenue_collected(),
            "available_reports": [
                "students",
                "finance",
                "access_logs",
            ],
            "available_formats": ["json", "csv"],
        }
    )


@api_methods("GET")
@admin_required
def students_report(request: HttpRequest):
    rows = _students().get_all_students_with_finance() or []
    rows = [_add_report_flags(add_photo_flags(row)) for row in rows]
    rows = _filter_students(rows, request.GET.get("status"))
    rows = _filter_by_ids(rows, request)

    if wants_csv(request):
        return csv_response("uor_students_report.csv", rows, _student_columns())
    return json_ok({"count": len(rows), "students": rows})


@api_methods("GET")
@admin_required
def finance_report(request: HttpRequest):
    limit = _safe_int(request.GET.get("limit"), default=500, minimum=1, maximum=2000)
    rows = _dashboard().get_students_finance_overview(limit) or []
    rows = [_add_report_flags(add_photo_flags(row)) for row in rows]
    rows = _filter_students(rows, request.GET.get("status"))
    rows = _filter_by_ids(rows, request)

    if wants_csv(request):
        return csv_response("uor_finance_report.csv", rows, _finance_columns())
    return json_ok({"count": len(rows), "students": rows})


@api_methods("GET")
@admin_required
def access_logs_report(request: HttpRequest):
    limit = _safe_int(request.GET.get("limit"), default=500, minimum=1, maximum=2000)
    rows = _dashboard().get_access_logs_with_students(limit) or []
    rows = [add_photo_flags(row) for row in rows]
    rows = _filter_access_logs(rows, request.GET.get("status"))

    if wants_csv(request):
        return csv_response("uor_access_logs_report.csv", rows, _access_log_columns())
    return json_ok({"count": len(rows), "access_logs": rows})


def _filter_students(rows: list[dict], status: str | None) -> list[dict]:
    status = str(status or "all").strip().lower()
    if status in {"all", ""}:
        return rows
    if status == "eligible":
        return [row for row in rows if bool(row.get("is_eligible"))]
    if status in {"non_eligible", "not_eligible"}:
        return [row for row in rows if not bool(row.get("is_eligible"))]
    if status == "paid":
        return [row for row in rows if _money(row.get("amount_paid")) > 0]
    if status in {"never_paid", "unpaid"}:
        return [row for row in rows if _money(row.get("amount_paid")) <= 0]
    return rows


def _filter_by_ids(rows: list[dict], request: HttpRequest) -> list[dict]:
    filters = {
        "faculty_id": request.GET.get("faculty_id"),
        "department_id": request.GET.get("department_id"),
        "promotion_id": request.GET.get("promotion_id"),
    }
    filtered = rows
    for key, value in filters.items():
        if value not in (None, ""):
            filtered = [row for row in filtered if str(row.get(key) or "") == str(value)]
    return filtered


def _filter_access_logs(rows: list[dict], status: str | None) -> list[dict]:
    status = str(status or "all").strip().upper()
    if status in {"ALL", ""}:
        return rows
    if status == "DENIED":
        return [row for row in rows if str(row.get("status") or "").upper() != "GRANTED"]
    return [row for row in rows if str(row.get("status") or "").upper() == status]


def _add_report_flags(row: dict) -> dict:
    amount_paid = _money(row.get("amount_paid"))
    row["payment_status"] = "eligible" if bool(row.get("is_eligible")) else "paid" if amount_paid > 0 else "never_paid"
    return row


def _money(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value, *, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except Exception:
        return default


def _student_columns() -> list[tuple[str, str]]:
    return [
        ("student_number", "Matricule"),
        ("firstname", "Prenom"),
        ("lastname", "Nom"),
        ("email", "Email"),
        ("phone_number", "Telephone"),
        ("faculty_name", "Faculte"),
        ("department_name", "Departement"),
        ("promotion_name", "Promotion"),
        ("academic_year_name", "Annee academique"),
        ("payment_status", "Statut paiement"),
        ("has_photo", "Photo"),
    ]


def _finance_columns() -> list[tuple[str, str]]:
    return [
        ("student_number", "Matricule"),
        ("firstname", "Prenom"),
        ("lastname", "Nom"),
        ("faculty_name", "Faculte"),
        ("department_name", "Departement"),
        ("promotion_name", "Promotion"),
        ("amount_paid", "Montant paye"),
        ("threshold_required", "Seuil requis"),
        ("promotion_fee", "Frais promotion"),
        ("is_eligible", "Eligible"),
        ("payment_status", "Statut paiement"),
    ]


def _access_log_columns() -> list[tuple[str, str]]:
    return [
        ("created_at", "Date"),
        ("student_number", "Matricule"),
        ("firstname", "Prenom"),
        ("lastname", "Nom"),
        ("access_point", "Point acces"),
        ("status", "Resultat"),
        ("password_validated", "Mot de passe"),
        ("face_validated", "Visage"),
        ("finance_validated", "Finance"),
        ("ip_address", "Adresse IP"),
        ("notes", "Notes"),
    ]
