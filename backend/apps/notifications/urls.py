from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.status, name="notification-status"),
    path("send-email/", views.send_email, name="send-email"),
    path("send-whatsapp/", views.send_whatsapp, name="send-whatsapp"),
]

