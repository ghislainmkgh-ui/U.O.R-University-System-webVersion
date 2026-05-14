"""Small JSON response helpers used by all API apps."""
from __future__ import annotations

import json
import re
from json import JSONDecodeError
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .serialization import to_jsonable


def json_ok(data: Any = None, *, status: int = 200, **extra: Any) -> JsonResponse:
    payload = {"success": True}
    if data is not None:
        payload["data"] = to_jsonable(data)
    payload.update(to_jsonable(extra))
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def json_error(message: str, *, status: int = 400, code: str = "error", **extra: Any) -> JsonResponse:
    payload = {"success": False, "error": public_error_message(message, code=code), "code": code}
    payload.update(to_jsonable(_public_error_extra(extra)))
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


TECHNICAL_ERROR_MESSAGES = {
    "OVERPAYMENT": "Le paiement depasse le montant total des frais academiques. Verifiez le reste a payer avant d'enregistrer.",
    "NO_ACTIVE_FEES": "Aucun frais academique actif n'est configure pour cette promotion.",
    "NO_FINANCE_PROFILE": "Le profil financier de cet etudiant est introuvable.",
    "NO_PROMOTION_DATA": "Les informations de promotion de cet etudiant sont introuvables.",
    "PAYMENT_EXCEPTION": "Paiement impossible pour le moment. Veuillez reessayer.",
    "NO_ACCESS_CODE": "Aucun code d'acces n'existe encore pour cet etudiant.",
    "ACCESS_CODE_EXPIRED": "Le dernier code d'acces est expire. Enregistrez un nouveau paiement valide ou regenerez un code.",
    "INVALID_ACCESS_CODE": "Le dernier code d'acces est invalide. Generez un nouveau code pour cet etudiant.",
    "ACCESS_CODE_NOTIFICATION_FAILED": "Le code existe, mais l'envoi a echoue. Verifiez l'email ou le numero WhatsApp.",
    "ACCESS_CODE_RESEND_EXCEPTION": "Le code n'a pas pu etre envoye pour le moment. Veuillez reessayer.",
}

GENERIC_CODE_MESSAGES = {
    "invalid_credentials": "Identifiant ou mot de passe incorrect. Verifiez vos informations puis reessayez.",
    "missing_credentials": "Identifiant et mot de passe requis.",
    "payment_failed": "Paiement refuse. Verifiez le montant et la situation financiere de l'etudiant.",
    "access_code_resend_failed": "Le code n'a pas pu etre envoye. Verifiez les contacts de l'etudiant et reessayez.",
    "error": "Une erreur est survenue. Veuillez reessayer.",
}


def public_error_message(message: Any, *, code: str = "error") -> str:
    raw = str(message or "").strip()
    if not raw:
        return GENERIC_CODE_MESSAGES.get(code, "Une erreur est survenue. Veuillez reessayer.")

    technical_key = _technical_error_key(raw)
    if technical_key:
        return TECHNICAL_ERROR_MESSAGES.get(
            technical_key,
            GENERIC_CODE_MESSAGES.get(code, "Une erreur est survenue. Veuillez reessayer."),
        )

    if _looks_technical(raw):
        return GENERIC_CODE_MESSAGES.get(code, "Une erreur est survenue. Veuillez reessayer.")

    return raw


def _public_error_extra(extra: dict[str, Any]) -> dict[str, Any]:
    public = {}
    hidden_keys = {"developer_hint", "debug", "traceback", "stack", "exception"}
    for key, value in extra.items():
        if key in hidden_keys:
            continue
        if key == "detail" and _looks_technical(str(value or "")):
            continue
        public[key] = value
    return public


def _technical_error_key(message: str) -> str:
    match = re.match(r"^\s*([A-Z][A-Z0-9_]+)\s*:", message)
    return match.group(1) if match else ""


def _looks_technical(message: str) -> bool:
    return any(
        [
            bool(_technical_error_key(message)),
            "student_id=" in message,
            "Traceback" in message,
            "Exception" in message,
            bool(re.search(r"\b(ModuleNotFoundError|OperationalError|IntegrityError|TypeError|ValueError|KeyError)\b", message)),
            "mysql.connector" in message,
            "File \"" in message,
            bool(re.search(r"\b[a-zA-Z_]+=[^;]+;", message)),
            bool(re.search(r"[A-Za-z]:\\", message)),
        ]
    )


def parse_json(request: HttpRequest) -> tuple[dict, JsonResponse | None]:
    if not request.body:
        return {}, None
    try:
        return json.loads(request.body.decode("utf-8")), None
    except (UnicodeDecodeError, JSONDecodeError):
        return {}, json_error("Payload JSON invalide", status=400, code="invalid_json")


def method_not_allowed() -> JsonResponse:
    return json_error("Methode non autorisee", status=405, code="method_not_allowed")


@csrf_exempt
def health(request: HttpRequest) -> JsonResponse:
    return json_ok({"status": "healthy", "service": "U.O.R Django Backend"})
