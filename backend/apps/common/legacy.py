"""Helpers that bridge Django to the web-local legacy service snapshot."""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from django.conf import settings


def ensure_legacy_path() -> Path:
    root = Path(settings.WEB_LEGACY_SRC)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


@lru_cache(maxsize=1)
def services() -> dict:
    """Lazy-load copied service modules after Django has configured settings."""
    ensure_legacy_path()
    from app.services.auth.authentication_service import AuthenticationService
    from app.services.dashboard_service import DashboardService
    from app.services.finance.academic_year_service import AcademicYearService
    from app.services.finance.finance_service import FinanceService
    from app.services.integration.notification_service import NotificationService
    from app.services.integration.esp32_status_service import ESP32StatusService
    from app.services.student.student_service import StudentService
    from app.services.transfer.transfer_service import TransferService

    return {
        "auth": AuthenticationService(),
        "dashboard": DashboardService(),
        "student": StudentService(),
        "finance": FinanceService(),
        "academic": AcademicYearService(),
        "notification": NotificationService(),
        "esp32": ESP32StatusService(),
        "transfer": TransferService(),
    }
