from django.urls import path

from . import views

urlpatterns = [
    path("pending/", views.pending_requests, name="pending-transfer-requests"),
    path("history/", views.history, name="transfer-history"),
    path("outgoing/", views.initiate_outgoing, name="initiate-outgoing-transfer"),
    path("incoming/<int:request_id>/approve/", views.approve_incoming, name="approve-incoming-transfer"),
    path("incoming/<int:request_id>/reject/", views.reject_incoming, name="reject-incoming-transfer"),
    path("partners/", views.partners, name="transfer-partners"),
    path("partners/<str:university_code>/api-url/", views.partner_api_url, name="partner-api-url"),
    path("packages/<str:transfer_code>/", views.transfer_package, name="transfer-package"),
]

