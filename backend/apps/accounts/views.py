"""Authentication and access-request API endpoints."""
from __future__ import annotations

import html
import os
import re
import secrets
from datetime import datetime
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import jwt
import requests

from apps.common.auth import create_token
from apps.common.decorators import api_methods, super_admin_required, token_required
from apps.common.legacy import services
from apps.common.responses import json_error, json_ok, parse_json
from apps.common.serialization import public_user

OAUTH_HANDOFFS: dict[str, dict] = {}
OAUTH_STATES: dict[str, dict] = {}
OAUTH_PROVIDERS = {
    "google": {
        "client_id_env": "GOOGLE_OAUTH_CLIENT_ID",
        "client_secret_env": "GOOGLE_OAUTH_CLIENT_SECRET",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "client_id_env": "GITHUB_OAUTH_CLIENT_ID",
        "client_secret_env": "GITHUB_OAUTH_CLIENT_SECRET",
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_info_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scope": "user:email",
    },
}


def _auth_service():
    return services()["auth"]


def _login_failure_message(message: str | None) -> str:
    raw = str(message or "").strip()
    allowed_business_messages = {
        "Votre compte est en attente de validation par le super admin",
        "Votre demande d'acces a ete rejetee",
    }
    if raw in allowed_business_messages:
        return raw
    return "Identifiant ou mot de passe incorrect. Verifiez vos informations puis reessayez."


