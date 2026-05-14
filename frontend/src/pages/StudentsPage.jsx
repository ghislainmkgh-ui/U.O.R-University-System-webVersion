import {
  CalendarDays,
  CheckSquare,
  ChevronRight,
  CircleDollarSign,
  CreditCard,
  Edit3,
  FileText,
  FolderOpen,
  GraduationCap,
  Landmark,
  Plus,
  Search,
  UsersRound,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

import { apiRequest } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { StudentPhoto } from "../components/StudentPhoto.jsx";
import { useApiResource } from "../hooks/useApiResource.js";
import { PaymentDialog, PaymentHistoryDialog } from "./FinancePage.jsx";

export function StudentsPage() {
  const { data, loading, error, reload } = useApiResource("/api/students/");
  const [yearId, setYearId] = useState("all");
  const [level, setLevel] = useState("faculty");
  const [selectedFaculty, setSelectedFaculty] = useState(null);
  const [selectedDepartment, setSelectedDepartment] = useState(null);
  const [query, setQuery] = useState("");
  const [modalMode, setModalMode] = useState("");
  const [editingStudent, setEditingStudent] = useState(null);
  const [paymentStudent, setPaymentStudent] = useState(null);
  const [historyStudent, setHistoryStudent] = useState(null);

  const rows = Array.isArray(data) ? data : [];
  const years = useMemo(() => academicYears(rows), [rows]);
  const filteredRows = useMemo(() => {
    if (yearId === "all") return rows;
    return rows.filter((row) => String(row.academic_year_id || "") === yearId);
  }, [rows, yearId]);
  const lookups = useMemo(() => buildLookups(rows), [rows]);

  const stats = useMemo(() => {
    const eligible = filteredRows.filter((row) => row.is_eligible).length;
    return { total: filteredRows.length, eligible, nonEligible: filteredRows.length - eligible };
  }, [filteredRows]);

  function resetToFaculty(nextYearId = yearId) {
    setYearId(nextYearId);
    setLevel("faculty");
    setSelectedFaculty(null);
    setSelectedDepartment(null);
    setQuery("");
  }

  return (
    <section className="page students-page desktop-page">
      <AsyncState loading={loading} error={error}>
        <div className="toolbar-line students-toolbar desktop-toolbar">
          <label>
            <CalendarDays size={18} />
            <span>Année académique:</span>
            <select value={yearId} onChange={(event) => resetToFaculty(event.target.value)}>
              <option value="all">Toutes Années</option>
              {years.map((year) => (
                <option key={year.id} value={year.id}>
                  {year.name}
                </option>
              ))}
            </select>
          </label>
          <span className="students-stats">
            Total: {stats.total} | <CheckSquare size={20} /> Éligibles: {stats.eligible} | <X size={23} /> Non-éligibles: {stats.nonEligible}
          </span>
          <button className="primary-button add-student-button" onClick={() => setModalMode("add")}>
            <Plus size={28} /> Ajouter Étudiant
          </button>
        </div>

        <div className="breadcrumb-line desktop-breadcrumb">
          <button className={level === "faculty" ? "active" : ""} onClick={() => resetToFaculty()}>
            <Landmark size={20} /> Facultés
          </button>
          {selectedFaculty && <ChevronRight className="breadcrumb-separator" size={20} />}
          {selectedFaculty && (
            <button
              className={level === "department" ? "active" : ""}
              onClick={() => {
                setLevel("department");
                setSelectedDepartment(null);
                setQuery("");
              }}
            >
              <FolderOpen size={20} />
              {selectedFaculty.name}
            </button>
          )}
          {selectedDepartment && <ChevronRight className="breadcrumb-separator" size={20} />}
          {selectedDepartment && (
            <button className="active">
              <FolderOpen size={20} />
              {selectedDepartment.name}
            </button>
          )}
        </div>

        <div className="surface hierarchy-card student-hierarchy-card">
          {level === "faculty" && (
            <FacultyView
              rows={filteredRows}
              onSelect={(faculty) => {
                setSelectedFaculty(faculty);
                setSelectedDepartment(null);
                setLevel("department");
              }}
            />
          )}
          {level === "department" && selectedFaculty && (
            <DepartmentView
              rows={filteredRows}
              faculty={selectedFaculty}
              onSelect={(department) => {
                setSelectedDepartment(department);
                setLevel("promotion");
              }}
            />
          )}
          {level === "promotion" && selectedDepartment && (
            <PromotionView
              rows={filteredRows}
              department={selectedDepartment}
              query={query}
              setQuery={setQuery}
              onEdit={(student) => {
                setEditingStudent(student);
                setModalMode("edit");
              }}
              onPay={setPaymentStudent}
              onHistory={setHistoryStudent}
            />
          )}
        </div>
      </AsyncState>

      {modalMode && (
        <StudentDialog
          mode={modalMode}
          student={editingStudent}
          lookups={lookups}
          onClose={() => {
            setModalMode("");
            setEditingStudent(null);
          }}
          onDone={() => {
            setModalMode("");
            setEditingStudent(null);
            reload();
          }}
        />
      )}
      {paymentStudent && (
        <PaymentDialog
          student={paymentStudent}
          onClose={() => setPaymentStudent(null)}
          onDone={() => {
            setPaymentStudent(null);
            reload();
          }}
        />
      )}
      {historyStudent && <PaymentHistoryDialog student={historyStudent} onClose={() => setHistoryStudent(null)} />}
    </section>
  );
}

function FacultyView({ rows, onSelect }) {
  const faculties = groupRows(rows, "faculty_id", (student) => ({
    id: student.faculty_id,
    name: student.faculty_name || "Faculté non définie",
    code: student.faculty_code || "-",
  }));

  return (
    <>
      <SectionHeading title="Sélectionnez une Faculté" subtitle="Cliquez sur une faculté pour voir ses départements." />
      <div className="entity-list">
        {faculties.map((faculty) => (
          <EntityCard key={faculty.id} item={faculty} icon={<Landmark size={28} />} onClick={() => onSelect(faculty)} />
        ))}
        {faculties.length === 0 && <p className="empty-cell">Aucune faculté trouvée.</p>}
      </div>
    </>
  );
}

function DepartmentView({ rows, faculty, onSelect }) {
  const departments = groupRows(
    rows.filter((student) => String(student.faculty_id || "unknown") === String(faculty.id)),
    "department_id",
    (student) => ({
      id: student.department_id,
      name: student.department_name || "Département non défini",
      code: student.department_code || "-",
    })
  );

  return (
    <>
      <SectionHeading title={`Départements de ${faculty.name}`} subtitle="Cliquez sur un département pour voir ses promotions." />
      <div className="entity-list">
        {departments.map((department) => (
          <EntityCard key={department.id} item={department} icon={<FolderOpen size={28} />} onClick={() => onSelect(department)} />
        ))}
        {departments.length === 0 && <p className="empty-cell">Aucun département trouvé.</p>}
      </div>
    </>
  );
}

function PromotionView({ rows, department, query, setQuery, onEdit, onPay, onHistory }) {
  const departmentRows = rows.filter((student) => String(student.department_id || "unknown") === String(department.id));
  const normalizedQuery = query.trim().toLowerCase();
  const promotions = groupRows(departmentRows, "promotion_id", (student) => ({
    id: student.promotion_id,
    name: student.promotion_name || "Promotion non définie",
    year: student.promotion_year || "-",
    fee: student.promotion_fee || 0,
    threshold: student.promotion_threshold || student.threshold_required || 0,
  }));

  return (
    <>
      <SectionHeading icon={<GraduationCap size={37} />} title={`Promotions - ${department.name}`} subtitle="Liste des étudiants par promotion" />
      <label className="search-line desktop-search">
        <Search size={18} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Rechercher un étudiant (nom, email...)..."
        />
      </label>

      <div className="promotion-list">
        {promotions.map((promotion) => {
          const students = promotion.students.filter((student) => {
            if (!normalizedQuery) return true;
            const haystack = `${student.firstname || ""} ${student.lastname || ""} ${student.email || ""} ${student.student_number || ""}`.toLowerCase();
            return haystack.includes(normalizedQuery);
          });
          if (students.length === 0) return null;
          return <PromotionTable key={promotion.id} promotion={promotion} rows={students} onEdit={onEdit} onPay={onPay} onHistory={onHistory} />;
        })}
        {promotions.length === 0 && <p className="empty-cell">Aucune promotion trouvée.</p>}
      </div>
    </>
  );
}

function PromotionTable({ promotion, rows, onEdit, onPay, onHistory }) {
  return (
    <article className="promotion-block desktop-promotion-block">
      <header>
        <strong>
          <GraduationCap size={18} /> {promotion.name} ({promotion.year})
        </strong>
        <span>
          <UsersRound size={18} /> {rows.length} étudiant{rows.length > 1 ? "s" : ""} | <CircleDollarSign size={18} /> Frais: {formatMoney(promotion.fee)} | Seuil: {formatMoney(promotion.threshold)}
        </span>
      </header>
      <div className="desktop-table-wrap">
        <div className="desktop-table-header student-columns">
          <span>Photo</span>
          <span>Nom Complet</span>
          <span>Email</span>
          <span className="header-with-icon"><CircleDollarSign size={18} /> Payé</span>
          <span>Éligibilité</span>
          <span>Solde ($)</span>
          <span>Actions</span>
        </div>
        <div className="desktop-table-body">
          {rows.map((row, index) => (
            <div className="desktop-table-row student-columns" key={`${row.student_number}-${index}`}>
              <StudentPhoto student={row} />
              <span>{`${row.firstname || ""} ${row.lastname || ""}`.trim() || "-"}</span>
              <span>{row.email || "-"}</span>
              <strong className="money-cell">{formatMoney(row.amount_paid || 0)}</strong>
              <span className={row.is_eligible ? "ok-mark" : "fail-mark"}>
                {row.is_eligible ? <CheckSquare size={24} /> : <X size={24} />}
              </span>
              <span>{formatMoney(Math.max(0, Number(row.promotion_fee || 0) - Number(row.amount_paid || 0)))}</span>
              <span className="row-actions">
                <button className="small-icon-button cyan" title="Modifier" onClick={() => onEdit(row)}>
                  <Edit3 size={16} />
                </button>
                <button className="small-icon-button blue" title="Paiement" onClick={() => onPay(row)}>
                  <CreditCard size={16} />
                </button>
                <button className="small-icon-button gold" title="Historique" onClick={() => onHistory(row)}>
                  <FileText size={16} />
                </button>
              </span>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}

function StudentDialog({ mode, student, lookups, onClose, onDone }) {
  const isEdit = mode === "edit";
  const [form, setForm] = useState(() => ({
    student_number: student?.student_number || "STU2026-001",
    firstname: student?.firstname || "Jean",
    lastname: student?.lastname || "Dupont",
    email: student?.email || "jean@uor.rw",
    phone_number: student?.phone_number || "+243123456789",
    academic_year_id: student?.academic_year_id || lookups.years[0]?.id || "",
    promotion_id: student?.promotion_id || lookups.promotions[0]?.id || "",
  }));
  const [photoFile, setPhotoFile] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (!form.promotion_id) {
      setError("Promotion obligatoire.");
      return;
    }
    if (!isEdit && !photoFile) {
      setError("Photo passeport obligatoire pour inscrire un etudiant.");
      return;
    }
    setBusy(true);
    try {
      const payload = { ...form, promotion_id: Number(form.promotion_id), academic_year_id: Number(form.academic_year_id) || null };
      if (photoFile) {
        payload.photo_base64 = await fileToDataUrl(photoFile);
        payload.photo_extension = extensionFromFile(photoFile.name);
      }
      await apiRequest(isEdit ? `/api/students/${student.id}/` : "/api/students/", {
        method: isEdit ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <form className="desktop-dialog student-dialog" onSubmit={submit}>
        <header className={`dialog-header ${isEdit ? "purple" : "blue"}`}>
          <h2>
            {isEdit ? <Edit3 size={30} /> : <Plus size={34} />} {isEdit ? "Modifier Etudiant" : "Nouvel Etudiant"}
          </h2>
          <p>{isEdit ? studentName(student) : "Remplissez tous les champs requis"}</p>
        </header>
        <div className="dialog-body student-dialog-body">
          <section>
            {!isEdit && <h3>Informations personnelles</h3>}
            <div className="form-grid">
              <DialogField label="Matricule etudiant *" value={form.student_number} onChange={(value) => update("student_number", value)} />
              <DialogField label="Prenom *" value={form.firstname} onChange={(value) => update("firstname", value)} />
              <DialogField label="Nom *" value={form.lastname} onChange={(value) => update("lastname", value)} />
              <DialogField label="Email *" value={form.email} onChange={(value) => update("email", value)} />
              <DialogField label="Telephone WhatsApp *" value={form.phone_number} onChange={(value) => update("phone_number", value)} wide />
            </div>
          </section>
          <section>
            {!isEdit && <h3>Informations academiques</h3>}
            <label className="dialog-field">
              <span>Annee academique *</span>
              <select value={form.academic_year_id} onChange={(event) => update("academic_year_id", event.target.value)}>
                {lookups.years.map((year) => (
                  <option key={year.id} value={year.id}>
                    {year.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="dialog-field">
              <span>Promotion *</span>
              <select value={form.promotion_id} onChange={(event) => update("promotion_id", event.target.value)}>
                {lookups.promotions.map((promotion) => (
                  <option key={promotion.id} value={promotion.id}>
                    {promotion.label}
                  </option>
                ))}
              </select>
            </label>
          </section>
          <section>
            <h3>Photo du visage (passeport){isEdit ? "" : " *"}</h3>
            <div className="file-row">
              <input value={photoFile?.name || ""} readOnly />
              <label>
                Parcourir
                <input type="file" accept="image/*" hidden onChange={(event) => setPhotoFile(event.target.files?.[0] || null)} />
              </label>
            </div>
            <span className="photo-hint">Fond neutre, visage centre, une seule personne, bonne lumiere.</span>
          </section>
          {error && <p className="error-text">{error}</p>}
          <div className="dialog-actions">
            <button type="button" className="dialog-secondary" onClick={onClose} disabled={busy}>
              Annuler
            </button>
            <button className="dialog-primary green" disabled={busy}>
              {isEdit ? "Enregistrer" : "Valider"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

function DialogField({ label, value, onChange, wide = false }) {
  return (
    <label className={`dialog-field ${wide ? "wide" : ""}`}>
      <span>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SectionHeading({ title, subtitle, icon }) {
  return (
    <div className="section-heading">
      <h2>
        {icon}
        {title}
      </h2>
      <p>{subtitle}</p>
    </div>
  );
}

function EntityCard({ item, icon, onClick }) {
  const eligible = item.students.filter((student) => student.is_eligible).length;
  return (
    <button className="entity-card" onClick={onClick}>
      <span className="entity-icon">{icon}</span>
      <span>
        <strong>{item.name}</strong>
        <small>Code: {item.code}</small>
      </span>
      <span className="entity-stats">
        <b>
          <UsersRound size={15} /> {item.students.length} étudiants
        </b>
        <b>{eligible} éligibles</b>
      </span>
    </button>
  );
}

function groupRows(rows, idKey, makeMeta) {
  const map = new Map();
  rows.forEach((student) => {
    const rawId = student[idKey] || "unknown";
    if (!map.has(rawId)) {
      map.set(rawId, { ...makeMeta(student), id: rawId, students: [] });
    }
    map.get(rawId).students.push(student);
  });
  return Array.from(map.values()).sort((a, b) => String(a.name).localeCompare(String(b.name)));
}

function academicYears(rows) {
  const map = new Map();
  rows.forEach((row) => {
    const id = row.academic_year_id;
    if (!id) return;
    map.set(String(id), row.academic_year_name || row.year_name || `Année ${id}`);
  });
  return Array.from(map, ([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
}

function buildLookups(rows) {
  const yearMap = new Map();
  const promoMap = new Map();
  rows.forEach((row) => {
    if (row.academic_year_id) {
      yearMap.set(String(row.academic_year_id), row.academic_year_name || row.year_name || `Année ${row.academic_year_id}`);
    }
    if (row.promotion_id) {
      promoMap.set(String(row.promotion_id), {
        id: row.promotion_id,
        label: `${row.promotion_name || "Promotion"}${row.promotion_year ? ` (${row.promotion_year})` : ""}`,
      });
    }
  });
  return {
    years: Array.from(yearMap, ([id, name]) => ({ id, name })),
    promotions: Array.from(promoMap.values()),
  };
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function extensionFromFile(name) {
  const match = String(name || "").match(/\.[^.]+$/);
  return match ? match[0] : ".jpg";
}

function studentName(row) {
  return `${row.firstname || ""} ${row.lastname || ""}`.trim() || "-";
}

function formatMoney(value) {
  return `$${Number(value || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
