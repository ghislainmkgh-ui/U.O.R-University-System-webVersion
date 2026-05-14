"""Decorators for API methods and token permissions."""
from __future__ import annotations

from functools import wraps
from typing import Callable

import jwt
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt

from .auth import get_bearer_payload
from .responses import json_error, method_not_allowed


def api_methods(*methods: str):
    allowed = {method.upper() for method in methods}

    def decorator(view: Callable):
        @csrf_exempt
        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if request.method.upper() not in allowed:
                return method_not_allowed()
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def token_required(view: Callable):
    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        try:
            payload = get_bearer_payload(request)
        except jwt.ExpiredSignatureError:
            return json_error("Session expiree", status=401, code="token_expired")
        except jwt.InvalidTokenError:
            return json_error("Token invalide", status=401, code="invalid_token")
        if not payload:
            return json_error("Authentification requise", status=401, code="auth_required")
        request.jwt_payload = payload
        request.current_user = payload.get("user") or {}
        return view(request, *args, **kwargs)

    return wrapper


def roles_required(*roles: str):
    allowed = {role.lower() for role in roles}

    def decorator(view: Callable):
        @wraps(view)
        @token_required
        def wrapper(request: HttpRequest, *args, **kwargs):
            role = str((getattr(request, "current_user", {}) or {}).get("role") or "").lower()
            if role not in allowed:
                return json_error("Acces refuse", status=403, code="forbidden")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(view: Callable):
    return roles_required("super_admin", "user", "admin")(view)


def elevated_admin_required(view: Callable):
    return roles_required("super_admin", "admin")(view)


def super_admin_required(view: Callable):
    return roles_required("super_admin")(view)
