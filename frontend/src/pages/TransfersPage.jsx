import {
  CheckSquare,
  Eye,
  FileJson,
  History,
  RefreshCw,
  Save,
  Search,
  Send,
  UserRound,
  XSquare,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { apiRequest } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { StudentPhoto } from "../components/StudentPhoto.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

const transferTabs = [
  { key: "outgoing", label: "Transferts Sortants", icon: Send },
  { key: "incoming", label: "Demandes Entrantes", icon: CheckSquare },
  { key: "history", label: "Historique", icon: History },
];

export function TransfersPage() {
  const students = useApiResource("/api/students/");
  const partners = useApiResource("/api/transfers/partners/");
  const pending = useApiResource("/api/transfers/pending/");
  const history = useApiResource("/api/transfers/history/?limit=80");
  const studentRows = Array.isArray(students.data) ? students.data : [];
  const partnerRows = Array.isArray(partners.data) ? partners.data : [];
  const pendingRows = Array.isArray(pending.data) ? pending.data : [];
  const historyRows = Array.isArray(history.data) ? history.data : [];
  const hierarchy = useMemo(() => buildHierarchy(studentRows), [studentRows]);
  const promotionOptions = useMemo(() => flattenPromotions(hierarchy), [hierarchy]);

  const [activeTab, setActiveTab] = useState("outgoing");
  const [facultyId, setFacultyId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [promotionId, setPromotionId] = useState("");
  const [query, setQuery] = useState("");
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [selectedPartnerCode, setSelectedPartnerCode] = useState("");
  const [apiUrlDraft, setApiUrlDraft] = useState("");
  const [includeDocuments, setIncludeDocuments] = useState(true);
  const [notes, setNotes] = useState("");
  const [targetPromotionByRequest, setTargetPromotionByRequest] = useState({});
  const [noteByRequest, setNoteByRequest] = useState({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [actionError, setActionError] = useState("");
  const [packageModal, setPackageModal] = useState(null);

  useEffect(() => {
    if (!hierarchy.faculties.length) return;
    const nextFaculty = hierarchy.faculties.find((faculty) => faculty.id === facultyId) || hierarchy.faculties[0];
    const nextDepartment = nextFaculty.departments.find((department) => department.id === departmentId) || nextFaculty.departments[0];
    const nextPromotion = nextDepartment?.promotions.find((promotion) => promotion.id === promotionId) || nextDepartment?.promotions[0];
    if (nextFaculty.id !== facultyId) setFacultyId(nextFaculty.id);
    if ((nextDepartment?.id || "") !== departmentId) setDepartmentId(nextDepartment?.id || "");
    if ((nextPromotion?.id || "") !== promotionId) setPromotionId(nextPromotion?.id || "");
  }, [hierarchy, facultyId, departmentId, promotionId]);

  useEffect(() => {
    if (!selectedPartnerCode && partnerRows.length) {
      setSelectedPartnerCode(partnerRows[0].university_code || "");
    }
  }, [partnerRows, selectedPartnerCode]);

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

  const selectedPartner = partnerRows.find((partner) => partner.university_code === selectedPartnerCode);

  useEffect(() => {
    setApiUrlDraft(selectedPartner?.api_url || selectedPartner?.api_endpoint || "");
  }, [selectedPartner]);

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

  function reloadTransfers() {
    students.reload();
    partners.reload();
    pending.reload();
    history.reload();
  }

  async function savePartnerApiUrl() {
    if (!selectedPartnerCode) return;
    setMessage("");
    setActionError("");
    setBusy(true);
    try {
      await apiRequest(`/api/transfers/partners/${encodeURIComponent(selectedPartnerCode)}/api-url/`, {
        method: "PATCH",
        body: JSON.stringify({ api_url: apiUrlDraft }),
      });
      setMessage("URL API partenaire sauvegardee.");
      partners.reload();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function generateOutgoingTransfer(event) {
    event.preventDefault();
    setMessage("");
    setActionError("");
    if (!selectedStudent) {
      setActionError("Veuillez selectionner un etudiant.");
      return;
    }
    if (!selectedPartner) {
      setActionError("Veuillez selectionner une universite partenaire.");
      return;
    }
    setBusy(true);
    try {
      const payload = await apiRequest("/api/transfers/outgoing/", {
        method: "POST",
        body: JSON.stringify({
          student_id: selectedStudent.id,
          destination_university: selectedPartner.university_name,
          destination_university_code: selectedPartner.university_code,
          include_documents: includeDocuments,
          notes,
        }),
      });
      const result = payload?.data || payload || {};
      setMessage(`Transfert genere: ${result.transfer_code || "package cree"}.`);
      setNotes("");
      history.reload();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function approveIncoming(row) {
    const targetPromotionId = targetPromotionByRequest[row.id];
    if (!targetPromotionId) {
      setActionError("Veuillez choisir une promotion cible avant d'approuver.");
      return;
    }
    setMessage("");
    setActionError("");
    setBusy(true);
    try {
      await apiRequest(`/api/transfers/incoming/${row.id}/approve/`, {
        method: "POST",
        body: JSON.stringify({
          target_promotion_id: Number(targetPromotionId),
          approval_notes: noteByRequest[row.id] || "",
        }),
      });
      setMessage("Demande de transfert approuvee.");
      pending.reload();
      history.reload();
      students.reload();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function rejectIncoming(row) {
    setMessage("");
    setActionError("");
    setBusy(true);
    try {
      await apiRequest(`/api/transfers/incoming/${row.id}/reject/`, {
        method: "POST",
        body: JSON.stringify({ reason: noteByRequest[row.id] || "Rejete depuis l'interface web." }),
      });
      setMessage("Demande de transfert rejetee.");
      pending.reload();
      history.reload();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function viewPackage(transferCode) {
    setActionError("");
    setPackageModal({ code: transferCode, loading: true, content: "" });
    try {
      const payload = await apiRequest(`/api/transfers/packages/${encodeURIComponent(transferCode)}/`);
      const result = payload?.data || payload || {};
      setPackageModal({ code: transferCode, loading: false, content: result.package_json || JSON.stringify(result, null, 2) });
    } catch (err) {
      setPackageModal(null);
      setActionError(err.message);
    }
  }

  return (
    <section className="page transfers-page desktop-page">
      <PageHeader title="Transferts Inter-Universitaires" subtitle="Transferts sortants, demandes entrantes et historique">
        <button className="primary-button" onClick={reloadTransfers}>
          <RefreshCw size={18} />
          Actualiser
        </button>
      </PageHeader>

      <div className="surface transfer-tabs-card">
        {transferTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button key={tab.key} className={activeTab === tab.key ? "active" : ""} onClick={() => setActiveTab(tab.key)}>
              <Icon size={18} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {message && <p className="success-text transfer-feedback">{message}</p>}
      {actionError && <p className="error-text transfer-feedback">{actionError}</p>}

      {activeTab === "outgoing" && (
        <AsyncState loading={students.loading || partners.loading} error={students.error || partners.error}>
          <div className="surface transfer-work-card">
            <div className="transfer-card-heading">
              <Send size={24} />
              <div>
                <h2>Initier un Transfert Sortant</h2>
                <span>Selection : Faculte / Departement / Promotion / Etudiant</span>
              </div>
            </div>

            <div className="transfer-two-columns">
              <aside className="transfer-left-column">
                <section className="nested-panel">
                  <h3>Selection Hierarchique</h3>
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
                </section>

                <section className="nested-panel transfer-students-panel">
                  <h3>Etudiants</h3>
                  <div className="search-line">
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
                    {!visibleStudents.length && <p className="empty-cell">Aucun etudiant actif dans cette promotion.</p>}
                  </div>
                </section>
              </aside>

              <form className="transfer-right-column" onSubmit={generateOutgoingTransfer}>
                <section className="nested-panel transfer-student-summary">
                  <h3>Informations Etudiant</h3>
                  {selectedStudent ? (
                    <div className="selected-student-line">
                      <StudentPhoto student={selectedStudent} size="medium" />
                      <div>
                        <strong>{studentName(selectedStudent)}</strong>
                        <span>{selectedStudent.student_number || "-"} | {selectedStudent.promotion_name || "-"}</span>
                        <small>{selectedStudent.email || "Email non renseigne"}</small>
                      </div>
                    </div>
                  ) : (
                    <p className="empty-cell">Selectionner un etudiant.</p>
                  )}
                </section>

                <section className="nested-panel">
                  <h3>Details du Transfert</h3>
                  <label className="desktop-field">
                    <span>Universite de destination</span>
                    <select value={selectedPartnerCode} onChange={(event) => setSelectedPartnerCode(event.target.value)}>
                      {partnerRows.map((partner) => (
                        <option key={partner.university_code} value={partner.university_code}>
                          {partner.university_name} ({partner.university_code}) - {partner.country || "-"}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="desktop-field">
                    <span>URL API de reception</span>
                    <input value={apiUrlDraft} onChange={(event) => setApiUrlDraft(event.target.value)} placeholder="https://..." />
                  </label>
                  <button type="button" className="dialog-primary" onClick={savePartnerApiUrl} disabled={busy || !selectedPartnerCode}>
                    <Save size={16} />
                    Sauvegarder l'URL API
                  </button>
                  <label className="check-line">
                    <input type="checkbox" checked={includeDocuments} onChange={(event) => setIncludeDocuments(event.target.checked)} />
                    <span>Inclure les documents et ouvrages</span>
                  </label>
                  <label className="desktop-field">
                    <span>Notes</span>
                    <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Notes optionnelles" />
                  </label>
                  <div className="dialog-actions">
                    <button className="dialog-primary green" disabled={busy}>
                      <Send size={16} />
                      Generer
                    </button>
                    <button type="button" className="dialog-secondary" onClick={reloadTransfers} disabled={busy}>
                      Rafraichir
                    </button>
                  </div>
                </section>
              </form>
            </div>
          </div>
        </AsyncState>
      )}

      {activeTab === "incoming" && (
        <AsyncState loading={pending.loading} error={pending.error}>
          <section className="surface transfer-work-card">
            <div className="transfer-card-heading">
              <CheckSquare size={24} />
              <div>
                <h2>Demandes de Transfert Entrantes</h2>
                <span>{pendingRows.length} demande(s) en attente</span>
              </div>
            </div>
            <div className="transfer-request-list">
              {pendingRows.map((row) => (
                <article className="transfer-request-card" key={row.id || row.request_code}>
                  <header>
                    <div>
                      <h3>
                        <UserRound size={18} />
                        {row.external_firstname || ""} {row.external_lastname || ""}
                      </h3>
                      <span>{row.request_code || "-"}</span>
                    </div>
                    <strong>EN ATTENTE</strong>
                  </header>
                  <p>
                    Universite source: {row.source_university || "-"} ({row.source_university_code || "N/A"})
                    <br />
                    Email: {row.external_email || "N/A"} | Telephone: {row.external_phone || "N/A"}
                    <br />
                    Date: {formatDateTime(row.requested_date || row.created_at)}
                  </p>
                  <div className="transfer-request-actions">
                    <select
                      value={targetPromotionByRequest[row.id] || ""}
                      onChange={(event) => setTargetPromotionByRequest((state) => ({ ...state, [row.id]: event.target.value }))}
                    >
                      <option value="">Promotion cible</option>
                      {promotionOptions.map((promotion) => (
                        <option key={promotion.id} value={promotion.rawId || ""} disabled={!promotion.rawId}>
                          {promotion.name}
                        </option>
                      ))}
                    </select>
                    <input
                      value={noteByRequest[row.id] || ""}
                      onChange={(event) => setNoteByRequest((state) => ({ ...state, [row.id]: event.target.value }))}
                      placeholder="Note de decision"
                    />
                    <button className="dialog-primary green" onClick={() => approveIncoming(row)} disabled={busy}>
                      <CheckSquare size={16} />
                      Approuver
                    </button>
                    <button className="dialog-primary danger-button" onClick={() => rejectIncoming(row)} disabled={busy}>
                      <XSquare size={16} />
                      Rejeter
                    </button>
                  </div>
                </article>
              ))}
              {!pendingRows.length && <p className="empty-cell">Aucune demande de transfert en attente.</p>}
            </div>
          </section>
        </AsyncState>
      )}

      {activeTab === "history" && (
        <AsyncState loading={history.loading} error={history.error}>
          <section className="surface transfer-work-card">
            <div className="transfer-card-heading">
              <History size={24} />
              <div>
                <h2>Historique des Transferts</h2>
                <span>{historyRows.length} transfert(s) recents</span>
              </div>
            </div>
            <div className="desktop-table-wrap transfer-history-table">
              <div className="desktop-table-header transfer-history-columns">
                <span>Code</span>
                <span>Etudiant</span>
                <span>Type</span>
                <span>Universite</span>
                <span>Date</span>
                <span>Statut</span>
                <span>Livraison</span>
                <span>Details</span>
              </div>
              <div className="desktop-table-body">
                {historyRows.map((row) => (
                  <div className="desktop-table-row transfer-history-columns" key={row.transfer_code || row.id}>
                    <span>{shortCode(row.transfer_code)}</span>
                    <span>{studentName(row)}</span>
                    <span>{row.transfer_type === "OUTGOING" ? "Sortant" : "Entrant"}</span>
                    <span>{row.destination_university || row.source_university || "-"}</span>
                    <span>{formatDate(row.transfer_date || row.created_at)}</span>
                    <span className={`status-pill ${statusTone(row.status)}`}>{row.status || "-"}</span>
                    <span className={`status-pill ${deliveryTone(row.delivery_status)}`}>{deliveryLabel(row.delivery_status)}</span>
                    <button className="small-icon-button blue" title="Voir le package" onClick={() => viewPackage(row.transfer_code)}>
                      <Eye size={16} />
                    </button>
                  </div>
                ))}
                {!historyRows.length && <p className="empty-cell">Aucun transfert enregistre.</p>}
              </div>
            </div>
          </section>
        </AsyncState>
      )}

      {packageModal && (
        <div className="modal-backdrop">
          <section className="desktop-dialog transfer-package-dialog">
            <header className="dialog-header purple">
              <h2>
                <FileJson size={24} /> Details du Transfert
              </h2>
              <p>{packageModal.code}</p>
            </header>
            <div className="dialog-body">
              {packageModal.loading ? <p>Chargement...</p> : <pre className="json-preview">{prettyJson(packageModal.content)}</pre>}
              <button className="dialog-secondary" onClick={() => setPackageModal(null)}>
                Fermer
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

function buildHierarchy(rows) {
  const faculties = new Map();
  rows.forEach((student) => {
    const facultyId = makeKey("faculty", student.faculty_id, student.faculty_name);
    const departmentId = makeKey("department", student.department_id, `${facultyId}-${student.department_name || ""}`);
    const promotionId = makeKey("promotion", student.promotion_id, `${departmentId}-${student.promotion_name || ""}`);
    if (!faculties.has(facultyId)) {
      faculties.set(facultyId, { id: facultyId, name: student.faculty_name || "Faculte non definie", departments: new Map() });
    }
    const faculty = faculties.get(facultyId);
    if (!faculty.departments.has(departmentId)) {
      faculty.departments.set(departmentId, { id: departmentId, name: student.department_name || "Departement non defini", promotions: new Map() });
    }
    const department = faculty.departments.get(departmentId);
    if (!department.promotions.has(promotionId)) {
      department.promotions.set(promotionId, {
        id: promotionId,
        rawId: student.promotion_id,
        name: student.promotion_name || "Promotion non definie",
        students: [],
      });
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

function flattenPromotions(hierarchy) {
  return hierarchy.faculties.flatMap((faculty) =>
    faculty.departments.flatMap((department) =>
      department.promotions.map((promotion) => ({
        id: promotion.id,
        rawId: promotion.rawId,
        name: `${faculty.name} / ${department.name} / ${promotion.name}`,
      })),
    ),
  );
}

function makeKey(prefix, id, fallback) {
  return `${prefix}:${id || String(fallback || "unknown").toLowerCase()}`;
}

function sortByName(left, right) {
  return left.name.localeCompare(right.name, "fr");
}

function studentName(row) {
  return `${row?.firstname || row?.external_firstname || ""} ${row?.lastname || row?.external_lastname || ""}`.trim() || "-";
}

function shortCode(value) {
  const code = String(value || "-");
  return code.length > 16 ? `${code.slice(0, 16)}...` : code;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString("fr-FR");
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function statusTone(value) {
  const status = String(value || "").toUpperCase();
  if (status === "COMPLETED" || status === "APPROVED") return "ok";
  if (status === "REJECTED" || status === "CANCELLED") return "bad";
  return "warn";
}

function deliveryTone(value) {
  const status = String(value || "").toLowerCase();
  if (status === "envoye" || status === "sent") return "ok";
  if (status === "echec" || status === "failed") return "bad";
  return "warn";
}

function deliveryLabel(value) {
  return {
    envoye: "Envoye",
    echec: "Echec",
    non_envoye: "Non envoye",
  }[String(value || "").toLowerCase()] || value || "Non envoye";
}

function prettyJson(content) {
  if (!content) return "{}";
  try {
    return JSON.stringify(typeof content === "string" ? JSON.parse(content) : content, null, 2);
  } catch {
    return String(content);
  }
}
