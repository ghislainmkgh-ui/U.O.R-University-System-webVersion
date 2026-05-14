from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login, name="auth-login"),
    path("oauth/start/", views.oauth_start, name="oauth-start"),
    path("oauth/callback/<str:provider>/", views.oauth_callback, name="oauth-callback"),
    path("oauth/consume/", views.oauth_consume, name="oauth-consume"),
    path("me/", views.me, name="auth-me"),
    path("request-access/", views.request_access, name="request-access"),
    path("reset-password/", views.reset_password, name="reset-password"),
    path("access-requests/pending/", views.pending_access_requests, name="pending-access-requests"),
    path("access-requests/<int:request_id>/approve/", views.approve_access_request, name="approve-access-request"),
    path("access-requests/<int:request_id>/reject/", views.reject_access_request, name="reject-access-request"),
    path("admins/", views.approved_administrators, name="approved-admins"),
    path("admins/<int:admin_id>/", views.delete_administrator, name="delete-admin"),
]
