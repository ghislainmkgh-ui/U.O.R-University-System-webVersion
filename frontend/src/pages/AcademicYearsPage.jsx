import { CalendarRange, GraduationCap, Landmark, Repeat, Save, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";

import { apiRequest } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { useApiResource } from "../hooks/useApiResource.js";
import { useAuth } from "../state/AuthContext.jsx";

export function AcademicYearsPage() {
  const auth = useAuth();
  const promotions = useApiResource("/api/finance/promotions/");
  const years = useApiResource("/api/finance/academic-years/");
  const [faculty, setFaculty] = useState("all");
  const [message, setMessage] = useState("");
  const [showPeriods, setShowPeriods] = useState(false);
  const [showMigration, setShowMigration] = useState(false);
  const rows = Array.isArray(promotions.data) ? promotions.data : [];
  const yearRows = Array.isArray(years.data) ? years.data : [];
  const isSuperAdmin = String(auth.user?.role || "").toLowerCase() === "super_admin";

  const faculties = useMemo(() => Array.from(new Set(rows.map((row) => row.faculty_name).filter(Boolean))).sort(), [rows]);
  const filteredRows = faculty === "all" ? rows : rows.filter((row) => row.faculty_name === faculty);

  async function savePromotion(row, fee, threshold) {
    setMessage("");
    if (Number(threshold) > Number(fee)) {
      setMessage("Le seuil ne peut pas dépasser les frais académiques.");
      return;
    }
    try {
      await apiRequest(`/api/finance/promotions/${row.id}/financials/`, {
        method: "POST",
        body: JSON.stringify({ fee_usd: Number(fee), threshold_amount: Number(threshold) }),
      });
      setMessage("Paramètres financiers enregistrés.");
      promotions.reload();
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <section className="page academic-years-page desktop-page">
      <PageHeader title="Années Académiques" subtitle="Gestion des seuils financiers et périodes d'examens" />

      <AsyncState loading={promotions.loading || years.loading} error={promotions.error || years.error}>
        <div className="surface academic-years-card">
          <div className="academic-toolbar">
            <div className="academic-toolbar-main">
              <h2>
                <GraduationCap size={25} /> Frais & Seuils par Faculté → Promotion
              </h2>
              <label>
                <Landmark size={18} />
                <span>Faculté:</span>
                <select value={faculty} onChange={(event) => setFaculty(event.target.value)}>
                  <option value="all">Toutes Facultés</option>
                  {faculties.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="academic-actions">
              {isSuperAdmin && (
                <button className="warning-button" onClick={() => setShowMigration(true)}>
                  <Repeat size={17} /> Bascule étudiants (année)
                </button>
              )}
              <button className="primary-button" onClick={() => setShowPeriods(true)}>
                <CalendarRange size={17} /> Gérer les périodes d'examens
              </button>
            </div>
          </div>

          {message && <p className={message.includes("enregistrés") ? "success-text" : "error-text"}>{message}</p>}

          <div className="desktop-table-wrap academic-table-wrap">
            <div className="desktop-table-header academic-columns">
              <span>Faculté</span>
              <span>Promotion</span>
              <span>Département</span>
              <span>Année</span>
              <span>Frais ($)</span>
              <span>Seuil ($)</span>
              <span>Action</span>
            </div>
            <div className="desktop-table-body academic-rows">
              {filteredRows.map((row) => (
                <PromotionFinanceRow key={row.id} row={row} onSave={savePromotion} />
              ))}
              {filteredRows.length === 0 && <p className="empty-cell">Aucune promotion trouvée.</p>}
            </div>
          </div>
        </div>
      </AsyncState>

      {showPeriods && <ExamPeriodsDialog years={yearRows} onClose={() => setShowPeriods(false)} />}
      {showMigration && <AcademicMigrationDialog years={yearRows} onClose={() => setShowMigration(false)} />}
    </section>
  );
}

function PromotionFinanceRow({ row, onSave }) {
  const [fee, setFee] = useState(row.fee_usd || 0);
  const [threshold, setThreshold] = useState(row.threshold_amount || 0);

  return (
    <div className="desktop-table-row academic-columns">
      <span className="muted-cell">{row.faculty_name || "-"}</span>
      <span>{row.name || "-"}</span>
      <span className="muted-cell">{row.department_name || "-"}</span>
      <span>{row.year || "-"}</span>
      <input value={fee} onChange={(event) => setFee(event.target.value)} />
      <input value={threshold} onChange={(event) => setThreshold(event.target.value)} />
      <button className="small-save-button" onClick={() => onSave(row, fee, threshold)}>
        <Save size={16} /> Enregistrer
      </button>
    </div>
  );
}

function ExamPeriodsDialog({ years, onClose }) {
  const yearOptions = Array.isArray(years) ? years : [];
  const [selectedYear, setSelectedYear] = useState(() => String(yearId(yearOptions.find((year) => year.is_active)) || yearId(yearOptions[0]) || ""));
  const [form, setForm] = useState({ period_name: "", start_date: "", end_date: "" });
  const [message, setMessage] = useState("");
  const periods = useApiResource(`/api/finance/exam-periods/?academic_year_id=${selectedYear || 0}`);
  const rows = Array.isArray(periods.data) ? periods.data : [];

  async function addPeriod(event) {
    event.preventDefault();
    setMessage("");
    try {
      await apiRequest("/api/finance/exam-periods/", {
        method: "POST",
        body: JSON.stringify({ ...form, academic_year_id: Number(selectedYear) }),
      });
      setForm({ period_name: "", start_date: "", end_date: "" });
      setMessage("Période créée.");
      periods.reload();
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function deletePeriod(periodId) {
    setMessage("");
    try {
      await apiRequest(`/api/finance/exam-periods/${periodId}/`, { method: "DELETE" });
      setMessage("Période supprimée.");
      periods.reload();
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <div className="modal-backdrop">
      <section className="desktop-dialog exam-period-dialog">
        <header className="dialog-header blue">
          <h2>
            <CalendarRange size={24} /> Gestion des Périodes d'Examens
          </h2>
          <p>Créez et organisez les sessions d'examen</p>
        </header>
        <div className="dialog-body">
          <label className="dialog-field">
            <span>Année académique</span>
            <select value={selectedYear} onChange={(event) => setSelectedYear(event.target.value)}>
              {yearOptions.map((year) => (
                <option key={yearId(year)} value={yearId(year)}>
                  {yearName(year)}
                </option>
              ))}
            </select>
          </label>
          <form className="exam-period-form" onSubmit={addPeriod}>
            <input value={form.period_name} placeholder="Nom de la période" onChange={(event) => setForm((current) => ({ ...current, period_name: event.target.value }))} />
            <input type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} />
            <input type="date" value={form.end_date} onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} />
            <button className="dialog-primary">Valider</button>
          </form>
          {message && <p className={message.includes("créée") || message.includes("supprimée") ? "success-text" : "error-text"}>{message}</p>}
          <AsyncState loading={periods.loading} error={periods.error}>
            <div className="period-list">
              {rows.map((period) => (
                <div className="period-row" key={period.exam_period_id || period.id}>
                  <span>
                    <strong>{period.period_name || period.name}</strong>
                    <small>
                      {period.start_date} → {period.end_date}
                    </small>
                  </span>
                  <button className="small-icon-button danger" title="Supprimer" onClick={() => deletePeriod(period.exam_period_id || period.id)}>
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
              {rows.length === 0 && <p className="empty-cell">Aucune période enregistrée.</p>}
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

function AcademicMigrationDialog({ years, onClose }) {
  const yearOptions = Array.isArray(years) ? years : [];
  const [fromYear, setFromYear] = useState(() => String(yearId(yearOptions[0]) || ""));
  const [toYear, setToYear] = useState(() => String(yearId(yearOptions[1]) || yearId(yearOptions[0]) || ""));
  const [eligibleOnly, setEligibleOnly] = useState(false);
  const [dryRun, setDryRun] = useState(true);
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setResult("");
    try {
      const payload = await apiRequest("/api/finance/academic-year-migration/", {
        method: "POST",
        body: JSON.stringify({
          from_academic_year_id: Number(fromYear),
          to_academic_year_id: Number(toYear),
          eligible_only: eligibleOnly,
          dry_run: dryRun,
        }),
      });
      setResult(payload.data?.message || payload.message || "Bascule traitée.");
    } catch (err) {
      setResult(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <form className="desktop-dialog migration-dialog" onSubmit={submit}>
        <header className="dialog-header gold">
          <h2>
            <Repeat size={24} /> Bascule étudiants (année)
          </h2>
          <p>Vérifiez en simulation avant de lancer la bascule réelle</p>
        </header>
        <div className="dialog-body">
          <label className="dialog-field">
            <span>Année source</span>
            <select value={fromYear} onChange={(event) => setFromYear(event.target.value)}>
              {yearOptions.map((year) => (
                <option key={yearId(year)} value={yearId(year)}>
                  {yearName(year)}
                </option>
              ))}
            </select>
          </label>
          <label className="dialog-field">
            <span>Année destination</span>
            <select value={toYear} onChange={(event) => setToYear(event.target.value)}>
              {yearOptions.map((year) => (
                <option key={yearId(year)} value={yearId(year)}>
                  {yearName(year)}
                </option>
              ))}
            </select>
          </label>
          <label className="check-line">
            <input type="checkbox" checked={eligibleOnly} onChange={(event) => setEligibleOnly(event.target.checked)} />
            Étudiants éligibles seulement
          </label>
          <label className="check-line">
            <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />
            Simulation sans modification
          </label>
          {result && <p className={result.toLowerCase().includes("erreur") ? "error-text" : "success-text"}>{result}</p>}
          <div className="dialog-actions">
            <button type="button" className="dialog-secondary" onClick={onClose} disabled={busy}>
              <X size={16} /> Annuler
            </button>
            <button className="dialog-primary" disabled={busy}>
              Lancer
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

function yearId(year) {
  return year?.academic_year_id || year?.id || "";
}

function yearName(year) {
  return year?.year_name || year?.name || `Année ${yearId(year)}`;
}
