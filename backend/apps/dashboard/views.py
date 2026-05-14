"""Dashboard data endpoints."""
from __future__ import annotations

from django.http import HttpRequest, JsonResponse

from apps.common.decorators import admin_required, api_methods
from apps.common.legacy import services
from apps.common.responses import json_ok


def _dashboard():
    return services()["dashboard"]


@api_methods("GET")
@admin_required
def summary(request: HttpRequest) -> JsonResponse:
    svc = _dashboard()
    data = {
        "total_students": svc.get_total_students(),
        "eligible_students": svc.get_eligible_students(),
        "non_eligible_students": svc.get_non_eligible_students(),
        "access_granted": svc.get_access_granted(),
        "access_denied": svc.get_access_denied(),
        "revenue": svc.get_revenue_collected(),
        "completion": svc.get_degree_of_completion(),
        "payment_status": svc.get_students_by_payment_status(),
    }
    return json_ok(data)


@api_methods("GET")
@admin_required
def recent_activities(request: HttpRequest) -> JsonResponse:
    limit = _safe_int(request.GET.get("limit"), default=8, minimum=1, maximum=50)
    return json_ok(_dashboard().get_recent_activities(limit))


@api_methods("GET")
@admin_required
def faculty_stats(request: HttpRequest) -> JsonResponse:
    with_photos = str(request.GET.get("with_photos") or "").lower() == "true"
    svc = _dashboard()
    rows = svc.get_faculty_stats_with_photos() if with_photos else svc.get_faculty_stats()
    return json_ok(rows)


@api_methods("GET")
@admin_required
def finance_snapshot(request: HttpRequest) -> JsonResponse:
    svc = _dashboard()
    limit = _safe_int(request.GET.get("limit"), default=200, minimum=1, maximum=500)
    data = {
        "revenue": svc.get_revenue_collected(),
        "payment_status": svc.get_students_by_payment_status(),
        "payments": svc.get_students_finance_overview(limit),
    }
    return json_ok(data)


def _safe_int(value, *, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except Exception:
        return default
