"""JSON serialization helpers for legacy MySQL rows."""
from __future__ import annotations

import base64
from datetime import date, datetime
from decimal import Decimal
from typing import Any


SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "face_encoding",
    "passport_photo_blob",
    "photo_blob",
    "file_blob",
    "api_key_encrypted",
    "auth_token_hash",
}


def to_jsonable(value: Any, *, include_blobs: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            key: to_jsonable(item, include_blobs=include_blobs)
            for key, item in value.items()
            if include_blobs or key not in SENSITIVE_KEYS
        }
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item, include_blobs=include_blobs) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        if include_blobs:
            return base64.b64encode(bytes(value)).decode("ascii")
        return None
    return value


def public_user(user: dict) -> dict:
    data = to_jsonable(user or {})
    for key in SENSITIVE_KEYS:
        data.pop(key, None)
    return data


def add_photo_flags(row: dict) -> dict:
    data = dict(row or {})
    data["has_photo"] = bool(data.get("passport_photo_blob") or data.get("passport_photo_path"))
    data.pop("passport_photo_blob", None)
    return to_jsonable(data)

