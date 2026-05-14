"""Notification endpoints for email and WhatsApp channels."""
from __future__ import annotations

from django.http import HttpRequest, JsonResponse

from apps.common.decorators import admin_required, api_methods
from apps.common.legacy import services
from apps.common.responses import json_error, json_ok, parse_json


def _notification():
    return services()["notification"]


@api_methods("GET")
@admin_required
def status(request: HttpRequest) -> JsonResponse:
    return json_ok(_notification().get_channel_status())


@api_methods("POST")
@admin_required
def send_email(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    recipient = str(payload.get("recipient") or payload.get("email") or "").strip()
    subject = str(payload.get("subject") or "U.O.R Notification").strip()
    message = str(payload.get("message") or "").strip()
    if not recipient or not message:
        return json_error("Destinataire et message requis", status=400, code="missing_email_payload")
    ok = _notification()._send_email(recipient, subject, message)
    if not ok:
        return json_error("Email non envoye", status=400, code="email_failed")
    return json_ok({"message": "Email envoye"})


@api_methods("POST")
@admin_required
def send_whatsapp(request: HttpRequest) -> JsonResponse:
    payload, error = parse_json(request)
    if error:
        return error
    phone = str(payload.get("phone") or payload.get("recipient") or "").strip()
    message = str(payload.get("message") or "").strip()
    if not phone or not message:
        return json_error("Numero et message requis", status=400, code="missing_whatsapp_payload")
    ok = _notification()._send_whatsapp(phone, message)
    if not ok:
        return json_error("WhatsApp non envoye", status=400, code="whatsapp_failed")
    return json_ok({"message": "WhatsApp envoye"})

