from django.urls import path

from . import views

urlpatterns = [
    path("summary/", views.summary, name="reports-summary"),
    path("students/", views.students_report, name="students-report"),
    path("finance/", views.finance_report, name="finance-report"),
    path("access-logs/", views.access_logs_report, name="access-logs-report"),
]
