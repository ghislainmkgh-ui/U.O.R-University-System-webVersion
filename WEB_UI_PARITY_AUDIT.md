# Audit de parite UI desktop -> web

Date: 2026-05-11

Objectif: reproduire l'application desktop dans `Web_app_migration/frontend`
sans perdre les parcours utilisateur, les validations et la logique metier deja
presentes dans `ui/screens/admin/admin_dashboard.py`.

## Structure desktop observee

- `main.py` demarre l'app CustomTkinter, ouvre `LoginScreen`, puis `AdminDashboard`.
- `AppWrapper` persiste `language`, `theme`, `last_view`, identifiant memorise et etat login.
- `AdminDashboard` pilote une navigation interne par `current_view`, pas par fichiers separes.
- Le dashboard instancie les services metier existants:
  - `DashboardService`
  - `StudentService`
  - `AuthenticationService`
  - `FinanceService`
  - `AcademicYearService`
  - `NotificationService`
  - `ESP32StatusService`
  - `TransferService`
  - `FaceRecognitionService` en initialisation lazy
- Les vues desktop utilisent du cache UI, des chargements avec overlay, des rendus par lots et des dialogues de validation.

## Correspondance des vues

| Vue desktop | Vue web actuelle | Etat | Logique a conserver |
| --- | --- | --- | --- |
| Login | `LoginPage.jsx` | Partiel | Remember me, reset password, request access, creation compte admin, langue, login social si garde. |
| Dashboard | `DashboardPage.jsx` | Avance | KPIs, charts, resume finance, logs, statut ESP32/camera, activites recentes. |
| Etudiants | `StudentsPage.jsx` | Structure portee | Navigation annee -> faculte -> departement -> promotion, recherche, stats. Reste: ajout, edition, photo/face, paiement depuis dossier. |
| Demandes d'acces | `AccessRequestsPage.jsx` | Base portee | Liste pending, approbation, rejet via endpoints super-admin. Reste: admins approuves/suppression. |
| Donnees academiques | `AcademicsPage.jsx` | Minimal | Selection etudiant, onglets notes/documents, CRUD notes, upload/download documents, generation code cours. |
| Finances | `FinancePage.jsx` | Structure portee | KPIs filtrants, tableau paiements. Reste: dialogue paiement, historique par etudiant, generation/affichage code acces. |
| Annees academiques | `AcademicYearsPage.jsx` | Minimal | Seuils/frais, promotions financials, periodes d'examen, migration annuelle, audit migration, notifications. |
| Transferts | `TransfersPage.jsx` | Minimal | Onglets sortants/entrants/historique, cascade faculte/departement/promotion/etudiant, URL API partenaire, approve/reject, livraison API partenaire. |
| Logs d'acces | `AccessPage.jsx` | Avance | Statut service/camera, compteurs, filtres accordes/refuses, table logs. Reste: verification code manuelle si souhaitee. |
| Rapports | `ReportsPage.jsx` | Base | Resume + CSV. Reste: filtres equivalence desktop, export PDF/Excel si requis. |

## Points de communication critiques

- Les pages web doivent toujours passer par les APIs Django, pas lire la base directement.
- Les APIs Django reutilisent les services desktop via `apps.common.legacy.services()`.
- Les mutations doivent invalider ou recharger les donnees concernees:
  - creation/edition etudiant -> dashboard, etudiants, finances, annees academiques;
  - paiement -> dashboard, finances, etudiants, code acces;
  - seuils/frais -> finances, etudiants, notifications;
  - transfert -> transferts, etudiants, donnees academiques;
  - demande acces -> demandes acces, admins approuves.
- Les operations camera/face/ESP32 doivent rester cote backend/service; le frontend ne doit afficher que l'etat et declencher les endpoints.

## Priorites de portage recommandees

1. Finaliser `StudentsPage`: ajout/edition avec photo base64, validation, creation faculte/departement/promotion si manquant.
2. Finaliser `FinancePage`: paiement, historique, code d'acces, refresh dashboard.
3. Finaliser `AcademicsPage`: selection etudiant + onglets notes/documents.
4. Finaliser `TransfersPage`: onglets desktop et actions approve/reject/generate.
5. Finaliser `AcademicYearsPage`: seuils, periodes d'examen, migration annuelle.
6. Reprendre `LoginPage`: remember me, request access, reset password, langue.

## Changements web effectues dans cette tranche

- Sidebar React compact/full persistante comme le desktop.
- Navigation web alignee sur les vues desktop principales.
- Hook `useApiResource` compatible avec les reponses `{data: ...}` et les endpoints bruts comme `/api/access/status/`.
- Dashboard enrichi avec statut ESP32/camera et activites recentes.
- Page etudiants remplacee par une navigation hierarchique.
- Page finances enrichie avec filtres KPI.
- Page logs d'acces enrichie avec statut, compteurs et table filtree.
- Page demandes d'acces super-admin ajoutee.
