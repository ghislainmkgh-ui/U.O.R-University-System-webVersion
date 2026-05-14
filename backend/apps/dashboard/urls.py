from django.urls import path

from . import views

urlpatterns = [
    path("summary/", views.summary, name="dashboard-summary"),
    path("recent-activities/", views.recent_activities, name="recent-activities"),
    path("faculty-stats/", views.faculty_stats, name="faculty-stats"),
    path("finance-snapshot/", views.finance_snapshot, name="finance-snapshot"),
]

