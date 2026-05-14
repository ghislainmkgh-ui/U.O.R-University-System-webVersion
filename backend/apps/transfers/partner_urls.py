from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.partner_health, name="partner-health"),
    path("auth/token/", views.partner_token, name="partner-token"),
    path("transfer/receive/", views.partner_receive_transfer, name="partner-receive-transfer"),
    path("transfer/send/", views.partner_send_transfer, name="partner-send-transfer"),
    path("transfer/status/<str:transfer_code>/", views.partner_transfer_status, name="partner-transfer-status"),
    path("universities/", views.partner_universities, name="partner-universities"),
]

