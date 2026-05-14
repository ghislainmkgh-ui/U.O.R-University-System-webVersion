from django.urls import path

from . import views

urlpatterns = [
    path("students/<int:student_id>/summary/", views.student_summary, name="academic-student-summary"),
    path("students/<int:student_id>/records/", views.student_records, name="academic-student-records"),
    path("records/<int:record_id>/", views.record_detail, name="academic-record-detail"),
    path("students/<int:student_id>/documents/", views.student_documents, name="academic-student-documents"),
    path("documents/<int:document_id>/", views.document_detail, name="academic-document-detail"),
    path("documents/<int:document_id>/download/", views.document_download, name="academic-document-download"),
]
