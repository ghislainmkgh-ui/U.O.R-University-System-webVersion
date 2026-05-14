import {
  CheckSquare,
  CircleDollarSign,
  KeyRound,
  RefreshCw,
  ShieldCheck,
  UsersRound,
  Wifi,
} from "lucide-react";
import { Link } from "react-router-dom";

import { AsyncState } from "../components/AsyncState.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

const dateFormatter = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "long",
  year: "numeric",
});

export function DashboardPage() {
  const summary = useApiResource("/api/dashboard/summary/");
  const accessStatus = useApiResource("/api/access/status/");
  const data = summary.data || {};

  const totalStudents = Number(data.total_students || 0);
  const eligibleStudents = Number(data.eligible_students || 0);
  const nonEligibleStudents = Number(data.non_eligible_students || 0);
  const accessGranted = Number(data.access_granted || 0);
  const accessDenied = Number(data.access_denied || 0);
  const revenue = Number(data.revenue || 0);
  const completionRate = Math.round(Number(data.completion?.percentage || 0));
  const eligibilityRate = totalStudents > 0 ? Math.round((eligibleStudents / totalStudents) * 100) : 0;
  const paymentStatus = data.payment_status || {};

  const chartValues = [
    { label: "Etudiants", value: totalStudents, tone: "blue" },
    { label: "Eligibles", value: eligibleStudents, tone: "green" },
    { label: "Non-elig.", value: nonEligibleStudents, tone: "red" },
    { label: "Acces+", value: accessGranted, tone: "teal" },
    { label: "Acces-", value: accessDenied, tone: "orange" },
  ];

  return (
    <section className="dashboard-page">
      <header className="dashboard-hero">
        <div>
          <h1>Tableau de Bord</h1>
          <p>Vue d'ensemble - {dateFormatter.format(new Date())}</p>
        </div>
      </header>

      <AsyncState loading={summary.loading} error={summary.error}>
        <div className="dashboard-metrics">
          <MetricCard
            icon={UsersRound}
            tone="violet"
            value={totalStudents.toLocaleString("fr-FR")}
            label="Etudiants Inscrits"
            footnote={`${eligibilityRate}% eligibles`}
          />
          <MetricCard
            icon={CircleDollarSign}
            tone="amber"
            value={formatMoney(revenue)}
            label="Revenus Collectes"
            footnote="Frais academiques"
          />
          <MetricCard
            icon={CheckSquare}
            tone="green"
            value={eligibleStudents.toLocaleString("fr-FR")}
            label="Etudiants Eligibles"
            footnote={`sur ${totalStudents.toLocaleString("fr-FR")} inscrits`}
          />
          <MetricCard
            icon={KeyRound}
            tone="teal"
            value={accessGranted.toLocaleString("fr-FR")}
            label="Acces Accordes"
            footnote={`${accessGrantedPercent(accessGranted, totalStudents)}% du total`}
          />
        </div>

        <div className="dashboard-panels">
          <section className="dashboard-panel academics-panel">
            <PanelHeader title="Statistiques Academiques" eyebrow="Comparaison des indicateurs" to="/reports" />
            <div className="academic-grid">
              <div className="indicator-list">
                <Indicator label="Revenus Actuels" value={formatMoney(revenue)} />
                <Indicator label="Total Etudiants" value={totalStudents.toLocaleString("fr-FR")} />
                <Indicator label="Taux Eligibilite" value={`${eligibilityRate}%`} positive />
                <Indicator label="Profils Complets" value={`${completionRate}%`} positive={completionRate >= 50} />
              </div>
              <BarChart values={chartValues} />
            </div>
          </section>

          <section className="dashboard-panel distribution-panel">
            <PanelHeader title="Repartition Etudiants" eyebrow="Sources academiques" to="/students" />
            <div className="legend-row">
              <span>
                <i className="legend-dot green" /> Eligibles
              </span>
              <span>
                <i className="legend-dot red" /> Non-eligibles
              </span>
              <span>
                <i className="legend-dot amber" /> En cours
              </span>
            </div>
            <DonutChart
              percentage={eligibilityRate}
              eligible={eligibleStudents}
              nonEligible={nonEligibleStudents}
              pending={Math.max(0, totalStudents - eligibleStudents - nonEligibleStudents)}
            />
          </section>
        </div>

        <div className="dashboard-bottom-grid">
          <ActionStrip
            title="Journaux d'Acces"
            icon={ShieldCheck}
            tone="violet"
            text="Historique et tentatives d'acces aux examens."
            to="/access"
            action="Voir les logs"
          />
          <ActionStrip
            title="Resume Financier"
            icon={CircleDollarSign}
            tone="green"
            text={`${formatMoney(revenue)} collectes. ${Number(paymentStatus.eligible || 0)} paiements complets.`}
            progress={totalStudents ? eligibleStudents / totalStudents : 0}
            to="/finance"
            action="Voir finances"
          />
        </div>

        <div className="dashboard-lower-grid">
          <Esp32Card data={accessStatus.data} loading={accessStatus.loading} error={accessStatus.error} reload={accessStatus.reload} />
          <OperationsCard
            totalStudents={totalStudents}
            eligibleStudents={eligibleStudents}
            nonEligibleStudents={nonEligibleStudents}
            accessGranted={accessGranted}
            accessDenied={accessDenied}
            eligibilityRate={eligibilityRate}
          />
        </div>
      </AsyncState>
    </section>
  );
}

function MetricCard({ icon: Icon, tone, value, label, footnote }) {
  return (
    <article className="dashboard-card metric-card">
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
        <small>{footnote}</small>
      </div>
      <div className={`metric-icon ${tone}`}>
        <Icon size={32} strokeWidth={2.2} />
      </div>
    </article>
  );
}

