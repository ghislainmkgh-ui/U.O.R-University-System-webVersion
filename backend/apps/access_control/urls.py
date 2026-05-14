from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.status, name="access-status"),
    path("validate-code/", views.validate_code, name="validate-code"),
    path("verify-face/", views.verify_face, name="verify-face"),
    path("verify-code/", views.verify_code, name="verify-code"),
    path("logs/", views.access_logs, name="access-logs"),
]

