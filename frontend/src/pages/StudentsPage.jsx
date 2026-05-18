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
import { useEffect, useMemo, useState } from "react";

import { apiRequest } from "../api/client.js";
import { AsyncState } from "../components/AsyncState.jsx";
import { StudentPhoto } from "../components/StudentPhoto.jsx";
import { useApiResource } from "../hooks/useApiResource.js";
import { PaymentDialog, PaymentHistoryDialog } from "./FinancePage.jsx";

export function StudentsPage() {
  const { data, loading, error, reload } = useApiResource("/api/students/");
  const promotionsResource = useApiResource("/api/students/promotions/");
  const yearsResource = useApiResource("/api/finance/academic-years/");
  const [yearId, setYearId] = useState("active");
  const [level, setLevel] = useState("faculty");
  const [selectedFaculty, setSelectedFaculty] = useState(null);
  const [selectedDepartment, setSelectedDepartment] = useState(null);
  const [query, setQuery] = useState("");
  const [modalMode, setModalMode] = useState("");
  const [editingStudent, setEditingStudent] = useState(null);
  const [paymentStudent, setPaymentStudent] = useState(null);
  const [historyStudent, setHistoryStudent] = useState(null);
  const [notice, setNotice] = useState("");

  const rows = Array.isArray(data) ? data : [];
  const years = useMemo(() => academicYears(rows, yearsResource.data), [rows, yearsResource.data]);
  const activeYear = useMemo(() => years.find((year) => year.is_active) || null, [years]);
  const activeYearId = activeYear ? String(activeYear.id) : "";
  const filteredRows = useMemo(() => {
    if (yearId === "all") return rows;
    const currentYearId = yearId === "active" ? activeYearId : yearId;
    if (!currentYearId) return [];
    return rows.filter((row) => String(row.academic_year_id || "") === currentYearId);
  }, [rows, yearId, activeYearId]);
  const lookups = useMemo(
    () => buildStudentLookups(rows, promotionsResource.data, yearsResource.data),
    [rows, promotionsResource.data, yearsResource.data],
  );

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
      <AsyncState loading={loading || promotionsResource.loading || yearsResource.loading} error={error || promotionsResource.error || yearsResource.error}>
        <div className="toolbar-line students-toolbar desktop-toolbar">
          <label>
            <CalendarDays size={18} />
            <span>Année académique:</span>
            <select value={yearId} onChange={(event) => resetToFaculty(event.target.value)}>
              <option value="active">Annee active{activeYear ? ` - ${activeYear.name}` : ""}</option>
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
          <button
            className="primary-button add-student-button"
            onClick={() => {
              setNotice("");
              setModalMode("add");
            }}
          >
            <Plus size={28} /> Ajouter Étudiant
          </button>
        </div>

        {notice && <p className="success-text student-success-message">{notice}</p>}

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
          onDone={(message) => {
            setModalMode("");
            setEditingStudent(null);
            setNotice(message || (modalMode === "edit" ? "Etudiant modifie avec succes." : "Etudiant ajoute avec succes."));
            reload();
            promotionsResource.reload();
            yearsResource.reload();
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
            const haystack = `${studentName(student)} ${student.email || ""} ${student.student_number || ""}`.toLowerCase();
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
              <span>{studentName(row)}</span>
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
  const initialIdentity = identityFromStudent(student);
  const hierarchy = lookups.hierarchy;
  const activeYear = lookups.years.find((year) => year.is_active) || lookups.years[0] || null;
  const initialFacultyId = student?.faculty_id || hierarchy[0]?.id || "";
  const initialDepartmentId =
    student?.department_id ||
    hierarchy.find((faculty) => String(faculty.id) === String(initialFacultyId))?.departments[0]?.id ||
    "";
  const initialPromotionId =
    student?.promotion_id ||
    hierarchy
      .find((faculty) => String(faculty.id) === String(initialFacultyId))
      ?.departments.find((department) => String(department.id) === String(initialDepartmentId))
      ?.promotions[0]?.id ||
    lookups.promotions[0]?.id ||
    "";
  const [form, setForm] = useState(() => ({
    student_number: student?.student_number || "",
    nom: initialIdentity.nom,
    postnom: initialIdentity.postnom,
    prenom: initialIdentity.prenom,
    email: student?.email || "",
    phone_number: student?.phone_number || "",
    academic_year_id: student?.academic_year_id || activeYear?.id || "",
    faculty_id: initialFacultyId,
    department_id: initialDepartmentId,
    promotion_id: initialPromotionId,
    new_faculty_name: "",
    new_faculty_code: "",
    new_department_name: "",
    new_department_code: "",
    new_promotion_name: "",
    new_promotion_year: new Date().getFullYear(),
  }));
  const [createAcademic, setCreateAcademic] = useState({ faculty: false, department: false, promotion: false });
  const [photoFile, setPhotoFile] = useState(null);
  const [photoStatus, setPhotoStatus] = useState("idle");
  const [photoMessage, setPhotoMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const selectedFaculty = hierarchy.find((faculty) => String(faculty.id) === String(form.faculty_id));
  const departments = selectedFaculty?.departments || [];
  const selectedDepartment = departments.find((department) => String(department.id) === String(form.department_id));
  const promotions = selectedDepartment?.promotions || [];

  useEffect(() => {
    if (isEdit || !activeYear?.id) return;
    setForm((current) => ({ ...current, academic_year_id: activeYear.id }));
  }, [activeYear?.id, isEdit]);

  useEffect(() => {
    if (!hierarchy.length) return;
    setForm((current) => {
      const faculty = hierarchy.find((item) => String(item.id) === String(current.faculty_id)) || hierarchy[0];
      const department = faculty.departments.find((item) => String(item.id) === String(current.department_id)) || faculty.departments[0];
      const promotion = department?.promotions.find((item) => String(item.id) === String(current.promotion_id)) || department?.promotions[0];
      return {
        ...current,
        faculty_id: faculty?.id || "",
        department_id: department?.id || "",
        promotion_id: promotion?.id || "",
      };
    });
  }, [hierarchy]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function toggleAcademicCreation(levelName, checked) {
    setCreateAcademic((current) => {
      if (levelName === "faculty") {
        return checked
          ? { faculty: true, department: true, promotion: true }
          : { faculty: false, department: false, promotion: false };
      }
      if (levelName === "department") {
        return checked
          ? { ...current, department: true, promotion: true }
          : { ...current, department: false, promotion: false };
      }
      return { ...current, promotion: checked };
    });
  }

  function chooseFaculty(value) {
    const faculty = hierarchy.find((item) => String(item.id) === String(value));
    const department = faculty?.departments[0];
    const promotion = department?.promotions[0];
    setForm((current) => ({
      ...current,
      faculty_id: faculty?.id || "",
      department_id: department?.id || "",
      promotion_id: promotion?.id || "",
    }));
  }

  function chooseDepartment(value) {
    const department = departments.find((item) => String(item.id) === String(value));
    const promotion = department?.promotions[0];
    setForm((current) => ({
      ...current,
      department_id: department?.id || "",
      promotion_id: promotion?.id || "",
    }));
  }

  async function choosePhoto(file) {
    setPhotoFile(file || null);
    setPhotoStatus(file ? "checking" : "idle");
    setPhotoMessage(file ? "Verification de la photo en cours..." : "");
    setError("");
    if (!file) return;
    try {
      const photo_base64 = await fileToDataUrl(file);
      const payload = await apiRequest("/api/students/validate-photo/", {
        method: "POST",
        body: JSON.stringify({
          photo_base64,
          photo_extension: extensionFromFile(file.name),
        }),
      });
      setPhotoStatus("valid");
      setPhotoMessage(payload.data?.message || "Photo valide pour la reconnaissance faciale.");
    } catch (err) {
      setPhotoStatus("invalid");
      setPhotoMessage(err.message);
    }
  }

  async function ensureAcademicStructure() {
    let facultyId = form.faculty_id;
    let departmentId = form.department_id;
    let promotionId = form.promotion_id;

    if (createAcademic.faculty) {
      const name = form.new_faculty_name.trim();
      if (!name) throw new Error("Veuillez entrer le nom de la nouvelle faculte.");
      const payload = await apiRequest("/api/students/faculties/", {
        method: "POST",
        body: JSON.stringify({ name, code: form.new_faculty_code.trim() || undefined }),
      });
      facultyId = payload.data?.id;
    }

    if (createAcademic.department) {
      const name = form.new_department_name.trim();
      if (!name) throw new Error("Veuillez entrer le nom du nouveau departement.");
      if (!facultyId) throw new Error("Veuillez choisir ou creer une faculte avant le departement.");
      const payload = await apiRequest("/api/students/departments/", {
        method: "POST",
        body: JSON.stringify({
          name,
          code: form.new_department_code.trim() || undefined,
          faculty_id: Number(facultyId),
        }),
      });
      departmentId = payload.data?.id;
    }

    if (createAcademic.promotion) {
      const name = form.new_promotion_name.trim();
      if (!name) throw new Error("Veuillez entrer le nom de la nouvelle promotion.");
      if (!departmentId) throw new Error("Veuillez choisir ou creer un departement avant la promotion.");
      const payload = await apiRequest("/api/students/promotions/", {
        method: "POST",
        body: JSON.stringify({
          name,
          year: Number(form.new_promotion_year) || new Date().getFullYear(),
          department_id: Number(departmentId),
        }),
      });
      promotionId = payload.data?.id;
    }

    if (!promotionId) {
      throw new Error("Promotion obligatoire.");
    }
    return Number(promotionId);
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (!form.nom.trim() || !form.postnom.trim() || !form.prenom.trim()) {
      setError("Nom, postnom et prenom sont obligatoires.");
      return;
    }
    if (!createAcademic.promotion && !form.promotion_id) {
      setError("Promotion obligatoire.");
      return;
    }
    if (!isEdit && !activeYear?.id) {
      setError("Configurez d'abord une annee academique active.");
      return;
    }
    if (!isEdit && !photoFile) {
      setError("Photo passeport obligatoire pour inscrire un etudiant.");
      return;
    }
    if (photoFile && photoStatus !== "valid") {
      setError("La photo doit etre validee avant l'enregistrement.");
      return;
    }
    setBusy(true);
    try {
      const promotionId = await ensureAcademicStructure();
      const payload = {
        student_number: form.student_number.trim(),
        nom: form.nom.trim(),
        postnom: form.postnom.trim(),
        prenom: form.prenom.trim(),
        lastname: form.nom.trim(),
        firstname: form.prenom.trim(),
        email: form.email.trim(),
        phone_number: form.phone_number.trim(),
        promotion_id: promotionId,
        academic_year_id: Number(isEdit ? form.academic_year_id : activeYear?.id) || null,
      };
      if (photoFile) {
        payload.photo_base64 = await fileToDataUrl(photoFile);
        payload.photo_extension = extensionFromFile(photoFile.name);
      }
      await apiRequest(isEdit ? `/api/students/${student.id}/` : "/api/students/", {
        method: isEdit ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      onDone(isEdit ? "Etudiant modifie avec succes." : "Etudiant ajoute avec succes.");
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
          <button type="button" className="dialog-close-button" aria-label="Fermer" title="Fermer" onClick={onClose} disabled={busy}>
            <X size={24} />
          </button>
        </header>
        <div className="dialog-body student-dialog-body">
          <section>
            {!isEdit && <h3>Informations personnelles</h3>}
            <div className="form-grid">
              <DialogField label="Matricule etudiant *" value={form.student_number} placeholder="Ex: STU2026-001" onChange={(value) => update("student_number", value)} />
              <DialogField label="Nom *" value={form.nom} placeholder="Ex: MABIKA" onChange={(value) => update("nom", value)} />
              <DialogField label="Postnom *" value={form.postnom} placeholder="Ex: KALALA" onChange={(value) => update("postnom", value)} />
              <DialogField label="Prenom *" value={form.prenom} placeholder="Ex: Gloria" onChange={(value) => update("prenom", value)} />
              <DialogField label="Email *" value={form.email} placeholder="Ex: etudiant@uor.cd" onChange={(value) => update("email", value)} />
              <DialogField label="Telephone WhatsApp *" value={form.phone_number} placeholder="Ex: +243..." onChange={(value) => update("phone_number", value)} wide />
            </div>
          </section>
          <section>
            {!isEdit && <h3>Informations academiques</h3>}
            <label className="dialog-field">
              <span>Annee academique *</span>
              <select value={form.academic_year_id} disabled={!isEdit} onChange={(event) => update("academic_year_id", event.target.value)}>
                {(isEdit ? lookups.years : activeYear ? [activeYear] : []).map((year) => (
                  <option key={year.id} value={year.id}>
                    {year.name}{year.is_active ? " (active)" : ""}
                  </option>
                ))}
                {!activeYear && !isEdit && <option value="">Aucune annee active</option>}
              </select>
            </label>
            <div className="dialog-field">
              <span>Faculte *</span>
              <label className="inline-create-check">
                <input type="checkbox" checked={createAcademic.faculty} onChange={(event) => toggleAcademicCreation("faculty", event.target.checked)} />
                Nouvelle faculte
              </label>
              {createAcademic.faculty ? (
                <div className="form-two-columns compact">
                  <input value={form.new_faculty_name} placeholder="Nom de la faculte" onChange={(event) => update("new_faculty_name", event.target.value)} />
                  <input value={form.new_faculty_code} placeholder="Faculte en sigle" onChange={(event) => update("new_faculty_code", event.target.value)} />
                </div>
              ) : (
                <select value={form.faculty_id} onChange={(event) => chooseFaculty(event.target.value)}>
                  {hierarchy.map((faculty) => (
                    <option key={faculty.id} value={faculty.id}>
                      {faculty.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="dialog-field">
              <span>Departement *</span>
              <label className="inline-create-check">
                <input
                  type="checkbox"
                  checked={createAcademic.department}
                  disabled={createAcademic.faculty}
                  onChange={(event) => toggleAcademicCreation("department", event.target.checked)}
                />
                Nouveau departement
              </label>
              {createAcademic.department ? (
                <div className="form-two-columns compact">
                  <input value={form.new_department_name} placeholder="Nom du departement" onChange={(event) => update("new_department_name", event.target.value)} />
                  <input value={form.new_department_code} placeholder="Departement en sigle" onChange={(event) => update("new_department_code", event.target.value)} />
                </div>
              ) : (
                <select value={form.department_id} onChange={(event) => chooseDepartment(event.target.value)} disabled={!departments.length}>
                  {departments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="dialog-field">
              <span>Promotion *</span>
              <label className="inline-create-check">
                <input
                  type="checkbox"
                  checked={createAcademic.promotion}
                  disabled={createAcademic.department}
                  onChange={(event) => toggleAcademicCreation("promotion", event.target.checked)}
                />
                Nouvelle promotion
              </label>
              {createAcademic.promotion ? (
                <div className="form-two-columns compact">
                  <input value={form.new_promotion_name} placeholder="Ex: L1 LMD/G.I" onChange={(event) => update("new_promotion_name", event.target.value)} />
                  <input value={form.new_promotion_year} placeholder="Annee" onChange={(event) => update("new_promotion_year", event.target.value)} />
                </div>
              ) : (
                <select value={form.promotion_id} onChange={(event) => update("promotion_id", event.target.value)} disabled={!promotions.length}>
                  {promotions.map((promotion) => (
                    <option key={promotion.id} value={promotion.id}>
                      {promotion.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <span className="photo-hint">
              Toute nouvelle promotion creee ici apparaitra dans Annees Academiques pour definir les frais et le seuil.
            </span>
          </section>
          <section>
            <h3>Photo du visage (passeport){isEdit ? "" : " *"}</h3>
            <div className="file-row">
              <input value={photoFile?.name || ""} readOnly />
              <label>
                Parcourir
                <input type="file" accept="image/*" hidden onChange={(event) => choosePhoto(event.target.files?.[0] || null)} />
              </label>
            </div>
            {photoMessage && <span className={`photo-validation ${photoStatus}`}>{photoMessage}</span>}
            <span className="photo-hint">Fond neutre, visage centre, une seule personne, bonne lumiere.</span>
          </section>
          {error && <p className="error-text">{error}</p>}
          <div className="dialog-actions">
            <button type="button" className="dialog-secondary" onClick={onClose} disabled={busy}>
              Annuler
            </button>
            <button className="dialog-primary green" disabled={busy || photoStatus === "checking"}>
              {isEdit ? "Enregistrer" : "Valider"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

function DialogField({ label, value, placeholder, onChange, wide = false }) {
  return (
    <label className={`dialog-field ${wide ? "wide" : ""}`}>
      <span>{label}</span>
      <input value={value} placeholder={placeholder || ""} onChange={(event) => onChange(event.target.value)} />
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

function academicYears(rows, yearRows = []) {
  const map = new Map();
  rows.forEach((row) => {
    const id = row.academic_year_id;
    if (!id) return;
    map.set(String(id), row.academic_year_name || row.year_name || `Année ${id}`);
  });
  (Array.isArray(yearRows) ? yearRows : []).forEach((year) => {
    const id = year.academic_year_id || year.id;
    if (!id) return;
    map.set(String(id), {
      id,
      name: year.year_name || year.name || `Annee ${id}`,
      is_active: isActiveYear(year),
    });
  });
  return Array.from(map, ([id, value]) =>
    typeof value === "object" ? value : { id, name: value, is_active: false },
  ).sort((a, b) => Number(b.is_active) - Number(a.is_active) || a.name.localeCompare(b.name, "fr"));
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

function buildStudentLookups(rows, promotionRows = [], yearRows = []) {
  const yearMap = new Map();
  const promoMap = new Map();
  const facultyMap = new Map();
  const allPromotions = [
    ...(Array.isArray(promotionRows) ? promotionRows : []),
    ...rows.filter((row) => row.promotion_id),
  ];

  function addPromotion(row) {
    const promotionId = row.promotion_id || row.id;
    if (!promotionId) return;
    const facultyId = row.faculty_id || `faculty:${row.faculty_name || "unknown"}`;
    const departmentId = row.department_id || `department:${facultyId}:${row.department_name || "unknown"}`;
    if (!facultyMap.has(String(facultyId))) {
      facultyMap.set(String(facultyId), {
        id: facultyId,
        name: row.faculty_name || "Faculte non definie",
        departments: new Map(),
      });
    }
    const faculty = facultyMap.get(String(facultyId));
    if (!faculty.departments.has(String(departmentId))) {
      faculty.departments.set(String(departmentId), {
        id: departmentId,
        name: row.department_name || "Departement non defini",
        promotions: new Map(),
      });
    }
    const department = faculty.departments.get(String(departmentId));
    department.promotions.set(String(promotionId), {
      id: promotionId,
      name: `${row.promotion_name || row.name || "Promotion"}${row.promotion_year || row.year ? ` (${row.promotion_year || row.year})` : ""}`,
    });
    promoMap.set(String(promotionId), {
      id: promotionId,
      label: `${row.faculty_name || "Faculte"} / ${row.department_name || "Departement"} / ${row.promotion_name || row.name || "Promotion"}`,
    });
  }

  allPromotions.forEach(addPromotion);
  rows.forEach((row) => {
    if (row.academic_year_id) {
      yearMap.set(String(row.academic_year_id), {
        id: row.academic_year_id,
        name: row.academic_year_name || row.year_name || `Annee ${row.academic_year_id}`,
        is_active: row.academic_year_is_active === true || row.academic_year_is_active === 1,
      });
    }
  });
  (Array.isArray(yearRows) ? yearRows : []).forEach((year) => {
    const id = year.academic_year_id || year.id;
    if (id) {
      yearMap.set(String(id), {
        id,
        name: year.year_name || year.name || `Annee ${id}`,
        is_active: isActiveYear(year),
      });
    }
  });

  return {
    years: Array.from(yearMap.values()).sort((a, b) => Number(b.is_active) - Number(a.is_active) || a.name.localeCompare(b.name, "fr")),
    promotions: Array.from(promoMap.values()),
    hierarchy: Array.from(facultyMap.values())
      .map((faculty) => ({
        ...faculty,
        departments: Array.from(faculty.departments.values())
          .map((department) => ({
            ...department,
            promotions: Array.from(department.promotions.values()).sort((a, b) => a.name.localeCompare(b.name, "fr")),
          }))
          .sort((a, b) => a.name.localeCompare(b.name, "fr")),
      }))
      .sort((a, b) => a.name.localeCompare(b.name, "fr")),
  };
}

function isActiveYear(year) {
  return year?.is_active === true || year?.is_active === 1 || String(year?.is_active).toLowerCase() === "true";
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
  const identity = identityFromStudent(row);
  return [identity.nom, identity.postnom, identity.prenom].filter(Boolean).join(" ") || row?.student_name || "-";
}

function identityFromStudent(row) {
  const lastname = String(row?.nom || row?.lastname || "").trim();
  const postnom = row?.postnom;
  if (postnom === undefined || postnom === null) {
    const parts = lastname.split(/\s+/).filter(Boolean);
    return {
      nom: parts[0] || "",
      postnom: parts.slice(1).join(" "),
      prenom: String(row?.prenom || row?.firstname || "").trim(),
    };
  }
  return {
    nom: lastname,
    postnom: String(postnom || "").trim(),
    prenom: String(row?.prenom || row?.firstname || "").trim(),
  };
}

function formatMoney(value) {
  return `$${Number(value || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