function PanelHeader({ title, eyebrow, to }) {
  return (
    <div className="panel-header">
      <h2>{title}</h2>
      <span>{eyebrow}</span>
      <Link to={to}>VOIR RAPPORT</Link>
    </div>
  );
}

function Indicator({ label, value, positive = false }) {
  return (
    <div className="indicator">
      <span>{label}</span>
      <strong className={positive ? "positive" : ""}>{value}</strong>
    </div>
  );
}

function BarChart({ values }) {
  const maxValue = Math.max(...values.map((item) => item.value), 1);

  return (
    <div className="bar-chart" aria-label="Statistiques academiques">
      <div className="chart-grid-lines" />
      {values.map((item) => {
        const height = Math.max(2, Math.round((item.value / maxValue) * 100));
        return (
          <div className="bar-item" key={item.label}>
            <span className={`bar ${item.tone}`} style={{ height: `${height}%` }}>
              <b>{item.value.toLocaleString("fr-FR")}</b>
            </span>
            <small>{item.label}</small>
          </div>
        );
      })}
    </div>
  );
}

function DonutChart({ percentage, eligible, nonEligible, pending }) {
  const total = Math.max(eligible + nonEligible + pending, 1);
  const eligibleEnd = Math.round((eligible / total) * 100);
  const deniedEnd = Math.min(100, eligibleEnd + Math.round((nonEligible / total) * 100));

  return (
    <div className="donut-wrap">
      <div
        className="donut-chart"
        style={{ "--eligible": `${eligibleEnd}%`, "--denied": `${deniedEnd}%` }}
        aria-label={`${eligible} eligibles, ${nonEligible} non-eligibles, ${pending} en cours`}
      >
        <div className="donut-center">
          <strong>{percentage}%</strong>
          <span>Eligibilite</span>
        </div>
      </div>
    </div>
  );
}

function ActionStrip({ title, icon: Icon, tone, text, progress, to, action }) {
  return (
    <article className="dashboard-strip">
      <div>
        <h2>{title}</h2>
        <span>{text}</span>
        {typeof progress === "number" && (
          <div className="mini-progress" aria-hidden="true">
            <i style={{ width: `${Math.round(Math.max(0, Math.min(1, progress)) * 100)}%` }} />
          </div>
        )}
        <Link className="text-action" to={to}>
          {action}
        </Link>
      </div>
      <div className={`strip-icon ${tone}`}>
        <Icon size={30} />
      </div>
    </article>
  );
}

function Esp32Card({ data, loading, error, reload }) {
  const cameraOk = data?.camera === "ok";
  const statusText = loading ? "Verification..." : error ? error : `Statut: ${data?.status || "indisponible"}`;
  const cameraText = loading ? "Camera: verification" : `Camera: ${cameraOk ? "ok" : data?.camera || "indisponible"}`;

  return (
    <article className="dashboard-panel esp32-panel">
      <div className="panel-header compact">
        <h2>Communication ESP32 (Wi-Fi)</h2>
        <span>{statusText}</span>
        <button className="icon-button" onClick={reload} title="Rafraichir">
          <RefreshCw size={17} />
        </button>
      </div>
      <div className="esp32-body">
        <div className={`status-orb ${cameraOk ? "ok" : "warn"}`}>
          <Wifi size={26} />
        </div>
        <div>
          <strong>{cameraText}</strong>
          <p>
            L'etudiant envoie matricule, code d'acces et photo. Le serveur repond ACCES_OK, ERR_AUTH,
            ERR_FACE ou ERR_FINANCE.
          </p>
        </div>
      </div>
    </article>
  );
}

function OperationsCard({ totalStudents, eligibleStudents, nonEligibleStudents, accessGranted, accessDenied, eligibilityRate }) {
  const actions = [
    {
      icon: UsersRound,
      title: "Dossiers etudiants",
      detail: "Inscriptions, photos et promotions",
      value: totalStudents.toLocaleString("fr-FR"),
      to: "/students",
      tone: "blue",
    },
    {
      icon: CheckSquare,
      title: "Demandes d'acces",
      detail: "Validation par Super Admin",
      value: "A traiter",
      to: "/access-requests",
      tone: "green",
    },
    {
      icon: ShieldCheck,
      title: "Controle d'acces",
      detail: `${accessGranted.toLocaleString("fr-FR")} accordes, ${accessDenied.toLocaleString("fr-FR")} refuses`,
      value: "Logs",
      to: "/access",
      tone: "teal",
    },
  ];

  return (
    <article className="dashboard-panel operations-panel">
      <div className="panel-header compact">
        <h2>Centre de pilotage</h2>
        <span>Actions principales</span>
        <CheckSquare size={18} />
      </div>
      <div className="operations-summary">
        <span>
          <strong>{eligibilityRate}%</strong>
          Eligibilite
        </span>
        <span>
          <strong>{eligibleStudents.toLocaleString("fr-FR")}</strong>
          Eligibles
        </span>
        <span>
          <strong>{nonEligibleStudents.toLocaleString("fr-FR")}</strong>
          Non-eligibles
        </span>
      </div>
      <div className="ops-action-list">
        {actions.map((item) => {
          const Icon = item.icon;
          return (
            <Link className="ops-action-row" key={item.title} to={item.to}>
              <span className={`ops-action-icon ${item.tone}`}>
                <Icon size={18} />
              </span>
              <span className="ops-action-copy">
                <strong>{item.title}</strong>
                <small>{item.detail}</small>
              </span>
              <b>{item.value}</b>
            </Link>
          );
        })}
      </div>
    </article>
  );
}

function formatMoney(value) {
  return `$${Number(value || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function accessGrantedPercent(accessGranted, totalStudents) {
  if (!totalStudents) return 0;
  return Math.round((accessGranted / totalStudents) * 100);
}
