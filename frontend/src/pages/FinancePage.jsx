import { CreditCard, FileText, FolderOpen, Landmark, Layers3 } from "lucide-react";
import { useMemo, useState } from "react";

import { apiRequest } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { StudentPhoto } from "../components/StudentPhoto.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

export function FinancePage() {
  const { data, loading, error } = useApiResource("/api/finance/overview/?limit=500");
  const [filter, setFilter] = useState("all");
  const [facultyId, setFacultyId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [promotionId, setPromotionId] = useState("");
  const rows = data?.students || [];
  const paymentStatus = data?.payment_status || {};

  const hierarchy = useMemo(() => buildFinanceHierarchy(rows), [rows]);
  const selectedFaculty = hierarchy.find((faculty) => String(faculty.id) === String(facultyId));
  const departments = selectedFaculty?.departments || [];
  const selectedDepartment = departments.find((department) => String(department.id) === String(departmentId));
  const promotions = selectedDepartment?.promotions || [];
  const selectedPromotion = promotions.find((promotion) => String(promotion.id) === String(promotionId));

  const filteredRows = useMemo(
    () =>
      rows.filter((row) => {
        if (filter !== "all" && paymentCategory(row) !== filter) return false;
        if (facultyId && String(row.faculty_id || "") !== String(facultyId)) return false;
        if (departmentId && String(row.department_id || "") !== String(departmentId)) return false;
        if (promotionId && String(row.promotion_id || "") !== String(promotionId)) return false;
        return true;
      }),
    [rows, filter, facultyId, departmentId, promotionId],
  );
  const groupedRows = useMemo(() => groupFinanceRows(filteredRows), [filteredRows]);

  function chooseFaculty(value) {
    setFacultyId(value);
    setDepartmentId("");
    setPromotionId("");
  }

  function chooseDepartment(value) {
    setDepartmentId(value);
    setPromotionId("");
  }

  return (
    <section className="page finance-page desktop-page">
      <PageHeader title="Gestion Financière" subtitle="Suivi des paiements et seuils" />

      <AsyncState loading={loading} error={error}>
        <div className="metric-grid finance-filter-grid desktop-kpis">
          <FinanceKpi
            value={formatMoney(data?.revenue || 0)}
            label="Revenus Totaux"
            tone="green"
            active={filter === "all"}
            onClick={() => setFilter("all")}
          />
          <FinanceKpi
            value={Number(paymentStatus.eligible || 0)}
            label="Paiements Complètes"
            tone="blue"
            active={filter === "paid"}
            onClick={() => setFilter("paid")}
          />
          <FinanceKpi
            value={Number(paymentStatus.partial_paid || 0)}
            label="Paiements Partiels"
            tone="gold"
            active={filter === "partial"}
            onClick={() => setFilter("partial")}
          />
          <FinanceKpi
            value={Number(paymentStatus.never_paid || 0)}
            label="Non Payés"
            tone="red"
            active={filter === "unpaid"}
            onClick={() => setFilter("unpaid")}
          />
        </div>

        <div className="surface finance-hierarchy-bar">
          <label>
            <Landmark size={16} />
            Faculte
            <select value={facultyId} onChange={(event) => chooseFaculty(event.target.value)}>
              <option value="">Toutes les facultes</option>
              {hierarchy.map((faculty) => (
                <option key={faculty.id} value={faculty.id}>
                  {faculty.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <FolderOpen size={16} />
            Departement
            <select value={departmentId} onChange={(event) => chooseDepartment(event.target.value)} disabled={!facultyId}>
              <option value="">Tous les departements</option>
              {departments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <Layers3 size={16} />
            Promotion
            <select value={promotionId} onChange={(event) => setPromotionId(event.target.value)} disabled={!departmentId}>
              <option value="">Toutes les promotions</option>
              {promotions.map((promotion) => (
                <option key={promotion.id} value={promotion.id}>
                  {promotion.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="surface table-section desktop-table-card">
          <div className="section-title-row">
            <div>
              <h2>
                <FileText size={26} /> Historique des Paiements - {filterLabel(filter)}
              </h2>
              <span>{hierarchyLabel(selectedFaculty, selectedDepartment, selectedPromotion)}</span>
            </div>
          </div>

          <DesktopFinanceTable groups={groupedRows} />
        </div>
      </AsyncState>
    </section>
  );
}

function DesktopFinanceTable({ groups }) {
  return (
    <div className="desktop-table-wrap">
      <div className="desktop-table-header finance-columns">
        <span>Photo</span>
        <span>Étudiant</span>
        <span>ID</span>
        <span>Montant Payé ($)</span>
        <span>Seuil Requis ($)</span>
        <span>Statut</span>
        <span>Date</span>
      </div>
      <div className="desktop-table-body">
        {rows.length === 0 ? (
          <p className="empty-cell">Aucun paiement trouvé.</p>
        ) : (
          rows.map((row, index) => (
            <div className="desktop-table-row finance-columns" key={`${row.student_number}-${index}`}>
              <StudentPhoto student={row} />
              <span>{`${row.firstname || ""} ${row.lastname || ""}`.trim() || "-"}</span>
              <span className="muted-cell">{row.student_number || "-"}</span>
              <strong className="money-cell">{formatMoney(row.amount_paid || 0)}</strong>
              <span>{formatMoney(row.threshold_required || 0)}</span>
              <span className={`status-text ${paymentCategory(row)}`}>{paymentLabel(row)}</span>
              <span className="date-cell">{formatFinanceDate(row.last_payment_date)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function FinanceKpi({ value, label, tone, active, onClick }) {
  return (
    <button className={`metric ${tone} ${active ? "active" : ""}`} onClick={onClick}>
      <strong>{value}</strong>
      <span>{label}</span>
    </button>
  );
}

export function PaymentDialog({ student, onClose, onDone }) {
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    const amountNumber = Number(String(amount).replace(",", "."));
    if (!amountNumber || amountNumber <= 0) {
      setError("Montant invalide.");
      return;
    }
    setBusy(true);
    setProgress(10);
    const interval = window.setInterval(() => {
      setProgress((value) => Math.min(88, value + 18));
    }, 220);
    try {
      await apiRequest("/api/finance/payments/", {
        method: "POST",
        body: JSON.stringify({ student_id: student.id, amount: amountNumber }),
      });
      setProgress(100);
      window.setTimeout(onDone, 450);
    } catch (err) {
      setError(err.message);
      setBusy(false);
      setProgress(0);
    } finally {
      window.clearInterval(interval);
    }
  }

  return (
    <div className="modal-backdrop">
      <form className="desktop-dialog payment-dialog" onSubmit={submit}>
        <header className="dialog-header blue">
          <h2>
            <CreditCard size={24} /> Enregistrer un Paiement
          </h2>
          <p>{studentName(student)} - #{student.student_number}</p>
        </header>
        <div className="dialog-body">
          <label className="dialog-field">
            <span>Montant a payer</span>
            <input value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="Entrez le montant (ex: 50.00)" />
          </label>
          <div className="dialog-progress">
            <i style={{ width: `${progress}%` }} />
          </div>
          <strong className="progress-percent">{progress}%</strong>
          {error && <p className="error-text">{error}</p>}
          <button className="dialog-primary" disabled={busy}>
            Enregistrer le Paiement
          </button>
          <button type="button" className="dialog-secondary" onClick={onClose} disabled={busy}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}

export function PaymentHistoryDialog({ student, onClose }) {
  const { data, loading, error } = useApiResource(`/api/finance/students/${student.id}/history/`);
  const accessCode = useApiResource(`/api/finance/students/${student.id}/access-code/`);
  const [resendingCode, setResendingCode] = useState(false);
  const [resendFeedback, setResendFeedback] = useState(null);
  const rows = Array.isArray(data) ? data : [];
  let cumulative = 0;

  async function resendAccessCode() {
    setResendFeedback(null);
    setResendingCode(true);
    try {
      const payload = await apiRequest(`/api/finance/students/${student.id}/access-code/resend/`, { method: "POST" });
      setResendFeedback({ type: "success", message: payload.data?.message || "Code renvoye a l'etudiant." });
      accessCode.reload();
    } catch (err) {
      setResendFeedback({ type: "error", message: err.message || "Code non envoye." });
    } finally {
      setResendingCode(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <section className="desktop-dialog history-dialog">
        <header className="dialog-header purple">
          <h2>
            <FileText size={24} /> Historique des Paiements
          </h2>
          <p>{studentName(student)} - #{student.student_number}</p>
        </header>
        <div className="dialog-body light-dialog-body">
          <div className="access-code-toolbar">
            <strong className="access-code-line">
              Code actuel: {accessCode.data?.access_code || "Aucun code"} {accessCode.data?.access_type ? `(${accessCode.data.access_type})` : ""}
            </strong>
            <button type="button" className="dialog-primary" onClick={resendAccessCode} disabled={resendingCode || !accessCode.data?.access_code}>
              {resendingCode ? "Envoi..." : "Renvoyer le code"}
            </button>
          </div>
          {resendFeedback && <p className={resendFeedback.type === "success" ? "success-text" : "error-text"}>{resendFeedback.message}</p>}
          <AsyncState loading={loading} error={error}>
            <div className="history-table">
              <div className="desktop-table-header history-columns">
                <span>Date</span>
                <span>Montant ($)</span>
                <span>Methode</span>
              </div>
              {rows.map((row, index) => {
                const amount = Number(row.amount_paid_usd || row.amount || 0);
                cumulative += amount;
                return (
                  <div className="desktop-table-row history-columns" key={index}>
                    <span>{formatDateTime(row.created_at || row.payment_date)}</span>
                    <span>
                      {amount.toFixed(2)}
                      <br />
                      Cumul: {cumulative.toFixed(2)}
                    </span>
                    <span>{row.payment_method || "Paiement bancaire"}</span>
                  </div>
                );
              })}
              {rows.length === 0 && <p className="empty-cell">Aucun paiement enregistre.</p>}
            </div>
          </AsyncState>
          <button className="dialog-secondary" onClick={onClose}>
            Fermer
          </button>
        </div>
      </section>
    </div>
  );
}

function paymentCategory(row) {
  const paid = Number(row.amount_paid || 0);
  const threshold = Number(row.threshold_required || 0);
  if (paid <= 0) return "unpaid";
  if (row.is_eligible || (threshold > 0 && paid >= threshold)) return "paid";
  return "partial";
}

function paymentLabel(row) {
  const category = paymentCategory(row);
  if (category === "paid") return "Payé";
  if (category === "partial") return "Partiel";
  return "Non payé";
}

function filterLabel(value) {
  return {
    all: "Tous",
    paid: "Payés Complètement",
    partial: "Paiements partiels",
    unpaid: "Non Payés",
  }[value];
}

function studentName(row) {
  return `${row.firstname || ""} ${row.lastname || ""}`.trim() || "-";
}

function formatMoney(value) {
  return `$${Number(value || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatFinanceDate(value) {
  if (!value) return "-";
  const raw = String(value);
  const date = new Date(raw.includes(" ") ? raw.replace(" ", "T") : raw);
  if (Number.isNaN(date.getTime())) return String(value);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const min = String(date.getMinutes()).padStart(2, "0");
  const sec = String(date.getSeconds()).padStart(2, "0");
  const hasTime = hh !== "00" || min !== "00" || sec !== "00";
  return hasTime ? `${yyyy}-${mm}-${dd}\n${hh}:${min}:${sec}` : `${yyyy}-${mm}-${dd}`;
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
