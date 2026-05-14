from __future__ import annotations

import os
import sys

from django.apps import AppConfig


class RuntimeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.runtime"
    label = "runtime"

    def ready(self) -> None:
        if not _should_bootstrap_runtime_services():
            return

        from .services import bootstrap_runtime_services

        bootstrap_runtime_services()


def _should_bootstrap_runtime_services() -> bool:
    argv = {arg.lower() for arg in sys.argv}
    if "runserver" not in argv:
        return False

    if "--noreload" in argv:
        return True

    return os.environ.get("RUN_MAIN") == "true"
