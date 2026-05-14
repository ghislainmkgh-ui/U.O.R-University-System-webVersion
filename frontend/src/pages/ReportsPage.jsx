import { ClipboardList, Download, FileDown, Landmark, ReceiptText, ShieldCheck, UsersRound } from "lucide-react";
import { useMemo, useState } from "react";

import { downloadApiFile } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { StudentPhoto } from "../components/StudentPhoto.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

const reports = [
  { key: "students", label: "Etudiants", icon: UsersRound },
  { key: "finance", label: "Finances", icon: Landmark },
  { key: "access", label: "Logs d'Acces", icon: ClipboardList },
];

export function ReportsPage() {
  const summary = useApiResource("/api/reports/summary/");
  const [activeReport, setActiveReport] = useState("students");
  const [studentStatus, setStudentStatus] = useState("all");
  const [accessStatus, setAccessStatus] = useState("ALL");
  const [limit, setLimit] = useState("200");
  const reportPath = useMemo(
    () => buildReportPath(activeReport, studentStatus, accessStatus, limit),
    [activeReport, studentStatus, accessStatus, limit],
  );
  const report = useApiResource(reportPath);
  const rows = activeReport === "access" ? report.data?.access_logs || [] : report.data?.students || [];

  return (
    <section className="page reports-page desktop-page">
      <PageHeader title="Rapports" subtitle="Exports et vues de controle" />

      <AsyncState loading={summary.loading} error={summary.error}>
        <div className="report-summary-grid">
          <ReportMetric icon={UsersRound} value={summary.data?.total_students || 0} label="Etudiants" tone="blue" />
          <ReportMetric icon={ShieldCheck} value={summary.data?.eligible_students || 0} label="Eligibles" tone="green" />
          <ReportMetric icon={ShieldCheck} value={summary.data?.non_eligible_students || 0} label="Non eligibles" tone="red" />
          <ReportMetric icon={ClipboardList} value={summary.data?.access_granted_today || 0} label="Acces accordes" tone="teal" />
          <ReportMetric icon={ReceiptText} value={formatMoney(summary.data?.revenue || 0)} label="Revenus" tone="gold" />
        </div>
      </AsyncState>

      <section className="surface reports-work-card">
        <div className="report-tabs">
          {reports.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.key} className={activeReport === item.key ? "active" : ""} onClick={() => setActiveReport(item.key)}>
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </div>

        <div className="report-toolbar">
          <div>
            <h2>{reports.find((item) => item.key === activeReport)?.label}</h2>
            <span>{rows.length} ligne(s) dans l'apercu</span>
          </div>

          {activeReport !== "access" ? (
            <label>
              Statut
              <select value={studentStatus} onChange={(event) => setStudentStatus(event.target.value)}>
                <option value="all">Tous</option>
                <option value="eligible">Eligibles</option>
                <option value="non_eligible">Non eligibles</option>
                <option value="paid">Avec paiement</option>
                <option value="never_paid">Non payes</option>
              </select>
            </label>
          ) : (
            <label>
              Resultat
              <select value={accessStatus} onChange={(event) => setAccessStatus(event.target.value)}>
                <option value="ALL">Tous</option>
                <option value="GRANTED">Accordes</option>
                <option value="DENIED">Refuses</option>
              </select>
            </label>
          )}

          {activeReport !== "students" && (
            <label>
              Limite
              <select value={limit} onChange={(event) => setLimit(event.target.value)}>
                <option value="100">100</option>
                <option value="200">200</option>
                <option value="500">500</option>
                <option value="1000">1000</option>
              </select>
            </label>
          )}

          <button className="primary-button" onClick={() => downloadApiFile(`${reportPath}${reportPath.includes("?") ? "&" : "?"}format=csv`, csvName(activeReport))}>
            <FileDown size={18} />
            Export CSV
          </button>
        </div>

        <AsyncState loading={report.loading} error={report.error}>
          {activeReport === "students" && <StudentsReportTable rows={rows} />}
          {activeReport === "finance" && <FinanceReportTable rows={rows} />}
          {activeReport === "access" && <AccessReportTable rows={rows} />}
        </AsyncState>
      </section>
    </section>
  );
}

function ReportMetric({ icon: Icon, value, label, tone }) {
  return (
    <div className={`surface report-metric ${tone}`}>
      <span>
        <Icon size={22} />
      </span>
      <strong>{value}</strong>
      <small>{label}</small>
    </div>
  );
}

