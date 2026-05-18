from __future__ import annotations

import csv
import html
import textwrap
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import Iterable

from django.http import HttpResponse


def csv_response(filename: str, rows: Iterable[dict], columns: list[tuple[str, str]]) -> HttpResponse:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for _, label in columns])
    for row in rows:
        writer.writerow([_csv_value(row.get(key)) for key, _ in columns])

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def export_response(filename_base: str, rows: Iterable[dict], columns: list[tuple[str, str]], fmt: str) -> HttpResponse | None:
    fmt = str(fmt or "").strip().lower()
    row_list = list(rows)
    if fmt == "csv":
        return csv_response(f"{filename_base}.csv", row_list, columns)
    if fmt in {"xls", "xlsx", "excel"}:
        return excel_response(f"{filename_base}.xls", row_list, columns)
    if fmt == "pdf":
        return pdf_response(f"{filename_base}.pdf", row_list, columns)
    return None


def wants_csv(request) -> bool:
    return str(request.GET.get("format") or "").strip().lower() == "csv"


def requested_format(request) -> str:
    return str(request.GET.get("format") or "").strip().lower()


def excel_response(filename: str, rows: Iterable[dict], columns: list[tuple[str, str]]) -> HttpResponse:
    header_cells = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(_csv_value(row.get(key)))}</td>" for key, _ in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    document = (
        "<html><head><meta charset='utf-8'></head><body>"
        "<table border='1'>"
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></body></html>"
    )
    response = HttpResponse(document, content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def pdf_response(filename: str, rows: Iterable[dict], columns: list[tuple[str, str]]) -> HttpResponse:
    lines = []
    lines.append(" | ".join(label for _, label in columns))
    lines.append("-" * 110)
    for row in rows:
        values = [_csv_value(row.get(key)) for key, _ in columns]
        line = " | ".join(values)
        lines.extend(textwrap.wrap(line, width=128) or [""])

    pdf_bytes = _build_text_pdf(lines)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _build_text_pdf(lines: list[str]) -> bytes:
    pages = [lines[index : index + 48] for index in range(0, max(1, len(lines)), 48)] or [[]]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{3 + page_index * 2} 0 R' for page_index in range(len(pages)))}] /Count {len(pages)} >>".encode("latin-1"),
    ]

    for page_index, page_lines in enumerate(pages):
        page_object_id = 3 + page_index * 2
        content_object_id = page_object_id + 1
        stream = _pdf_text_stream(page_lines)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] "
                f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
                f"/Contents {content_object_id} 0 R >>"
            ).encode("latin-1")
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(pdf)


def _pdf_text_stream(lines: list[str]) -> bytes:
    parts = ["BT", "/F1 8 Tf", "34 560 Td", "10 TL"]
    for line in lines:
        parts.append(f"({_pdf_escape(line)}) Tj")
        parts.append("T*")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


def _pdf_escape(value: str) -> str:
    clean = str(value or "").encode("latin-1", errors="replace").decode("latin-1")
    return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