@api_methods("POST")
def login(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error

    identifier = str(payload.get("identifier") or payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not identifier or not password:
        return json_error("Identifiant et mot de passe requis", status=400, code="missing_credentials")

    user, message = _auth_service().authenticate(identifier, password)
    if not user:
        return json_error(_login_failure_message(message), status=401, code="invalid_credentials")

    safe_user = public_user(user)
    return json_ok(
        {
            "token": create_token(safe_user),
            "token_type": "Bearer",
            "expires_in": int(settings.JWT_EXPIRATION),
            "user": safe_user,
        }
    )


@api_methods("POST")
def oauth_start(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error

    provider = _normalize_provider(payload.get("provider"))
    expected_email = str(payload.get("expected_email") or payload.get("email") or "").strip().lower()
    if not provider:
        return json_error("Fournisseur OAuth non pris en charge", status=400, code="oauth_provider_unsupported")
    if not _looks_like_email(expected_email):
        return json_error("Email valide requis pour OAuth", status=400, code="oauth_email_required")

    config = OAUTH_PROVIDERS[provider]
    client_id = os.getenv(config["client_id_env"], "")
    client_secret = os.getenv(config["client_secret_env"], "")
    if not client_id or not client_secret:
        return json_error(
            f"OAuth {provider} non configure",
            status=503,
            code="oauth_not_configured",
        )

    nonce = secrets.token_urlsafe(16)
    OAUTH_STATES[nonce] = {"provider": provider, "expected_email": expected_email}
    state = jwt.encode(
        {"provider": provider, "nonce": nonce},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    redirect_uri = _oauth_redirect_uri(provider)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": config["scope"],
        "state": state,
        "response_type": "code",
    }
    if provider == "google":
        params["access_type"] = "online"
    return json_ok({"auth_url": f"{config['auth_url']}?{urlencode(params)}"})


@api_methods("GET")
def oauth_callback(request: HttpRequest, provider: str) -> HttpResponse:
    provider = _normalize_provider(provider)
    code = str(request.GET.get("code") or "").strip()
    state = str(request.GET.get("state") or "").strip()
    if not provider or not code or not state:
        return _oauth_redirect("error=oauth_callback_invalid")

    try:
        state_payload = jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return _oauth_redirect("error=oauth_state_invalid")

    nonce = str(state_payload.get("nonce") or "")
    state_data = OAUTH_STATES.pop(nonce, None)
    if state_payload.get("provider") != provider or not state_data or state_data.get("provider") != provider:
        return _oauth_redirect("error=oauth_provider_mismatch")

    config = OAUTH_PROVIDERS[provider]
    client_id = os.getenv(config["client_id_env"], "")
    client_secret = os.getenv(config["client_secret_env"], "")
    if not client_id or not client_secret:
        return _oauth_redirect("error=oauth_not_configured")

    try:
        token_response = requests.post(
            config["token_url"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": _oauth_redirect_uri(provider),
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return _oauth_redirect("error=oauth_token_missing")

        provider_email = _fetch_oauth_email(provider, config, access_token)
        expected_email = str(state_data.get("expected_email") or "").strip().lower()
        if not provider_email:
            return _oauth_redirect("error=oauth_email_missing")
        if provider_email != expected_email:
            return _oauth_redirect("error=oauth_email_mismatch")

        user = _auth_service().authenticate_by_email_no_pw(provider_email)
        if not user:
            return _oauth_redirect("error=oauth_local_account_missing")

        safe_user = public_user(user)
        handoff = secrets.token_urlsafe(24)
        OAUTH_HANDOFFS[handoff] = {
            "token": create_token(safe_user),
            "token_type": "Bearer",
            "expires_in": int(settings.JWT_EXPIRATION),
            "user": safe_user,
            "provider": provider,
        }
        return _oauth_redirect(f"oauth_handoff={handoff}")
    except Exception:
        return _oauth_redirect("error=oauth_server_error")


@api_methods("POST")
def oauth_consume(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    handoff = str(payload.get("handoff") or "").strip()
    data = OAUTH_HANDOFFS.pop(handoff, None)
    if not data:
        return json_error("Session OAuth expiree ou invalide", status=400, code="oauth_handoff_invalid")
    return json_ok(data)


@api_methods("GET")
@token_required
def me(request: HttpRequest) -> JsonResponse:
    return json_ok(getattr(request, "current_user", {}) or {})


@api_methods("POST")
def request_access(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    ok, message = _auth_service().register_user_access_request(
        username=str(payload.get("username") or "").strip(),
        email=str(payload.get("email") or "").strip(),
        password=str(payload.get("password") or ""),
    )
    if not ok:
        return json_error(message, status=400, code="request_access_failed")
    return json_ok({"message": message}, status=201)


@api_methods("POST")
def reset_password(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    ok, message = _auth_service().reset_password_by_email(
        identifier=str(payload.get("identifier") or "").strip(),
        new_password=str(payload.get("new_password") or payload.get("password") or ""),
    )
    if not ok:
        return json_error(message, status=400, code="reset_failed")
    return json_ok({"message": message})


@api_methods("GET")
@super_admin_required
def pending_access_requests(request: HttpRequest) -> JsonResponse:
    return json_ok(_auth_service().get_pending_access_requests())


@api_methods("POST")
@super_admin_required
def approve_access_request(request: HttpRequest, request_id: int) -> JsonResponse:
    reviewer = _reviewer_identifier(request)
    ok, message = _auth_service().approve_access_request(request_id, reviewer_identifier=reviewer)
    if not ok:
        return json_error(message, status=400, code="approve_failed")
    return json_ok({"message": message})


@api_methods("POST")
@super_admin_required
def reject_access_request(request: HttpRequest, request_id: int) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    reviewer = _reviewer_identifier(request)
    ok, message = _auth_service().reject_access_request(
        request_id,
        reviewer_identifier=reviewer,
        note=str(payload.get("note") or ""),
    )
    if not ok:
        return json_error(message, status=400, code="reject_failed")
    return json_ok({"message": message})


@api_methods("GET")
@super_admin_required
def approved_administrators(request: HttpRequest) -> JsonResponse:
    return json_ok(_auth_service().get_approved_administrators())


@api_methods("DELETE")
@super_admin_required
def delete_administrator(request: HttpRequest, admin_id: int) -> JsonResponse:
    ok, message = _auth_service().delete_administrator(admin_id, requester_is_super_admin=True)
    if not ok:
        return json_error(message, status=400, code="delete_admin_failed")
    return json_ok({"message": message})


@csrf_exempt
def access_request_decision(request: HttpRequest) -> HttpResponse:
    """Browser-friendly endpoint used by email approval links."""
    if request.method == "GET":
        token = (request.GET.get("token") or "").strip()
        action = _normalize_action(request.GET.get("action"))
        if not token or not action:
            return _decision_page("Lien invalide", "Le lien est incomplet ou incorrect.", status=400)
        label = "Valider cette demande" if action == "approve" else "Rejeter cette demande"
        body = (
            f"<p>Vous allez <strong>{html.escape(action)}</strong> la demande d'acces.</p>"
            "<form method='post'>"
            f"<input type='hidden' name='token' value='{html.escape(token)}' />"
            f"<input type='hidden' name='action' value='{html.escape(action)}' />"
            f"<button type='submit'>{html.escape(label)}</button>"
            "</form>"
        )
        return _decision_page("Confirmation decision", body, raw=True)

    if request.method == "POST":
        token = (request.POST.get("token") or request.GET.get("token") or "").strip()
        action = _normalize_action(request.POST.get("action") or request.GET.get("action"))
        if not token or not action:
            return _decision_page("Donnees invalides", "Action ou jeton manquant.", status=400)
        reviewer = f"email_link:{request.META.get('REMOTE_ADDR') or 'unknown'}"
        ok, message = _auth_service().process_access_request_token_decision(token, action, reviewer)
        title = "Decision enregistree" if ok else "Decision impossible"
        return _decision_page(title, html.escape(message or ""), status=200 if ok else 400, raw=True)

    return _decision_page("Methode non autorisee", "Methode non autorisee.", status=405)


def _reviewer_identifier(request: HttpRequest) -> str:
    user = getattr(request, "current_user", {}) or {}
    return str(user.get("email") or user.get("username") or user.get("id") or "super_admin")


def _normalize_provider(provider: str | None) -> str:
    value = str(provider or "").strip().lower()
    return value if value in OAUTH_PROVIDERS else ""


def _looks_like_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value or "").strip()))


def _oauth_redirect_uri(provider: str) -> str:
    return f"{settings.BACKEND_PUBLIC_URL}/api/auth/oauth/callback/{provider}/"


def _oauth_redirect(query: str) -> HttpResponse:
    return HttpResponse(
        "",
        status=302,
        headers={"Location": f"{settings.FRONTEND_URL}/login?{query}"},
    )


def _fetch_oauth_email(provider: str, config: dict, access_token: str) -> str:
    user_response = requests.get(
        config["user_info_url"],
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=10,
    )
    user_data = user_response.json()
    email = str(user_data.get("email") or "").strip().lower()
    if email or provider != "github":
        return email

    email_response = requests.get(
        config["emails_url"],
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=10,
    )
    for item in email_response.json() or []:
        if item.get("primary") and item.get("verified", True):
            return str(item.get("email") or "").strip().lower()
    return ""


def _normalize_action(action: str | None) -> str:
    value = (action or "").strip().lower()
    return value if value in {"approve", "reject"} else ""


def _decision_page(title: str, body: str, *, status: int = 200, raw: bool = False) -> HttpResponse:
    safe_body = body if raw else f"<p>{html.escape(body)}</p>"
    content = f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f7fb; color: #172033; }}
    main {{ max-width: 680px; margin: 42px auto; padding: 24px; background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; }}
    button {{ border: 0; border-radius: 8px; padding: 10px 16px; background: #0f766e; color: #fff; font-weight: 700; cursor: pointer; }}
    .muted {{ color: #64748b; font-size: 13px; }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    {safe_body}
    <p class="muted">U.O.R - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
  </main>
</body>
</html>"""
    return HttpResponse(content, status=status, content_type="text/html; charset=utf-8")
