from django.urls import path

from . import views

urlpatterns = [
    path("", views.students, name="students"),
    path("validate-photo/", views.validate_photo, name="validate-photo"),
    path("<int:student_id>/", views.student_detail, name="student-detail"),
    path("<int:student_id>/photo/", views.student_photo, name="student-photo"),
    path("faculties/", views.faculties, name="faculties"),
    path("departments/", views.departments, name="departments"),
    path("promotions/", views.promotions, name="promotions"),
]
