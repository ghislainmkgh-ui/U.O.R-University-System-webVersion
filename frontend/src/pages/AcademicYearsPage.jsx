import {
  CalendarRange,
  CheckCircle2,
  GraduationCap,
  Landmark,
  Plus,
  Repeat,
  Save,
  Settings,
  Trash2,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

import { apiRequest } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { useApiResource } from "../hooks/useApiResource.js";
import { useAuth } from "../state/AuthContext.jsx";

const defaultYearForm = {
  year_name: "",
  start_date: "",
  end_date: "",
  is_active: true,
};

export function AcademicYearsPage() {
  const auth = useAuth();
  const promotions = useApiResource("/api/finance/promotions/");
  const years = useApiResource("/api/finance/academic-years/?financials=true");
  const [faculty, setFaculty] = useState("all");
  const [message, setMessage] = useState("");
  const [showPeriods, setShowPeriods] = useState(false);
  const [showMigration, setShowMigration] = useState(false);
  const rows = Array.isArray(promotions.data) ? promotions.data : [];
  const yearRows = Array.isArray(years.data) ? years.data : [];
  const role = String(auth.user?.role || "").toLowerCase();
  const isSuperAdmin = role === "super_admin";
  const canCreateYears = role === "super_admin" || role === "admin";

  const faculties = useMemo(() => Array.from(new Set(rows.map((row) => row.faculty_name).filter(Boolean))).sort(), [rows]);
  const filteredRows = faculty === "all" ? rows : rows.filter((row) => row.faculty_name === faculty);

  async function savePromotion(row, fee, threshold) {
    setMessage("");
    if (!isSuperAdmin) {
      setMessage("Seul le super admin peut modifier les frais et les seuils.");
      return;
    }
    if (Number(threshold) > Number(fee)) {
      setMessage("Le seuil ne peut pas depasser les frais academiques.");
      return;
    }
    try {
      await apiRequest(`/api/finance/promotions/${row.id}/financials/`, {
        method: "POST",
        body: JSON.stringify({ fee_usd: Number(fee), threshold_amount: Number(threshold) }),
      });
      setMessage("Parametres financiers enregistres.");
      promotions.reload();
    } catch (err) {
      setMessage(err.message);
    }
  }

  function reloadYears() {
    years.reload();
  }

  return (
    <section className="page academic-years-page desktop-page">
      <PageHeader title="Annees Academiques" subtitle="Configuration de l'annee active, des periodes d'examens et des copies d'etudiants" />

      <AsyncState loading={years.loading} error={years.error}>
        <AcademicYearManager years={yearRows} canCreate={canCreateYears} canEdit={isSuperAdmin} onReload={reloadYears} />
      </AsyncState>

      <AsyncState loading={promotions.loading || years.loading} error={promotions.error || years.error}>
        <div className="surface academic-years-card">
          <div className="academic-toolbar">
            <div className="academic-toolbar-main">
              <h2>
                <GraduationCap size={25} /> Frais & Seuils par Faculte - Promotion
              </h2>
              <label>
                <Landmark size={18} />
                <span>Faculte:</span>
                <select value={faculty} onChange={(event) => setFaculty(event.target.value)}>
                  <option value="all">Toutes Facultes</option>
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
                  <Repeat size={17} /> Copier vers une annee
                </button>
              )}
              <button className="primary-button" onClick={() => setShowPeriods(true)}>
                <CalendarRange size={17} /> Gerer les periodes d'examens
              </button>
            </div>
          </div>

          {message && <p className={message.includes("enregistres") ? "success-text" : "error-text"}>{message}</p>}

          <div className="desktop-table-wrap academic-table-wrap">
            <div className="desktop-table-header academic-columns">
              <span>Faculte</span>
              <span>Promotion</span>
              <span>Departement</span>
              <span>Annee</span>
              <span>Frais ($)</span>
              <span>Seuil ($)</span>
              <span>Action</span>
            </div>
            <div className="desktop-table-body academic-rows">
              {filteredRows.map((row) => (
                <PromotionFinanceRow key={row.id} row={row} canEdit={isSuperAdmin} onSave={savePromotion} />
              ))}
              {filteredRows.length === 0 && <p className="empty-cell">Aucune promotion trouvee.</p>}
            </div>
          </div>
        </div>
      </AsyncState>

      {showPeriods && <ExamPeriodsDialog years={yearRows} onClose={() => setShowPeriods(false)} />}
      {showMigration && <AcademicMigrationDialog years={yearRows} onClose={() => setShowMigration(false)} />}
    </section>
  );
}

