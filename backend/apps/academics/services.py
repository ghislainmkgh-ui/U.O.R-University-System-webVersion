from __future__ import annotations

import base64
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings

from apps.common.legacy import ensure_legacy_path

ensure_legacy_path()

from core.database.connection import DatabaseConnection  # noqa: E402


class AcademicValidationError(ValueError):
    def __init__(self, message: str, code: str = "invalid_academic_payload"):
        super().__init__(message)
        self.code = code


class AcademicService:
    def __init__(self):
        self.db = DatabaseConnection()

    def summary(self, student_id: int) -> dict:
        student = self._student(student_id)
        if not student:
            raise AcademicValidationError("Etudiant introuvable", "student_not_found")
        records = self.list_records(student_id)
        documents = self.list_documents(student_id)
        grades = [float(row["grade"]) for row in records if row.get("grade") is not None]
        return {
            "student": student,
            "records_count": len(records),
            "documents_count": len(documents),
            "total_credits": sum(int(row.get("credits") or 0) for row in records),
            "average_grade": round(sum(grades) / len(grades), 2) if grades else None,
            "passed_count": sum(1 for row in records if str(row.get("status") or "").upper() == "PASSED"),
            "failed_count": sum(1 for row in records if str(row.get("status") or "").upper() == "FAILED"),
            "transferred_records_count": sum(1 for row in records if bool(row.get("is_transferred"))),
            "transferred_documents_count": sum(1 for row in documents if bool(row.get("is_transferred"))),
        }

    def list_records(self, student_id: int) -> list[dict]:
        self._require_student(student_id)
        query = """
            SELECT ar.*,
                   p.name AS promotion_name,
                   ay.year_name AS academic_year_name
            FROM academic_record ar
            LEFT JOIN promotion p ON p.id = ar.promotion_id
            LEFT JOIN academic_year ay ON ay.academic_year_id = ar.academic_year_id
            WHERE ar.student_id = %s
            ORDER BY ar.exam_date DESC, ar.created_at DESC, ar.id DESC
        """
        return self._query(query, (student_id,))

    def create_record(self, student_id: int, payload: dict) -> dict:
        student = self._require_student(student_id)
        data = self._record_payload(payload, student)
        columns = list(data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        record_id = self._insert(
            f"INSERT INTO academic_record ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(data[column] for column in columns),
        )
        return self.get_record(record_id)

    def get_record(self, record_id: int) -> dict:
        rows = self._query(
            """
            SELECT ar.*,
                   p.name AS promotion_name,
                   ay.year_name AS academic_year_name
            FROM academic_record ar
            LEFT JOIN promotion p ON p.id = ar.promotion_id
            LEFT JOIN academic_year ay ON ay.academic_year_id = ar.academic_year_id
            WHERE ar.id = %s
            LIMIT 1
            """,
            (record_id,),
        )
        if not rows:
            raise AcademicValidationError("Note introuvable", "record_not_found")
        return rows[0]

    def update_record(self, record_id: int, payload: dict) -> dict:
        current = self.get_record(record_id)
        student = self._require_student(int(current["student_id"]))
        data = self._record_update_payload(payload, student)
        if not data:
            raise AcademicValidationError("Aucune donnee a mettre a jour", "empty_update")
        if "updated_at" in self._table_columns("academic_record"):
            data["updated_at"] = RawSql("NOW()")
        self._update("academic_record", record_id, data)
        return self.get_record(record_id)

    def delete_record(self, record_id: int) -> None:
        self.get_record(record_id)
        self._execute("DELETE FROM academic_record WHERE id = %s", (record_id,))

    def list_documents(self, student_id: int) -> list[dict]:
        self._require_student(student_id)
        return self._query(
            """
            SELECT id, student_id, document_type, title, description, author, isbn,
                   category, file_path, file_size_mb, issue_date, return_date,
                   status, library_code, is_transferred, source_university,
                   created_at, updated_at,
                   CASE WHEN file_blob IS NULL THEN 0 ELSE 1 END AS has_file_blob
            FROM student_document
            WHERE student_id = %s
            ORDER BY issue_date DESC, created_at DESC, id DESC
            """,
            (student_id,),
        )

    def create_document(self, student_id: int, payload: dict) -> dict:
        self._require_student(student_id)
        data = self._document_payload(payload, student_id)
        columns = list(data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        document_id = self._insert(
            f"INSERT INTO student_document ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(data[column] for column in columns),
        )
        return self.get_document(document_id)

    def get_document(self, document_id: int) -> dict:
        rows = self._query(
            """
            SELECT id, student_id, document_type, title, description, author, isbn,
                   category, file_path, file_size_mb, issue_date, return_date,
                   status, library_code, is_transferred, source_university,
                   created_at, updated_at,
                   CASE WHEN file_blob IS NULL THEN 0 ELSE 1 END AS has_file_blob
            FROM student_document
            WHERE id = %s
            LIMIT 1
            """,
            (document_id,),
        )
        if not rows:
            raise AcademicValidationError("Document introuvable", "document_not_found")
        return rows[0]

    def get_document_file(self, document_id: int) -> tuple[bytes | None, Path | None, str]:
        rows = self._query(
            "SELECT title, file_path, file_blob FROM student_document WHERE id = %s LIMIT 1",
            (document_id,),
        )
        if not rows:
            raise AcademicValidationError("Document introuvable", "document_not_found")
        row = rows[0]
        title = str(row.get("title") or f"document_{document_id}")
        blob = row.get("file_blob")
        if blob:
            return bytes(blob), None, title
        file_path = self._safe_existing_path(row.get("file_path"))
        return None, file_path, title

    def update_document(self, document_id: int, payload: dict) -> dict:
        current = self.get_document(document_id)
        data = self._document_update_payload(payload, int(current["student_id"]))
        if not data:
            raise AcademicValidationError("Aucune donnee a mettre a jour", "empty_update")
        if "updated_at" in self._table_columns("student_document"):
            data["updated_at"] = RawSql("NOW()")
        self._update("student_document", document_id, data)
        return self.get_document(document_id)

    def delete_document(self, document_id: int) -> None:
        self.get_document(document_id)
        self._execute("DELETE FROM student_document WHERE id = %s", (document_id,))

    def _record_payload(self, payload: dict, student: dict) -> dict:
        course_name = str(payload.get("course_name") or "").strip()
        if not course_name:
            raise AcademicValidationError("Nom du cours requis", "missing_course_name")
        grade = self._grade(payload.get("grade"))
        credits = self._int(payload.get("credits"), default=0, minimum=0, maximum=60)
        status = self._status(payload.get("status"), grade)
        return {
            "student_id": int(student["id"]),
            "promotion_id": int(payload.get("promotion_id") or student["promotion_id"]),
            "academic_year_id": payload.get("academic_year_id") or student.get("academic_year_id"),
            "course_name": course_name,
            "course_code": str(payload.get("course_code") or self.generate_course_code(course_name)).strip() or None,
            "credits": credits,
            "grade": grade,
            "grade_letter": str(payload.get("grade_letter") or self.grade_letter(grade)).strip(),
            "semester": self._semester(payload.get("semester")),
            "exam_date": self._date(payload.get("exam_date")),
            "professor_name": self._clean_optional(payload.get("professor_name")),
            "status": status,
            "remarks": self._clean_optional(payload.get("remarks")),
            "is_transferred": bool(payload.get("is_transferred", False)),
            "source_university": self._clean_optional(payload.get("source_university")),
        }

    def _record_update_payload(self, payload: dict, student: dict) -> dict:
        allowed = {}
        if "course_name" in payload:
            course_name = str(payload.get("course_name") or "").strip()
            if not course_name:
                raise AcademicValidationError("Nom du cours requis", "missing_course_name")
            allowed["course_name"] = course_name
        if "course_code" in payload:
            allowed["course_code"] = self._clean_optional(payload.get("course_code"))
        if "credits" in payload:
            allowed["credits"] = self._int(payload.get("credits"), default=0, minimum=0, maximum=60)
        if "grade" in payload:
            grade = self._grade(payload.get("grade"))
            allowed["grade"] = grade
            allowed["grade_letter"] = str(payload.get("grade_letter") or self.grade_letter(grade)).strip()
            allowed["status"] = self._status(payload.get("status"), grade) if "status" in payload else "PASSED" if grade >= 10 else "FAILED"
        if "grade_letter" in payload and "grade" not in payload:
            allowed["grade_letter"] = self._clean_optional(payload.get("grade_letter"))
        if "semester" in payload:
            allowed["semester"] = self._semester(payload.get("semester"))
        if "exam_date" in payload:
            allowed["exam_date"] = self._date(payload.get("exam_date"))
        if "professor_name" in payload:
            allowed["professor_name"] = self._clean_optional(payload.get("professor_name"))
        if "status" in payload and "grade" not in payload:
            allowed["status"] = self._status(payload.get("status"), None)
        if "remarks" in payload:
            allowed["remarks"] = self._clean_optional(payload.get("remarks"))
        if "promotion_id" in payload:
            allowed["promotion_id"] = int(payload.get("promotion_id") or student["promotion_id"])
        if "academic_year_id" in payload:
            allowed["academic_year_id"] = payload.get("academic_year_id") or None
        return allowed

    def _document_payload(self, payload: dict, student_id: int) -> dict:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise AcademicValidationError("Titre du document requis", "missing_document_title")
        file_path, file_blob, file_size = self._extract_document_file(payload, student_id, title)
        return {
            "student_id": student_id,
            "document_type": self._document_type(payload.get("document_type")),
            "title": title,
            "description": self._clean_optional(payload.get("description")),
            "author": self._clean_optional(payload.get("author")),
            "isbn": self._clean_optional(payload.get("isbn")),
            "category": self._clean_optional(payload.get("category")),
            "file_path": file_path,
            "file_blob": file_blob,
            "file_size_mb": file_size,
            "issue_date": self._date(payload.get("issue_date")),
            "return_date": self._date(payload.get("return_date")),
            "status": self._document_status(payload.get("status")),
            "library_code": self._clean_optional(payload.get("library_code")),
            "is_transferred": bool(payload.get("is_transferred", False)),
            "source_university": self._clean_optional(payload.get("source_university")),
        }

    def _document_update_payload(self, payload: dict, student_id: int) -> dict:
        data = {}
        for key in ("title", "description", "author", "isbn", "category", "library_code", "source_university"):
            if key in payload:
                data[key] = self._clean_optional(payload.get(key))
        if "title" in data and not data["title"]:
            raise AcademicValidationError("Titre du document requis", "missing_document_title")
        if "document_type" in payload:
            data["document_type"] = self._document_type(payload.get("document_type"))
        if "status" in payload:
            data["status"] = self._document_status(payload.get("status"))
        if "issue_date" in payload:
            data["issue_date"] = self._date(payload.get("issue_date"))
        if "return_date" in payload:
            data["return_date"] = self._date(payload.get("return_date"))
        if "is_transferred" in payload:
            data["is_transferred"] = bool(payload.get("is_transferred"))
        file_path, file_blob, file_size = self._extract_document_file(payload, student_id, data.get("title") or "document")
        if file_path or file_blob:
            data["file_path"] = file_path
            data["file_blob"] = file_blob
            data["file_size_mb"] = file_size
        return data

    def generate_course_code(self, course_name: str) -> str:
        clean = unicodedata.normalize("NFKD", course_name).encode("ascii", "ignore").decode("ascii")
        words = re.findall(r"[A-Za-z0-9]+", clean.upper())
        if not words:
            return "COURSE"
        prefix = "".join(word[:3] for word in words[:2])[:6]
        return prefix or "COURSE"

    @staticmethod
    def grade_letter(grade: Decimal) -> str:
        value = float(grade)
        if value >= 18:
            return "A"
        if value >= 16:
            return "B"
        if value >= 14:
            return "C"
        if value >= 12:
            return "D"
        return "F"

    def _student(self, student_id: int) -> dict | None:
        rows = self._query(
            """
            SELECT s.id, s.student_number, s.firstname, s.lastname, s.email,
                   s.promotion_id, s.academic_year_id,
                   p.name AS promotion_name,
                   d.name AS department_name,
                   f.name AS faculty_name,
                   ay.year_name AS academic_year_name
            FROM student s
            LEFT JOIN promotion p ON p.id = s.promotion_id
            LEFT JOIN department d ON d.id = p.department_id
            LEFT JOIN faculty f ON f.id = d.faculty_id
            LEFT JOIN academic_year ay ON ay.academic_year_id = s.academic_year_id
            WHERE s.id = %s AND COALESCE(s.is_active, 1) = 1
            LIMIT 1
            """,
            (student_id,),
        )
        return rows[0] if rows else None

    def _require_student(self, student_id: int) -> dict:
        student = self._student(student_id)
        if not student:
            raise AcademicValidationError("Etudiant introuvable", "student_not_found")
        return student

    def _extract_document_file(self, payload: dict, student_id: int, title: str) -> tuple[str | None, bytes | None, Decimal | None]:
        raw = payload.get("file_base64")
        if not raw:
            return None, None, None
        data = str(raw)
        if "," in data:
            data = data.split(",", 1)[1]
        try:
            file_blob = base64.b64decode(data, validate=True)
        except Exception as exc:
            raise AcademicValidationError("Fichier base64 invalide", "invalid_file") from exc

        ext = self._clean_ext(payload.get("file_extension") or payload.get("filename") or ".bin")
        safe_title = re.sub(r"[^A-Za-z0-9_-]", "_", title).strip("_")[:80] or "document"
        storage_dir = Path(settings.LEGACY_STORAGE_ROOT) / "student_documents" / str(student_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = storage_dir / f"{safe_title}{ext}"
        file_path.write_bytes(file_blob)
        return str(file_path), file_blob, Decimal(str(round(len(file_blob) / (1024 * 1024), 4)))

    def _safe_existing_path(self, value) -> Path | None:
        if not value:
            return None
        try:
            path = Path(str(value)).resolve()
            storage_root = Path(settings.LEGACY_STORAGE_ROOT).resolve()
            if not path.exists() or storage_root not in path.parents and path != storage_root:
                return None
            return path
        except Exception:
            return None

    @staticmethod
    def _grade(value) -> Decimal:
        try:
            grade = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise AcademicValidationError("Note valide requise", "invalid_grade") from exc
        if grade < 0 or grade > 20:
            raise AcademicValidationError("La note doit etre entre 0 et 20", "invalid_grade")
        return grade

    @staticmethod
    def _int(value, *, default: int, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        return max(minimum, min(maximum, number))

    @staticmethod
    def _date(value):
        if value in (None, ""):
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise AcademicValidationError("Date invalide. Format attendu: YYYY-MM-DD", "invalid_date") from exc

    @staticmethod
    def _status(value, grade: Decimal | None) -> str:
        mapping = {
            "REUSSI": "PASSED",
            "RÉUSSI": "PASSED",
            "PASSED": "PASSED",
            "ECHEC": "FAILED",
            "ÉCHOUÉ": "FAILED",
            "FAILED": "FAILED",
            "EN COURS": "IN_PROGRESS",
            "IN_PROGRESS": "IN_PROGRESS",
            "VALIDATED": "VALIDATED",
        }
        raw = str(value or "").strip().upper()
        if raw:
            return mapping.get(raw, raw if raw in {"PASSED", "FAILED", "IN_PROGRESS", "VALIDATED"} else "PASSED")
        return "PASSED" if grade is not None and grade >= 10 else "FAILED" if grade is not None else "IN_PROGRESS"

    @staticmethod
    def _semester(value) -> str:
        mapping = {"ANNUEL": "Annual", "ANNUAL": "Annual", "1": "1", "2": "2"}
        return mapping.get(str(value or "Annual").strip().upper(), "Annual")

    @staticmethod
    def _document_type(value) -> str:
        mapping = {
            "LIVRE": "BOOK",
            "BOOK": "BOOK",
            "THESE": "THESIS",
            "THÈSE": "THESIS",
            "THESIS": "THESIS",
            "RAPPORT": "REPORT",
            "REPORT": "REPORT",
            "CERTIFICAT": "CERTIFICATE",
            "CERTIFICATE": "CERTIFICATE",
            "DIPLOME": "DIPLOMA",
            "DIPLÔME": "DIPLOMA",
            "DIPLOMA": "DIPLOMA",
            "OTHER": "OTHER",
            "AUTRE": "OTHER",
        }
        return mapping.get(str(value or "OTHER").strip().upper(), "OTHER")

    @staticmethod
    def _document_status(value) -> str:
        allowed = {"ACTIVE", "RETURNED", "LOST", "TRANSFERRED"}
        raw = str(value or "ACTIVE").strip().upper()
        return raw if raw in allowed else "ACTIVE"

    @staticmethod
    def _clean_optional(value):
        cleaned = str(value).strip() if value is not None else ""
        return cleaned or None

    @staticmethod
    def _clean_ext(value) -> str:
        suffix = Path(str(value or ".bin")).suffix.lower()
        return suffix if suffix and re.fullmatch(r"\.[a-z0-9]{1,8}", suffix) else ".bin"

    def _table_columns(self, table: str) -> set[str]:
        rows = self._query(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """,
            (table,),
        )
        return {row["COLUMN_NAME"] for row in rows}

    def _query(self, query: str, params: tuple = ()) -> list[dict]:
        return self.db.execute_query(query, params) or []

    def _execute(self, query: str, params: tuple = ()) -> int:
        return self.db.execute_update(query, params)

    def _insert(self, query: str, params: tuple) -> int:
        conn = None
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)

    def _update(self, table: str, row_id: int, data: dict) -> None:
        parts = []
        params = []
        for key, value in data.items():
            if isinstance(value, RawSql):
                parts.append(f"{key} = {value.sql}")
            else:
                parts.append(f"{key} = %s")
                params.append(value)
        params.append(row_id)
        self._execute(f"UPDATE {table} SET {', '.join(parts)} WHERE id = %s", tuple(params))


class RawSql:
    def __init__(self, sql: str):
        self.sql = sql
