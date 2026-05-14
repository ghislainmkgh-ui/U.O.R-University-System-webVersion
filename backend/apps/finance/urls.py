from django.urls import path

from . import views

urlpatterns = [
    path("overview/", views.overview, name="finance-overview"),
    path("payments/", views.record_payment, name="record-payment"),
    path("students/<int:student_id>/history/", views.payment_history, name="payment-history"),
    path("students/<int:student_id>/access-code/", views.latest_access_code, name="latest-access-code"),
    path("students/<int:student_id>/access-code/resend/", views.resend_access_code, name="resend-access-code"),
    path("academic-years/", views.academic_years, name="academic-years"),
    path("academic-years/<int:academic_year_id>/thresholds/", views.update_academic_year_thresholds, name="year-thresholds"),
    path("exam-periods/", views.exam_periods, name="exam-periods"),
    path("exam-periods/<int:period_id>/", views.delete_exam_period, name="delete-exam-period"),
    path("promotions/", views.promotions_financials, name="promotions-financials"),
    path("promotions/<int:promotion_id>/financials/", views.update_promotion_financials, name="update-promotion-financials"),
    path("academic-year-migration/", views.academic_year_migration, name="academic-year-migration"),
    path("academic-year-migration/audit/", views.academic_year_migration_audit, name="academic-year-migration-audit"),
]