function AcademicYearManager({ years, canCreate, canEdit, onReload }) {
  const yearOptions = Array.isArray(years) ? years : [];
  const currentActiveId = String(yearId(yearOptions.find((year) => isActiveYear(year))) || "");
  const [form, setForm] = useState(defaultYearForm);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function createYear(event) {
    event.preventDefault();
    setMessage("");

    if (!form.year_name.trim()) {
      setMessage("Le nom de l'annee academique est requis.");
      return;
    }
    if (form.start_date && form.end_date && form.start_date > form.end_date) {
      setMessage("La date de debut doit etre avant la date de fin.");
      return;
    }

    setBusy(true);
    try {
      await apiRequest("/api/finance/academic-years/", {
        method: "POST",
        body: JSON.stringify({
          year_name: form.year_name.trim(),
          start_date: form.start_date || null,
          end_date: form.end_date || null,
          is_active: form.is_active,
        }),
      });
      setForm(defaultYearForm);
      setMessage("Annee academique creee avec succes.");
      onReload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="surface academic-years-card academic-management-card">
      <div className="academic-toolbar academic-toolbar-compact">
        <div className="academic-toolbar-main">
          <h2>
            <Settings size={24} /> Gestion des annees academiques
          </h2>
          <p className="muted-cell">Creez l'annee courante ici. Une seule annee reste active; les anciennes deviennent inactives.</p>
        </div>
      </div>

      {canCreate && (
        <form className="academic-year-create-form" onSubmit={createYear}>
          <input value={form.year_name} placeholder="Ex: 2026-2027" onChange={(event) => setForm((current) => ({ ...current, year_name: event.target.value }))} />
          <input type="date" value={form.start_date} title="Date de debut" onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} />
          <input type="date" value={form.end_date} title="Date de fin" onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} />
          <label className="check-line academic-active-check">
            <input type="checkbox" checked={form.is_active} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} />
            Activer
          </label>
          <button className="primary-button" disabled={busy}>
            <Plus size={17} /> Ajouter
          </button>
        </form>
      )}

      {message && <p className={message.includes("succes") || message.includes("enregistree") ? "success-text" : "error-text"}>{message}</p>}

      <div className="desktop-table-wrap academic-year-table-wrap">
        <div className="desktop-table-header academic-year-columns">
          <span>Annee</span>
          <span>Debut</span>
          <span>Fin</span>
          <span>Statut</span>
          <span>Actions</span>
        </div>
        <div className="desktop-table-body academic-year-rows">
          {yearOptions.map((year) => (
            <AcademicYearRow key={yearId(year)} year={year} currentActiveId={currentActiveId} canEdit={canEdit} onReload={onReload} />
          ))}
          {yearOptions.length === 0 && <p className="empty-cell">Aucune annee academique configuree.</p>}
        </div>
      </div>
    </div>
  );
}

