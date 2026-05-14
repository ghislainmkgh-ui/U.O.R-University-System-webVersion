"""JWT helpers for the Django API."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import jwt
from django.conf import settings
from django.http import HttpRequest

from .serialization import public_user


ALGORITHM = "HS256"


def create_token(user: dict) -> str:
    now = datetime.utcnow()
    safe_user = public_user(user)
    payload = {
        "sub": str(safe_user.get("id") or safe_user.get("student_number") or safe_user.get("username") or ""),
        "role": safe_user.get("role") or "user",
        "user": safe_user,
        "iat": now,
        "exp": now + timedelta(seconds=int(settings.JWT_EXPIRATION)),
        "iss": "uor-web-backend",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def get_bearer_payload(request: HttpRequest) -> dict | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    if not token:
        return None
    return decode_token(token)

