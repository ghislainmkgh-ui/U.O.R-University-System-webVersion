import { CheckSquare, FileText, ShieldCheck, ShieldX } from "lucide-react";
import { useMemo, useState } from "react";

import { AsyncState } from "../components/AsyncState.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { StudentPhoto } from "../components/StudentPhoto.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

const filters = [
  { key: "all", label: "Tous les acces" },
  { key: "granted", label: "Acces accordes" },
  { key: "denied", label: "Acces refuses" },
];

export function AccessPage() {
  const logs = useApiResource("/api/access/logs/?limit=200");
  const [filter, setFilter] = useState("all");
  const rows = Array.isArray(logs.data) ? logs.data : [];

  const counts = useMemo(() => {
    const granted = rows.filter((row) => normalizeStatus(row.status).includes("granted")).length;
    return { granted, denied: rows.length - granted, total: rows.length };
  }, [rows]);

  const filteredRows = rows.filter((row) => {
    const normalized = normalizeStatus(row.status);
    if (filter === "granted") return normalized.includes("granted");
    if (filter === "denied") return !normalized.includes("granted");
    return true;
  });

  return (
    <section className="page access-page desktop-page">
      <PageHeader title="Historique d'Acces" subtitle="Suivi des tentatives d'acces" />

      <div className="page-section-heading">
        <FileText size={34} />
        <h2>Historique d'Acces</h2>
      </div>

      <div className="metric-grid access-filter-grid desktop-kpis">
        <AccessKpi tone="green" value={counts.granted} label="Acces Accordes" active={filter === "granted"} onClick={() => setFilter("granted")} />
        <AccessKpi tone="red" value={counts.denied} label="Acces Refuses" active={filter === "denied"} onClick={() => setFilter("denied")} />
        <AccessKpi tone="blue" value={counts.total} label="Total Tentatives" active={filter === "all"} onClick={() => setFilter("all")} />
      </div>

      <div className="surface table-section desktop-table-card">
        <div className="section-title-row vertical-title">
          <div>
            <h2>
              <FileText size={26} /> Detail des Tentatives d'Acces
            </h2>
            <span>Filtre actif : {filters.find((item) => item.key === filter)?.label}</span>
          </div>
          <button className="primary-button" onClick={logs.reload}>
            Actualiser
          </button>
        </div>
        <AsyncState loading={logs.loading} error={logs.error}>
          <DesktopAccessTable rows={filteredRows} />
        </AsyncState>
      </div>
    </section>
  );
}

function AccessKpi({ tone, value, label, active, onClick }) {
  return (
    <button className={`metric ${tone} ${active ? "active" : ""}`} onClick={onClick}>
      {tone === "red" ? <ShieldX size={24} /> : <ShieldCheck size={24} />}
      <strong>{value}</strong>
      <span>{label}</span>
    </button>
  );
}

function DesktopAccessTable({ rows }) {
  return (
    <div className="desktop-table-wrap">
      <div className="desktop-table-header access-columns">
        <span>Photo</span>
        <span>Etudiant</span>
        <span>ID</span>
        <span>Point d'Acces</span>
        <span>Resultat</span>
        <span>Mot de passe</span>
        <span>Visage</span>
        <span>Finance</span>
        <span>Heure</span>
      </div>
      <div className="desktop-table-body">
        {rows.map((row, index) => (
          <div className="desktop-table-row access-columns" key={`${row.student_number}-${row.created_at}-${index}`}>
            <StudentPhoto student={row} />
            <span>{studentName(row)}</span>
            <span className="muted-cell">{row.student_number || "-"}</span>
            <span>{row.access_point || "-"}</span>
            <span className={normalizeStatus(row.status).includes("granted") ? "ok-mark" : "fail-mark"}>
              <CheckSquare size={18} />
            </span>
            <span className="ok-mark">{truthy(row.password_validated) ? "✓" : "×"}</span>
            <span className={truthy(row.face_validated) ? "ok-mark" : "fail-mark"}>{truthy(row.face_validated) ? "✓" : "×"}</span>
            <span className={truthy(row.finance_validated) ? "ok-mark" : "fail-mark"}>{truthy(row.finance_validated) ? "✓" : "×"}</span>
            <span>{formatTime(row.created_at)}</span>
          </div>
        ))}
        {rows.length === 0 && <p className="empty-cell">Aucune tentative trouvee.</p>}
      </div>
    </div>
  );
}

function normalizeStatus(value) {
  return String(value || "").toLowerCase();
}

function truthy(value) {
  return value === true || value === 1 || value === "1";
}

function studentName(row) {
  return row.student_name || `${row.firstname || ""} ${row.lastname || ""}`.trim() || "-";
}

function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}