function StudentsReportTable({ rows }) {
  return (
    <div className="desktop-table-wrap reports-table">
      <div className="desktop-table-header report-student-columns">
        <span>Photo</span>
        <span>Etudiant</span>
        <span>Matricule</span>
        <span>Faculte</span>
        <span>Promotion</span>
        <span>Paiement</span>
      </div>
      <div className="desktop-table-body">
        {rows.map((row) => (
          <div className="desktop-table-row report-student-columns" key={row.id || row.student_number}>
            <StudentPhoto student={row} />
            <span>{studentName(row)}</span>
            <span className="muted-cell">{row.student_number || "-"}</span>
            <span>{row.faculty_name || "-"}</span>
            <span>{row.promotion_name || "-"}</span>
            <span className={`status-pill ${row.is_eligible ? "ok" : Number(row.amount_paid || 0) > 0 ? "warn" : "bad"}`}>
              {row.is_eligible ? "Eligible" : Number(row.amount_paid || 0) > 0 ? "Partiel" : "Non paye"}
            </span>
          </div>
        ))}
        {!rows.length && <p className="empty-cell">Aucun etudiant dans ce rapport.</p>}
      </div>
    </div>
  );
}

function FinanceReportTable({ rows }) {
  return (
    <div className="desktop-table-wrap reports-table">
      <div className="desktop-table-header report-finance-columns">
        <span>Photo</span>
        <span>Etudiant</span>
        <span>Matricule</span>
        <span>Montant paye</span>
        <span>Seuil requis</span>
        <span>Frais promotion</span>
        <span>Statut</span>
      </div>
      <div className="desktop-table-body">
        {rows.map((row) => (
          <div className="desktop-table-row report-finance-columns" key={row.id || row.student_number}>
            <StudentPhoto student={row} />
            <span>{studentName(row)}</span>
            <span className="muted-cell">{row.student_number || "-"}</span>
            <strong className="success-text">{formatMoney(row.amount_paid || 0)}</strong>
            <span>{formatMoney(row.threshold_required || 0)}</span>
            <span>{formatMoney(row.promotion_fee || 0)}</span>
            <span className={`status-pill ${row.is_eligible ? "ok" : Number(row.amount_paid || 0) > 0 ? "warn" : "bad"}`}>
              {row.is_eligible ? "Eligible" : Number(row.amount_paid || 0) > 0 ? "Partiel" : "Non paye"}
            </span>
          </div>
        ))}
        {!rows.length && <p className="empty-cell">Aucune ligne finance dans ce rapport.</p>}
      </div>
    </div>
  );
}

function AccessReportTable({ rows }) {
  return (
    <div className="desktop-table-wrap reports-table">
      <div className="desktop-table-header report-access-columns">
        <span>Date</span>
        <span>Etudiant</span>
        <span>Matricule</span>
        <span>Point d'acces</span>
        <span>Resultat</span>
        <span>Mot de passe</span>
        <span>Visage</span>
        <span>Finance</span>
      </div>
      <div className="desktop-table-body">
        {rows.map((row, index) => (
          <div className="desktop-table-row report-access-columns" key={`${row.created_at}-${row.student_number}-${index}`}>
            <span>{formatDateTime(row.created_at)}</span>
            <span>{studentName(row)}</span>
            <span className="muted-cell">{row.student_number || "-"}</span>
            <span>{row.access_point || "-"}</span>
            <span className={`status-pill ${String(row.status || "").toUpperCase() === "GRANTED" ? "ok" : "bad"}`}>{row.status || "-"}</span>
            <span>{yesNo(row.password_validated)}</span>
            <span>{yesNo(row.face_validated)}</span>
            <span>{yesNo(row.finance_validated)}</span>
          </div>
        ))}
        {!rows.length && <p className="empty-cell">Aucun log dans ce rapport.</p>}
      </div>
    </div>
  );
}

function buildReportPath(activeReport, studentStatus, accessStatus, limit) {
  if (activeReport === "finance") {
    return `/api/reports/finance/?limit=${encodeURIComponent(limit)}&status=${encodeURIComponent(studentStatus)}`;
  }
  if (activeReport === "access") {
    return `/api/reports/access-logs/?limit=${encodeURIComponent(limit)}&status=${encodeURIComponent(accessStatus)}`;
  }
  return `/api/reports/students/?status=${encodeURIComponent(studentStatus)}`;
}

function csvName(activeReport) {
  return {
    students: "uor_students_report.csv",
    finance: "uor_finance_report.csv",
    access: "uor_access_logs_report.csv",
  }[activeReport];
}

function studentName(row) {
  return `${row?.firstname || ""} ${row?.lastname || ""}`.trim() || row?.student_name || "-";
}

function formatMoney(value) {
  return `$${Number(value || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function yesNo(value) {
  return value === true || value === 1 || value === "1" ? "Oui" : "Non";
}
