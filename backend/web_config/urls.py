"""URL routing for the U.O.R web backend."""
from django.urls import include, path

from apps.access_control import views as access_views
from apps.accounts import views as account_views
from apps.common.responses import health

urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/students/", include("apps.students.urls")),
    path("api/finance/", include("apps.finance.urls")),
    path("api/access/", include("apps.access_control.urls")),
    path("api/transfers/", include("apps.transfers.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/academics/", include("apps.academics.urls")),
    path("api/v1/", include("apps.transfers.partner_urls")),
    path("access-request/decision/", account_views.access_request_decision, name="access-request-decision"),
    # Compatibility endpoints for the ESP32 firmware and existing scripts.
    path("status/", access_views.status, name="access-status-compat"),
    path("validate_code/", access_views.validate_code, name="validate-code-compat"),
    path("verify_face/", access_views.verify_face, name="verify-face-compat"),
    path("verify_code/", access_views.verify_code, name="verify-code-compat"),
]
