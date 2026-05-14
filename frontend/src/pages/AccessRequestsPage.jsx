import { CheckSquare, RefreshCw, Trash2, UserCheck, XSquare } from "lucide-react";
import { useState } from "react";

import { apiRequest } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

export function AccessRequestsPage() {
  const pending = useApiResource("/api/auth/access-requests/pending/");
  const admins = useApiResource("/api/auth/admins/");
  const pendingRows = Array.isArray(pending.data) ? pending.data : [];
  const adminRows = Array.isArray(admins.data) ? admins.data : [];
  const [activeTab, setActiveTab] = useState("pending");
  const [noteByRequest, setNoteByRequest] = useState({});
  const [actionError, setActionError] = useState("");
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState("");

  function reload() {
    pending.reload();
    admins.reload();
  }

  async function decide(row, action) {
    setActionError("");
    setMessage("");
    setBusyId(`${row.id}-${action}`);
    try {
      await apiRequest(`/api/auth/access-requests/${row.id}/${action}/`, {
        method: "POST",
        body: JSON.stringify({ note: noteByRequest[row.id] || "" }),
      });
      setMessage(action === "approve" ? "Demande approuvee." : "Demande rejetee.");
      reload();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusyId("");
    }
  }

  async function deleteAdmin(row) {
    setActionError("");
    setMessage("");
    setBusyId(`delete-${row.id}`);
    try {
      await apiRequest(`/api/auth/admins/${row.id}/`, { method: "DELETE" });
      setMessage("Administrateur supprime.");
      admins.reload();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="page access-requests-page desktop-page">
      <PageHeader title="Demandes d'acces" subtitle="Validation des comptes administrateurs">
        <button className="primary-button" onClick={reload}>
          <RefreshCw size={18} />
          Actualiser
        </button>
      </PageHeader>

      <section className="surface access-requests-card">
        <div className="report-tabs access-request-tabs">
          <button className={activeTab === "pending" ? "active" : ""} onClick={() => setActiveTab("pending")}>
            <CheckSquare size={18} />
            Demandes en attente
            <span className="tab-count">{pendingRows.length}</span>
          </button>
          <button className={activeTab === "admins" ? "active" : ""} onClick={() => setActiveTab("admins")}>
            <UserCheck size={18} />
            Administrateurs
            <span className="tab-count">{adminRows.length}</span>
          </button>
        </div>

        {message && <p className="success-text transfer-feedback">{message}</p>}
        {actionError && <p className="error-text transfer-feedback">{actionError}</p>}

        {activeTab === "pending" ? (
          <AsyncState loading={pending.loading} error={pending.error}>
            <div className="access-request-list">
              {pendingRows.map((row) => (
                <article className="access-request-card" key={row.id}>
                  <header>
                    <div>
                      <h3>{row.username || "-"}</h3>
                      <span>{row.email || "-"}</span>
                    </div>
                    <strong>EN ATTENTE</strong>
                  </header>
                  <p>Demande envoyee le {formatDate(row.requested_at || row.created_at)}</p>
                  <div className="transfer-request-actions">
                    <input
                      value={noteByRequest[row.id] || ""}
                      onChange={(event) => setNoteByRequest((state) => ({ ...state, [row.id]: event.target.value }))}
                      placeholder="Note de decision"
                    />
                    <button className="dialog-primary green" disabled={Boolean(busyId)} onClick={() => decide(row, "approve")}>
                      <CheckSquare size={16} />
                      Approuver
                    </button>
                    <button className="dialog-primary danger-button" disabled={Boolean(busyId)} onClick={() => decide(row, "reject")}>
                      <XSquare size={16} />
                      Rejeter
                    </button>
                  </div>
                </article>
              ))}
              {!pendingRows.length && (
                <div className="empty-panel-state">
                  <CheckSquare size={28} />
                  <strong>Aucune demande d'acces en attente</strong>
                  <span>Quand un nouvel utilisateur demande l'acces au logiciel, sa demande apparaitra ici.</span>
                </div>
              )}
            </div>
          </AsyncState>
        ) : (
          <AsyncState loading={admins.loading} error={admins.error}>
            <div className="desktop-table-wrap access-admin-table">
              <div className="desktop-table-header access-admin-columns">
                <span>ID</span>
                <span>Utilisateur</span>
                <span>Email</span>
                <span>Role</span>
                <span>Etat</span>
                <span>Action</span>
              </div>
              <div className="desktop-table-body">
                {adminRows.map((row) => (
                  <div className="desktop-table-row access-admin-columns" key={row.id}>
                    <span className="muted-cell">#{row.id}</span>
                    <strong>{row.username || "-"}</strong>
                    <span>{row.email || "-"}</span>
                    <span>{row.is_super_admin ? "Super admin" : "Admin"}</span>
                    <span className={`status-pill ${row.is_active === false ? "bad" : "ok"}`}>{row.is_active === false ? "Inactif" : "Actif"}</span>
                    <button className="small-icon-button danger" title="Supprimer" disabled={Boolean(busyId) || row.is_super_admin} onClick={() => deleteAdmin(row)}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
                {!adminRows.length && (
                  <div className="empty-panel-state">
                    <UserCheck size={28} />
                    <strong>Aucun administrateur approuve</strong>
                    <span>Les comptes valides par le Super Admin seront listes dans cet espace.</span>
                  </div>
                )}
              </div>
            </div>
          </AsyncState>
        )}
      </section>
    </section>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}