function AcademicYearRow({ year, currentActiveId, canEdit, onReload }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const active = String(yearId(year)) === String(currentActiveId);

  async function activateYear() {
    setMessage("");
    setBusy(true);
    try {
      await apiRequest(`/api/finance/academic-years/${yearId(year)}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: true }),
      });
      setMessage("Annee active mise a jour.");
      onReload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="desktop-table-row academic-year-columns">
      <span>{yearName(year)}</span>
      <span>{dateField(year?.start_date) || "-"}</span>
      <span>{dateField(year?.end_date) || "-"}</span>
      <span className={`status-pill ${active ? "ok" : "warn"}`}>{active ? "Active" : "Inactive"}</span>
      <span className="academic-year-row-actions">
        {!active ? (
          <button className="small-save-button activate" type="button" disabled={!canEdit || busy} onClick={activateYear}>
            <CheckCircle2 size={16} /> Activer
          </button>
        ) : (
          <span className="muted-cell">Annee courante</span>
        )}
      </span>
      {message && <small className={message.includes("active") ? "success-text academic-year-row-message" : "error-text academic-year-row-message"}>{message}</small>}
    </div>
  );
}

function PromotionFinanceRow({ row, canEdit, onSave }) {
  const [fee, setFee] = useState(row.fee_usd || 0);
  const [threshold, setThreshold] = useState(row.threshold_amount || 0);

  return (
    <div className="desktop-table-row academic-columns">
      <span className="muted-cell">{row.faculty_name || "-"}</span>
      <span>{row.name || "-"}</span>
      <span className="muted-cell">{row.department_name || "-"}</span>
      <span>{row.year || "-"}</span>
      <input value={fee} disabled={!canEdit} onChange={(event) => setFee(event.target.value)} />
      <input value={threshold} disabled={!canEdit} onChange={(event) => setThreshold(event.target.value)} />
      <button className="small-save-button" disabled={!canEdit} onClick={() => onSave(row, fee, threshold)}>
        <Save size={16} /> Enregistrer
      </button>
    </div>
  );
}

function ExamPeriodsDialog({ years, onClose }) {
  const yearOptions = Array.isArray(years) ? years : [];
  const [selectedYear, setSelectedYear] = useState(() => String(yearId(yearOptions.find((year) => isActiveYear(year))) || yearId(yearOptions[0]) || ""));
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
      setMessage("Periode creee.");
      periods.reload();
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function deletePeriod(periodId) {
    setMessage("");
    try {
      await apiRequest(`/api/finance/exam-periods/${periodId}/`, { method: "DELETE" });
      setMessage("Periode supprimee.");
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
            <CalendarRange size={24} /> Gestion des Periodes d'Examens
          </h2>
          <p>Creez et organisez les sessions d'examen</p>
          <button type="button" className="dialog-close-button" aria-label="Fermer" title="Fermer" onClick={onClose}>
            <X size={24} />
          </button>
        </header>
        <div className="dialog-body">
          <label className="dialog-field">
            <span>Annee academique</span>
            <select value={selectedYear} onChange={(event) => setSelectedYear(event.target.value)}>
              {yearOptions.map((year) => (
                <option key={yearId(year)} value={yearId(year)}>
                  {yearName(year)}
                </option>
              ))}
            </select>
          </label>
          <form className="exam-period-form" onSubmit={addPeriod}>
            <input value={form.period_name} placeholder="Nom de la periode" onChange={(event) => setForm((current) => ({ ...current, period_name: event.target.value }))} />
            <input type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} />
            <input type="date" value={form.end_date} onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} />
            <button className="dialog-primary">Valider</button>
          </form>
          {message && <p className={message.includes("creee") || message.includes("supprimee") ? "success-text" : "error-text"}>{message}</p>}
          <AsyncState loading={periods.loading} error={periods.error}>
            <div className="period-list">
              {rows.map((period) => (
                <div className="period-row" key={period.exam_period_id || period.id}>
                  <span>
                    <strong>{period.period_name || period.name}</strong>
                    <small>
                      {period.start_date} - {period.end_date}
                    </small>
                  </span>
                  <button className="small-icon-button danger" title="Supprimer" onClick={() => deletePeriod(period.exam_period_id || period.id)}>
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
              {rows.length === 0 && <p className="empty-cell">Aucune periode enregistree.</p>}
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
  const activeYear = yearOptions.find((year) => isActiveYear(year)) || null;
  const sourceOptions = yearOptions.filter((year) => String(yearId(year)) !== String(yearId(activeYear)));
  const [fromYear, setFromYear] = useState(() => String(yearId(sourceOptions[0]) || yearId(yearOptions[0]) || ""));
  const [toYear, setToYear] = useState(() => String(yearId(activeYear) || yearId(yearOptions[0]) || ""));
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
      setResult(payload.data?.message || payload.message || "Copie traitee.");
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
            <Repeat size={24} /> Copie des etudiants vers une autre annee
          </h2>
          <p>Les dossiers de l'annee source restent en place; une nouvelle inscription est creee dans l'annee cible</p>
          <button type="button" className="dialog-close-button" aria-label="Fermer" title="Fermer" onClick={onClose} disabled={busy}>
            <X size={24} />
          </button>
        </header>
        <div className="dialog-body">
          <label className="dialog-field">
            <span>Annee source</span>
            <select value={fromYear} onChange={(event) => setFromYear(event.target.value)}>
              {(sourceOptions.length ? sourceOptions : yearOptions).map((year) => (
                <option key={yearId(year)} value={yearId(year)}>
                  {yearName(year)}
                </option>
              ))}
            </select>
          </label>
          <label className="dialog-field">
            <span>Annee destination</span>
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
            Etudiants eligibles seulement
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
              Copier
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

function dateField(value) {
  if (!value) return "";
  return String(value).slice(0, 10);
}

function isActiveYear(year) {
  return year?.is_active === true || year?.is_active === 1 || String(year?.is_active).toLowerCase() === "true";
}

function yearId(year) {
  return year?.academic_year_id || year?.id || "";
}

function yearName(year) {
  return year?.year_name || year?.name || `Annee ${yearId(year)}`;
}
