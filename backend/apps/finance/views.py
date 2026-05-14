"""Finance, academic-year and exam-period endpoints."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.http import HttpRequest, JsonResponse

from apps.common.decorators import admin_required, api_methods, elevated_admin_required, super_admin_required
from apps.common.legacy import services
from apps.common.responses import json_error, json_ok, parse_json
from apps.common.serialization import add_photo_flags


def _finance():
    return services()["finance"]


def _academic():
    return services()["academic"]


def _students():
    return services()["student"]


def _dashboard():
    return services()["dashboard"]


@api_methods("GET")
@admin_required
def overview(request: HttpRequest) -> JsonResponse:
    limit = _safe_int(request.GET.get("limit"), default=200, minimum=1, maximum=500)
    rows = _dashboard().get_students_finance_overview(limit) or []
    data = {
        "payment_status": _dashboard().get_students_by_payment_status(),
        "revenue": _dashboard().get_revenue_collected(),
        "students": [add_photo_flags(row) for row in rows],
    }
    return json_ok(data)


@api_methods("POST")
@admin_required
def record_payment(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    student_id = int(payload.get("student_id") or 0)
    amount = _decimal(payload.get("amount"))
    if not student_id or amount is None or amount <= 0:
        return json_error("Etudiant et montant valides requis", status=400, code="invalid_payment")
    ok = _finance().record_payment(student_id, amount)
    if not ok:
        return json_error(_payment_failure_message(_finance().get_last_error()), status=400, code="payment_failed")
    return json_ok(
        {
            "finance": _finance().get_student_finance(student_id),
            "latest_access_code": _finance().get_latest_access_code(student_id),
        },
        status=201,
    )


@api_methods("GET")
@admin_required
def payment_history(request: HttpRequest, student_id: int) -> JsonResponse:
    limit = _safe_int(request.GET.get("limit"), default=100, minimum=1, maximum=500)
    return json_ok(_finance().get_student_payment_history(student_id, limit))


@api_methods("GET")
@admin_required
def latest_access_code(request: HttpRequest, student_id: int) -> JsonResponse:
    return json_ok(_finance().get_latest_access_code(student_id) or {})


@api_methods("POST")
@admin_required
def resend_access_code(request: HttpRequest, student_id: int) -> JsonResponse:
    ok = _finance().resend_latest_access_code_notification(student_id)
    if not ok:
        detail = _finance().get_last_error() or "unknown"
        return json_error(
            _access_code_resend_message(detail),
            status=400,
            code="access_code_resend_failed",
        )
    return json_ok({"message": "Code renvoye a l'etudiant"})


@api_methods("GET", "POST")
@elevated_admin_required
def academic_years(request: HttpRequest) -> JsonResponse:
    svc = _academic()
    if request.method == "GET":
        include_financials = str(request.GET.get("financials") or "").lower() == "true"
        rows = svc.get_years_financials() if include_financials else svc.get_years()
        return json_ok(rows or [])

    payload, error = parse_json(request)
    if error:
        return error
    year_id = svc.create_year_simple(
        str(payload.get("year_name") or payload.get("name") or "").strip(),
        threshold_amount=float(payload.get("threshold_amount") or 0),
        final_fee=float(payload.get("final_fee") or 0),
        partial_valid_days=int(payload.get("partial_valid_days") or 30),
    )
    if not year_id:
        return json_error("Creation annee academique impossible", status=400, code="year_create_failed")
    return json_ok({"academic_year_id": year_id}, status=201)


@api_methods("PATCH", "POST")
@super_admin_required
def update_academic_year_thresholds(request: HttpRequest, academic_year_id: int) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    threshold = _decimal(payload.get("threshold_amount"))
    final_fee = _decimal(payload.get("final_fee"))
    partial_days = int(payload.get("partial_valid_days") or 30)
    if threshold is None or final_fee is None:
        return json_error("Seuil et frais finaux requis", status=400, code="invalid_thresholds")
    ok = _finance().update_financial_thresholds(academic_year_id, threshold, final_fee, partial_days)
    if not ok:
        return json_error("Mise a jour des seuils impossible", status=400, code="threshold_update_failed")
    return json_ok({"message": "Seuils mis a jour"})


@api_methods("GET", "POST")
@elevated_admin_required
def exam_periods(request: HttpRequest) -> JsonResponse:
    svc = _academic()
    if request.method == "GET":
        academic_year_id = int(request.GET.get("academic_year_id") or 0)
        if not academic_year_id:
            return json_error("academic_year_id requis", status=400, code="missing_academic_year")
        return json_ok(svc.get_exam_periods(academic_year_id) or [])

    payload, error = parse_json(request)
    if error:
        return error
    try:
        start_date = date.fromisoformat(str(payload.get("start_date")))
        end_date = date.fromisoformat(str(payload.get("end_date")))
    except ValueError:
        return json_error("Dates invalides. Format attendu: YYYY-MM-DD", status=400, code="invalid_dates")

    ok = svc.add_exam_period(
        int(payload.get("academic_year_id") or 0),
        str(payload.get("period_name") or payload.get("name") or "").strip(),
        start_date,
        end_date,
    )
    if not ok:
        return json_error("Creation periode examen impossible", status=400, code="exam_period_failed")
    return json_ok({"message": "Periode creee"}, status=201)


@api_methods("DELETE")
@elevated_admin_required
def delete_exam_period(request: HttpRequest, period_id: int) -> JsonResponse:
    ok = _academic().delete_exam_period(period_id)
    if not ok:
        return json_error("Suppression impossible", status=400, code="delete_period_failed")
    return json_ok({"message": "Periode supprimee"})


@api_methods("GET")
@elevated_admin_required
def promotions_financials(request: HttpRequest) -> JsonResponse:
    return json_ok(_students().get_promotions_with_fees() or [])


@api_methods("PATCH", "POST")
@super_admin_required
def update_promotion_financials(request: HttpRequest, promotion_id: int) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    fee = _decimal(payload.get("fee_usd") or payload.get("final_fee"))
    threshold = _decimal(payload.get("threshold_amount"))
    if fee is None or threshold is None:
        return json_error("Frais et seuil requis", status=400, code="invalid_financials")
    if threshold > fee:
        return json_error("Le seuil ne peut pas depasser les frais", status=400, code="threshold_over_fee")
    ok = _students().update_promotion_financials(promotion_id, fee, threshold)
    if not ok:
        return json_error("Mise a jour promotion impossible", status=400, code="promotion_update_failed")
    return json_ok(_students().get_promotion_details(promotion_id))


@api_methods("POST")
@super_admin_required
def academic_year_migration(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    result = _students().migrate_students_to_academic_year(
        from_academic_year_id=int(payload.get("from_academic_year_id") or 0),
        to_academic_year_id=int(payload.get("to_academic_year_id") or 0),
        eligible_only=bool(payload.get("eligible_only", False)),
        dry_run=bool(payload.get("dry_run", False)),
    )
    if result.get("success") and not result.get("dry_run"):
        user = getattr(request, "current_user", {}) or {}
        _students().log_academic_year_migration_audit(
            actor_identifier=str(user.get("email") or user.get("username") or user.get("id") or "web"),
            actor_role=str(user.get("role") or "super_admin"),
            from_academic_year_id=int(payload.get("from_academic_year_id") or 0),
            to_academic_year_id=int(payload.get("to_academic_year_id") or 0),
            eligible_only=bool(payload.get("eligible_only", False)),
            moved_student_ids=result.get("moved_student_ids") or [],
            eligible_student_ids=result.get("eligible_student_ids") or [],
        )
    status = 200 if result.get("success") else 400
    return json_ok(result, status=status) if result.get("success") else json_error(result.get("message"), status=status)


@api_methods("GET")
@super_admin_required
def academic_year_migration_audit(request: HttpRequest) -> JsonResponse:
    limit = _safe_int(request.GET.get("limit"), default=20, minimum=1, maximum=100)
    return json_ok(_students().get_recent_academic_year_migration_audit(limit))


def _decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _safe_int(value, *, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except Exception:
        return default


def _access_code_resend_message(detail: str) -> str:
    detail_lower = str(detail or "").lower()
    if "no_access_code" in detail_lower:
        return "Aucun code d'acces n'existe encore pour cet etudiant."
    if "expired" in detail_lower:
        return "Le dernier code d'acces est expire. Enregistrez un nouveau paiement valide ou regenerez un code."
    if "notification_failed" in detail_lower:
        return "Le code existe, mais l'envoi a echoue. Verifiez l'email, le numero WhatsApp et la configuration des notifications."
    return "Le code n'a pas pu etre envoye. Verifiez les contacts de l'etudiant et reessayez."


def _payment_failure_message(detail: str | None) -> str:
    detail_lower = str(detail or "").lower()
    if "overpayment" in detail_lower:
        return "Le paiement depasse le montant total des frais academiques. Verifiez le reste a payer avant d'enregistrer."
    if "no_active_fees" in detail_lower:
        return "Aucun frais academique actif n'est configure pour cette promotion."
    if "no_finance_profile" in detail_lower:
        return "Le profil financier de cet etudiant est introuvable."
    if "no_promotion_data" in detail_lower:
        return "Les informations de promotion de cet etudiant sont introuvables."
    return "Paiement refuse. Verifiez le montant et la situation financiere de l'etudiant."
