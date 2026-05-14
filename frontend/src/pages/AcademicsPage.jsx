import {
  BookOpenCheck,
  Download,
  FileText,
  GraduationCap,
  LibraryBig,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { apiRequest, downloadApiFile } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { StudentPhoto } from "../components/StudentPhoto.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

const statusOptions = [
  { value: "PASSED", label: "REUSSI" },
  { value: "FAILED", label: "ECHOUE" },
  { value: "IN_PROGRESS", label: "EN COURS" },
  { value: "VALIDATED", label: "VALIDE" },
];

const documentTypes = [
  { value: "CERTIFICATE", label: "CERTIFICAT" },
  { value: "DIPLOMA", label: "DIPLOME" },
  { value: "REPORT", label: "RAPPORT" },
  { value: "THESIS", label: "THESE" },
  { value: "BOOK", label: "LIVRE" },
  { value: "OTHER", label: "AUTRE" },
];

export function AcademicsPage() {
  const students = useApiResource("/api/students/");
  const rows = Array.isArray(students.data) ? students.data : [];
  const hierarchy = useMemo(() => buildHierarchy(rows), [rows]);
  const [facultyId, setFacultyId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [promotionId, setPromotionId] = useState("");
  const [query, setQuery] = useState("");
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [activeTab, setActiveTab] = useState("grades");
  const [gradeForm, setGradeForm] = useState(() => initialGradeForm());
  const [documentForm, setDocumentForm] = useState(() => initialDocumentForm());
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");
  const [formSuccess, setFormSuccess] = useState("");

  useEffect(() => {
    if (!hierarchy.faculties.length) return;

    const nextFaculty = hierarchy.faculties.find((faculty) => faculty.id === facultyId) || hierarchy.faculties[0];
    const nextDepartment = nextFaculty.departments.find((department) => department.id === departmentId) || nextFaculty.departments[0];
    const nextPromotion = nextDepartment?.promotions.find((promotion) => promotion.id === promotionId) || nextDepartment?.promotions[0];

    if (nextFaculty.id !== facultyId) setFacultyId(nextFaculty.id);
    if ((nextDepartment?.id || "") !== departmentId) setDepartmentId(nextDepartment?.id || "");
    if ((nextPromotion?.id || "") !== promotionId) setPromotionId(nextPromotion?.id || "");
  }, [hierarchy, facultyId, departmentId, promotionId]);

  const currentFaculty = hierarchy.faculties.find((faculty) => faculty.id === facultyId);
  const currentDepartment = currentFaculty?.departments.find((department) => department.id === departmentId);
  const currentPromotion = currentDepartment?.promotions.find((promotion) => promotion.id === promotionId);
  const promotionStudents = currentPromotion?.students || [];
  const visibleStudents = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return promotionStudents;
    return promotionStudents.filter((student) => {
      const haystack = `${student.student_number || ""} ${student.firstname || ""} ${student.lastname || ""} ${student.email || ""}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [promotionStudents, query]);

  useEffect(() => {
    if (!promotionStudents.length) {
      setSelectedStudent(null);
      return;
    }
    if (!selectedStudent || !promotionStudents.some((student) => student.id === selectedStudent.id)) {
      setSelectedStudent(promotionStudents[0]);
    }
  }, [promotionStudents, selectedStudent]);

  const selectedId = selectedStudent?.id;
  const summary = useApiResource(selectedId ? `/api/academics/students/${selectedId}/summary/` : null);
  const records = useApiResource(selectedId ? `/api/academics/students/${selectedId}/records/` : null);
  const documents = useApiResource(selectedId ? `/api/academics/students/${selectedId}/documents/` : null);
  const recordRows = records.data?.records || [];
  const documentRows = documents.data?.documents || [];

  function reloadAcademicData() {
    summary.reload();
    records.reload();
    documents.reload();
  }

  function chooseFaculty(nextFacultyId) {
    const nextFaculty = hierarchy.faculties.find((faculty) => faculty.id === nextFacultyId);
    const nextDepartment = nextFaculty?.departments[0];
    const nextPromotion = nextDepartment?.promotions[0];
    setFacultyId(nextFaculty?.id || "");
    setDepartmentId(nextDepartment?.id || "");
    setPromotionId(nextPromotion?.id || "");
    setQuery("");
  }

  function chooseDepartment(nextDepartmentId) {
    const nextDepartment = currentFaculty?.departments.find((department) => department.id === nextDepartmentId);
    const nextPromotion = nextDepartment?.promotions[0];
    setDepartmentId(nextDepartment?.id || "");
    setPromotionId(nextPromotion?.id || "");
    setQuery("");
  }

  function updateGrade(field, value) {
    setGradeForm((form) => {
      const next = { ...form, [field]: value };
      if (field === "courseName") {
        next.courseCode = generateCourseCode(value);
      }
      return next;
    });
  }

  async function submitGrade(event) {
    event.preventDefault();
    if (!selectedStudent) return;
    setFormError("");
    setFormSuccess("");
    const grade = Number(String(gradeForm.grade).replace(",", "."));
    if (!gradeForm.courseName.trim()) {
      setFormError("Veuillez entrer le nom du cours.");
      return;
    }
    if (Number.isNaN(grade) || grade < 0 || grade > 20) {
      setFormError("La note doit etre comprise entre 0 et 20.");
      return;
    }
    setBusy(true);
    try {
      await apiRequest(`/api/academics/students/${selectedStudent.id}/records/`, {
        method: "POST",
        body: JSON.stringify({
          course_name: gradeForm.courseName,
          course_code: gradeForm.courseCode || generateCourseCode(gradeForm.courseName),
          credits: Number(gradeForm.credits || 0),
          grade,
          semester: gradeForm.semester,
          exam_date: gradeForm.examDate || null,
          professor_name: gradeForm.professorName || null,
          status: gradeForm.status,
          remarks: gradeForm.remarks || null,
        }),
      });
      setGradeForm(initialGradeForm());
      setFormSuccess("Note ajoutee avec succes.");
      reloadAcademicData();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitDocument(event) {
    event.preventDefault();
    if (!selectedStudent) return;
    setFormError("");
    setFormSuccess("");
    if (!documentForm.title.trim()) {
      setFormError("Veuillez entrer le titre du document.");
      return;
    }
    setBusy(true);
    try {
      const filePayload = documentForm.file ? await fileToDataUrl(documentForm.file) : null;
      await apiRequest(`/api/academics/students/${selectedStudent.id}/documents/`, {
        method: "POST",
        body: JSON.stringify({
          document_type: documentForm.documentType,
          title: documentForm.title,
          category: documentForm.category || null,
          author: documentForm.author || null,
          description: documentForm.description || null,
          issue_date: documentForm.issueDate || null,
          status: "ACTIVE",
          file_base64: filePayload,
          file_extension: documentForm.file ? fileExtension(documentForm.file.name) : undefined,
        }),
      });
      setDocumentForm(initialDocumentForm());
      setFormSuccess("Document ajoute avec succes.");
      reloadAcademicData();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteRecord(recordId) {
    if (!recordId) return;
    setFormError("");
    setFormSuccess("");
    setBusy(true);
    try {
      await apiRequest(`/api/academics/records/${recordId}/`, { method: "DELETE" });
      setFormSuccess("Note supprimee.");
      reloadAcademicData();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteDocument(documentId) {
    if (!documentId) return;
    setFormError("");
    setFormSuccess("");
    setBusy(true);
    try {
      await apiRequest(`/api/academics/documents/${documentId}/`, { method: "DELETE" });
      setFormSuccess("Document supprime.");
      reloadAcademicData();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page academics-page desktop-page">
      <PageHeader title="Donnees Academiques" subtitle="Notes, cours et documents par etudiant" />

      <AsyncState loading={students.loading} error={students.error}>
        <div className="academic-desktop-grid">
          <aside className="surface academic-sidebar-card">
            <div className="card-heading">
              <GraduationCap size={22} />
              <div>
                <h2>Selection Hierarchique</h2>
                <span>Faculte / Departement / Promotion</span>
              </div>
            </div>

            <label className="desktop-field">
              <span>Faculte</span>
              <select value={facultyId} onChange={(event) => chooseFaculty(event.target.value)}>
                {hierarchy.faculties.map((faculty) => (
                  <option key={faculty.id} value={faculty.id}>
                    {faculty.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="desktop-field">
              <span>Departement</span>
              <select value={departmentId} onChange={(event) => chooseDepartment(event.target.value)}>
                {(currentFaculty?.departments || []).map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="desktop-field">
              <span>Promotion</span>
              <select value={promotionId} onChange={(event) => setPromotionId(event.target.value)}>
                {(currentDepartment?.promotions || []).map((promotion) => (
                  <option key={promotion.id} value={promotion.id}>
                    {promotion.name}
                  </option>
                ))}
              </select>
            </label>

            <div className="search-line academic-search">
              <Search size={18} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nom, numero ou email" />
            </div>

            <div className="student-pick-list">
              {visibleStudents.map((student) => (
                <button
                  key={student.id}
                  className={selectedStudent?.id === student.id ? "active" : ""}
                  onClick={() => setSelectedStudent(student)}
                >
                  <StudentPhoto student={student} size="small" />
                  <span>
                    <strong>{studentName(student)}</strong>
                    <small>{student.student_number || "-"}</small>
                  </span>
                </button>
              ))}
              {!visibleStudents.length && <p className="empty-cell">Aucun etudiant trouve.</p>}
            </div>
          </aside>

          <main className="surface academic-detail-card">
            {!selectedStudent ? (
              <div className="empty-detail-state">
                <UserRound size={44} />
                <h2>Selectionner un etudiant</h2>
                <p>Les notes et documents apparaitront ici.</p>
              </div>
            ) : (
              <>
                <div className="academic-student-header">
                  <StudentPhoto student={selectedStudent} size="large" />
                  <div>
                    <h2>{studentName(selectedStudent)}</h2>
                    <p>
                      {selectedStudent.student_number || "-"} | {selectedStudent.promotion_name || currentPromotion?.name || "-"}
                    </p>
                    <span>{selectedStudent.email || "Email non renseigne"}</span>
                  </div>
                  <button className="primary-button" onClick={reloadAcademicData}>
                    <RefreshCw size={18} />
                    Actualiser
                  </button>
                </div>

                <AsyncState loading={summary.loading} error={summary.error}>
                  <div className="academic-summary-grid">
                    <SummaryTile value={summary.data?.records_count || 0} label="Cours" tone="blue" />
                    <SummaryTile value={summary.data?.documents_count || 0} label="Documents" tone="green" />
                    <SummaryTile value={summary.data?.total_credits || 0} label="Credits" tone="gold" />
                    <SummaryTile value={formatAverage(summary.data?.average_grade)} label="Moyenne" tone="purple" />
                  </div>
                </AsyncState>

                <div className="academic-tabs">
                  <button className={activeTab === "grades" ? "active" : ""} onClick={() => setActiveTab("grades")}>
                    <BookOpenCheck size={18} />
                    Notes
                  </button>
                  <button className={activeTab === "documents" ? "active" : ""} onClick={() => setActiveTab("documents")}>
                    <LibraryBig size={18} />
                    Documents
                  </button>
                </div>

                {formError && <p className="error-text academic-feedback">{formError}</p>}
                {formSuccess && <p className="success-text academic-feedback">{formSuccess}</p>}

                {activeTab === "grades" ? (
                  <div className="academic-tab-grid">
                    <form className="surface academic-form-card" onSubmit={submitGrade}>
                      <h3>
                        <Plus size={18} /> Ajouter une note
                      </h3>
                      <label className="desktop-field wide">
                        <span>Nom du cours *</span>
                        <input value={gradeForm.courseName} onChange={(event) => updateGrade("courseName", event.target.value)} placeholder="Ex: Programmation Python" />
                      </label>
                      <div className="form-two-columns">
                        <label className="desktop-field">
                          <span>Code du cours</span>
                          <input value={gradeForm.courseCode} disabled placeholder="Genere automatiquement" />
                        </label>
                        <label className="desktop-field">
                          <span>Credits ECTS</span>
                          <input value={gradeForm.credits} onChange={(event) => updateGrade("credits", event.target.value)} placeholder="Ex: 4" />
                        </label>
                      </div>
                      <div className="form-two-columns">
                        <label className="desktop-field">
                          <span>Note /20 *</span>
                          <input value={gradeForm.grade} onChange={(event) => updateGrade("grade", event.target.value)} placeholder="Ex: 15.5" />
                        </label>
                        <label className="desktop-field">
                          <span>Statut</span>
                          <select value={gradeForm.status} onChange={(event) => updateGrade("status", event.target.value)}>
                            {statusOptions.map((status) => (
                              <option key={status.value} value={status.value}>
                                {status.label}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <div className="form-two-columns">
                        <label className="desktop-field">
                          <span>Semestre</span>
                          <select value={gradeForm.semester} onChange={(event) => updateGrade("semester", event.target.value)}>
                            <option value="1">1</option>
                            <option value="2">2</option>
                            <option value="Annual">Annuel</option>
                          </select>
                        </label>
                        <label className="desktop-field">
                          <span>Date d'examen</span>
                          <input type="date" value={gradeForm.examDate} onChange={(event) => updateGrade("examDate", event.target.value)} />
                        </label>
                      </div>
                      <label className="desktop-field wide">
                        <span>Enseignant</span>
                        <input value={gradeForm.professorName} onChange={(event) => updateGrade("professorName", event.target.value)} placeholder="Nom de l'enseignant" />
                      </label>
                      <div className="dialog-actions">
                        <button className="dialog-primary green" disabled={busy}>
                          Ajouter la Note
                        </button>
                        <button type="button" className="dialog-secondary" onClick={() => setGradeForm(initialGradeForm())} disabled={busy}>
                          Reinitialiser
                        </button>
                      </div>
                    </form>

                    <AcademicRecordsTable rows={recordRows} loading={records.loading} error={records.error} onDelete={deleteRecord} />
                  </div>
                ) : (
                  <div className="academic-tab-grid">
                    <form className="surface academic-form-card" onSubmit={submitDocument}>
                      <h3>
                        <FileText size={18} /> Ajouter un document
                      </h3>
                      <label className="desktop-field">
                        <span>Type de document *</span>
                        <select value={documentForm.documentType} onChange={(event) => setDocumentForm((form) => ({ ...form, documentType: event.target.value }))}>
                          {documentTypes.map((type) => (
                            <option key={type.value} value={type.value}>
                              {type.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="desktop-field wide">
                        <span>Titre du document *</span>
                        <input value={documentForm.title} onChange={(event) => setDocumentForm((form) => ({ ...form, title: event.target.value }))} placeholder="Ex: Certificat de scolarite" />
                      </label>
                      <div className="form-two-columns">
                        <label className="desktop-field">
                          <span>Categorie</span>
                          <input value={documentForm.category} onChange={(event) => setDocumentForm((form) => ({ ...form, category: event.target.value }))} placeholder="Administration" />
                        </label>
                        <label className="desktop-field">
                          <span>Auteur</span>
                          <input value={documentForm.author} onChange={(event) => setDocumentForm((form) => ({ ...form, author: event.target.value }))} placeholder="U.O.R" />
                        </label>
                      </div>
                      <label className="desktop-field">
                        <span>Date d'emission</span>
                        <input type="date" value={documentForm.issueDate} onChange={(event) => setDocumentForm((form) => ({ ...form, issueDate: event.target.value }))} />
                      </label>
                      <label className="desktop-field wide">
                        <span>Description</span>
                        <textarea value={documentForm.description} onChange={(event) => setDocumentForm((form) => ({ ...form, description: event.target.value }))} />
                      </label>
                      <label className="desktop-field wide">
                        <span>Fichier</span>
                        <input type="file" onChange={(event) => setDocumentForm((form) => ({ ...form, file: event.target.files?.[0] || null }))} />
                      </label>
                      <div className="dialog-actions">
                        <button className="dialog-primary green" disabled={busy}>
                          Ajouter le Document
                        </button>
                        <button type="button" className="dialog-secondary" onClick={() => setDocumentForm(initialDocumentForm())} disabled={busy}>
                          Reinitialiser
                        </button>
                      </div>
                    </form>

                    <AcademicDocumentsTable rows={documentRows} loading={documents.loading} error={documents.error} onDelete={deleteDocument} />
                  </div>
                )}
              </>
            )}
          </main>
        </div>
      </AsyncState>
    </section>
  );
}

function SummaryTile({ value, label, tone }) {
  return (
    <div className={`academic-summary-tile ${tone}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function AcademicRecordsTable({ rows, loading, error, onDelete }) {
  return (
    <section className="surface academic-data-card">
      <h3>Dernieres Notes</h3>
      <AsyncState loading={loading} error={error}>
        <div className="desktop-table-wrap">
          <div className="desktop-table-header academic-record-columns">
            <span>Cours</span>
            <span>Code</span>
            <span>Credits</span>
            <span>Note</span>
            <span>Statut</span>
            <span>Date</span>
            <span></span>
          </div>
          <div className="desktop-table-body">
            {rows.map((row) => (
              <div className="desktop-table-row academic-record-columns" key={row.id}>
                <span>{row.course_name || "-"}</span>
                <span className="muted-cell">{row.course_code || "-"}</span>
                <span>{row.credits || 0}</span>
                <strong className={Number(row.grade || 0) >= 10 ? "success-text" : "error-text"}>{formatNumber(row.grade)}/20</strong>
                <span>{statusLabel(row.status)}</span>
                <span>{formatDate(row.exam_date)}</span>
                <button className="small-icon-button danger" title="Supprimer" onClick={() => onDelete(row.id)}>
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            {!rows.length && <p className="empty-cell">Aucune note enregistree.</p>}
          </div>
        </div>
      </AsyncState>
    </section>
  );
}

function AcademicDocumentsTable({ rows, loading, error, onDelete }) {
  return (
    <section className="surface academic-data-card">
      <h3>Documents</h3>
      <AsyncState loading={loading} error={error}>
        <div className="desktop-table-wrap">
          <div className="desktop-table-header academic-document-columns">
            <span>Type</span>
            <span>Titre</span>
            <span>Categorie</span>
            <span>Auteur</span>
            <span>Date</span>
            <span>Fichier</span>
            <span></span>
          </div>
          <div className="desktop-table-body">
            {rows.map((row) => (
              <div className="desktop-table-row academic-document-columns" key={row.id}>
                <span>{documentTypeLabel(row.document_type)}</span>
                <strong>{row.title || "-"}</strong>
                <span>{row.category || "-"}</span>
                <span>{row.author || "-"}</span>
                <span>{formatDate(row.issue_date || row.created_at)}</span>
                <button
                  className="small-icon-button blue"
                  title="Telecharger"
                  disabled={!row.has_file_blob && !row.file_path}
                  onClick={() => downloadApiFile(`/api/academics/documents/${row.id}/download/`, row.title || "document")}
                >
                  <Download size={16} />
                </button>
                <button className="small-icon-button danger" title="Supprimer" onClick={() => onDelete(row.id)}>
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            {!rows.length && <p className="empty-cell">Aucun document enregistre.</p>}
          </div>
        </div>
      </AsyncState>
    </section>
  );
}

function initialGradeForm() {
  return {
    courseName: "",
    courseCode: "",
    credits: "",
    grade: "",
    semester: "Annual",
    examDate: new Date().toISOString().slice(0, 10),
    professorName: "",
    status: "PASSED",
    remarks: "",
  };
}

function initialDocumentForm() {
  return {
    documentType: "CERTIFICATE",
    title: "",
    category: "",
    author: "",
    issueDate: new Date().toISOString().slice(0, 10),
    description: "",
    file: null,
  };
}

function buildHierarchy(rows) {
  const faculties = new Map();
  rows.forEach((student) => {
    const facultyId = makeKey("faculty", student.faculty_id, student.faculty_name);
    const departmentId = makeKey("department", student.department_id, `${facultyId}-${student.department_name || ""}`);
    const promotionId = makeKey("promotion", student.promotion_id, `${departmentId}-${student.promotion_name || ""}`);

    if (!faculties.has(facultyId)) {
      faculties.set(facultyId, { id: facultyId, name: student.faculty_name || "Faculte non definie", departments: new Map(), count: 0 });
    }
    const faculty = faculties.get(facultyId);
    faculty.count += 1;

    if (!faculty.departments.has(departmentId)) {
      faculty.departments.set(departmentId, { id: departmentId, name: student.department_name || "Departement non defini", promotions: new Map(), count: 0 });
    }
    const department = faculty.departments.get(departmentId);
    department.count += 1;

    if (!department.promotions.has(promotionId)) {
      department.promotions.set(promotionId, { id: promotionId, name: student.promotion_name || "Promotion non definie", students: [] });
    }
    department.promotions.get(promotionId).students.push(student);
  });

  return {
    faculties: Array.from(faculties.values()).map((faculty) => ({
      ...faculty,
      departments: Array.from(faculty.departments.values()).map((department) => ({
        ...department,
        promotions: Array.from(department.promotions.values()).sort(sortByName),
      })).sort(sortByName),
    })).sort(sortByName),
  };
}

function makeKey(prefix, id, fallback) {
  return `${prefix}:${id || String(fallback || "unknown").toLowerCase()}`;
}

function sortByName(left, right) {
  return left.name.localeCompare(right.name, "fr");
}

function studentName(student) {
  return `${student?.firstname || ""} ${student?.lastname || ""}`.trim() || "-";
}

function formatAverage(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(2);
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "-";
  return Number(value).toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString("fr-FR");
}

function generateCourseCode(value) {
  const words = String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .match(/[A-Z0-9]+/g);
  if (!words || !words.length) return "";
  return words.map((word) => word.slice(0, 3)).join("").slice(0, 6) || "";
}

function statusLabel(value) {
  return {
    PASSED: "REUSSI",
    FAILED: "ECHOUE",
    IN_PROGRESS: "EN COURS",
    VALIDATED: "VALIDE",
  }[String(value || "").toUpperCase()] || value || "-";
}

function documentTypeLabel(value) {
  return {
    CERTIFICATE: "CERTIFICAT",
    DIPLOMA: "DIPLOME",
    REPORT: "RAPPORT",
    THESIS: "THESE",
    BOOK: "LIVRE",
    OTHER: "AUTRE",
  }[String(value || "").toUpperCase()] || value || "-";
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Lecture du fichier impossible."));
    reader.readAsDataURL(file);
  });
}

function fileExtension(filename) {
  const match = String(filename || "").match(/\.[a-z0-9]{1,8}$/i);
  return match ? match[0].toLowerCase() : ".bin";
}
