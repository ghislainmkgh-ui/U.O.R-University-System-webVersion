from __future__ import annotations

import mimetypes

from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse

from apps.common.decorators import api_methods, elevated_admin_required
from apps.common.responses import json_error, json_ok, parse_json

from .services import AcademicService, AcademicValidationError


def _academic():
    return AcademicService()


@api_methods("GET")
@elevated_admin_required
def student_summary(request: HttpRequest, student_id: int) -> JsonResponse:
    return _handle(lambda: json_ok(_academic().summary(student_id)))


@api_methods("GET", "POST")
@elevated_admin_required
def student_records(request: HttpRequest, student_id: int) -> JsonResponse:
    if request.method == "GET":
        return _handle(lambda: json_ok({"records": _academic().list_records(student_id)}))
    payload, error = parse_json(request)
    if error:
        return error
    return _handle(lambda: json_ok(_academic().create_record(student_id, payload), status=201))


@api_methods("GET", "PATCH", "DELETE")
@elevated_admin_required
def record_detail(request: HttpRequest, record_id: int) -> JsonResponse:
    service = _academic()
    if request.method == "GET":
        return _handle(lambda: json_ok(service.get_record(record_id)))
    if request.method == "DELETE":
        return _handle(lambda: _delete_response(service.delete_record, record_id))
    payload, error = parse_json(request)
    if error:
        return error
    return _handle(lambda: json_ok(service.update_record(record_id, payload)))


@api_methods("GET", "POST")
@elevated_admin_required
def student_documents(request: HttpRequest, student_id: int) -> JsonResponse:
    if request.method == "GET":
        return _handle(lambda: json_ok({"documents": _academic().list_documents(student_id)}))
    payload, error = parse_json(request)
    if error:
        return error
    return _handle(lambda: json_ok(_academic().create_document(student_id, payload), status=201))


@api_methods("GET", "PATCH", "DELETE")
@elevated_admin_required
def document_detail(request: HttpRequest, document_id: int) -> JsonResponse:
    service = _academic()
    if request.method == "GET":
        return _handle(lambda: json_ok(service.get_document(document_id)))
    if request.method == "DELETE":
        return _handle(lambda: _delete_response(service.delete_document, document_id))
    payload, error = parse_json(request)
    if error:
        return error
    return _handle(lambda: json_ok(service.update_document(document_id, payload)))


@api_methods("GET")
@elevated_admin_required
def document_download(request: HttpRequest, document_id: int):
    def response():
        blob, path, title = _academic().get_document_file(document_id)
        filename = title.replace('"', "").strip() or f"document_{document_id}"
        if blob:
            return HttpResponse(
                blob,
                content_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        if path:
            content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            return FileResponse(open(path, "rb"), content_type=content_type, as_attachment=True, filename=path.name)
        return json_error("Fichier introuvable", status=404, code="file_not_found")

    return _handle(response)


def _delete_response(callback, row_id: int) -> JsonResponse:
    callback(row_id)
    return json_ok({"deleted": True})


def _handle(callback):
    try:
        return callback()
    except AcademicValidationError as exc:
        status = 404 if exc.code.endswith("_not_found") else 400
        return json_error(str(exc), status=status, code=exc.code)
