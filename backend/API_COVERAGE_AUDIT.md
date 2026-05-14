# Audit de couverture backend Django

Date: 2026-05-08

Ce document compare les grandes fonctionnalites du logiciel desktop avec les
APIs Django actuellement disponibles dans `Web_app_migration/backend`.

## Resume

Le backend Django couvre deja les domaines principaux de la migration:

- authentification et demandes d'acces administrateur;
- dashboard;
- etudiants, facultes, departements et promotions;
- finances, paiements, annees academiques et periodes d'examen;
- controle d'acces ESP32 et camera IP;
- notifications email et WhatsApp;
- transferts inter-universitaires;
- rapports et exports CSV principaux;
- modeles Django non geres pour reutiliser la base existante.

Les prochains ecarts backend a traiter sont les exports PDF/Excel si necessaires
et l'enrichissement progressif de la documentation des payloads API.

## Couverture par domaine

| Domaine desktop | Etat API Django | Endpoints principaux | Notes |
| --- | --- | --- | --- |
| Sante backend | Couvert | `GET /api/health/` | Repond en HTTP localement. |
| Connexion admin/utilisateur | Couvert | `POST /api/auth/login/`, `GET /api/auth/me/` | JWT present, pages frontend devront l'utiliser pour proteger les routes. |
| Demandes d'acces admin | Couvert | `/api/auth/request-access/`, `/api/auth/access-requests/...` | Approval/reject present, lien email HTML conserve. |
| Dashboard | Couvert | `/api/dashboard/summary/`, `/api/dashboard/recent-activities/`, `/api/dashboard/faculty-stats/` | Donnees branchees sur `DashboardService`. |
| Etudiants | Couvert | `/api/students/`, `/api/students/<id>/`, `/api/students/<id>/photo/` | Creation, lecture, mise a jour, suppression logique et photo. |
| Faculte/departement/promotion | Couvert | `/api/students/faculties/`, `/api/students/departments/`, `/api/students/promotions/` | Creation et listes disponibles. |
| Reconnaissance faciale a l'inscription | Partiel | `POST /api/students/`, `PATCH /api/students/<id>/` | Encodage photo appele si photo base64 fournie; a tester avec images reelles. |
| Finances | Couvert | `/api/finance/overview/`, `/api/finance/payments/`, `/api/finance/students/<id>/history/` | Paiement et generation de code via service existant. |
| Seuils et frais | Couvert | `/api/finance/academic-years/`, `/api/finance/promotions/<id>/financials/` | Certaines routes exigent super admin. |
| Periodes d'examen | Couvert | `/api/finance/exam-periods/` | CRUD partiel: liste, creation, suppression. |
| Migration annee academique | Couvert | `/api/finance/academic-year-migration/`, `/api/finance/academic-year-migration/audit/` | Dry run et audit disponibles via service existant. |
| Controle acces ESP32 | Couvert | `/status/`, `/validate_code/`, `/verify_face/`, `/verify_code/` | Compatibilite ancienne API conservee. |
| Controle acces web | Couvert | `/api/access/status/`, `/api/access/validate-code/`, `/api/access/verify-code/`, `/api/access/logs/` | Camera IP indiquee indisponible pendant le dernier check local. |
| Notifications | Couvert | `/api/notifications/status/`, `/api/notifications/send-email/`, `/api/notifications/send-whatsapp/` | Statut email/WhatsApp expose; envoi reel depend de `.env`. |
| Transferts admin | Couvert | `/api/transfers/pending/`, `/api/transfers/history/`, `/api/transfers/outgoing/` | Approbation, rejet, partenaires et packages disponibles. |
| API partenaire transfert | Couvert | `/api/v1/health/`, `/api/v1/auth/token/`, `/api/v1/transfer/receive/` | Compatibilite API transfert conservee. |
| Rapports | Couvert pour les rapports principaux | `/api/reports/summary/`, `/api/reports/students/`, `/api/reports/finance/`, `/api/reports/access-logs/` | JSON et CSV disponibles pour les rapports principaux. |
| Export | Couvert pour CSV principal | `?format=csv` sur les routes rapports | PDF/Excel restent a definir si necessaires. |
| Donnees academiques detaillees | Couvert | `/api/academics/students/<id>/summary/`, `/api/academics/students/<id>/records/`, `/api/academics/students/<id>/documents/` | Notes et documents ont maintenant CRUD API. |
| Internationalisation | A reporter au frontend | Aucune API dediee | React pourra reutiliser une structure i18n propre. |

## Routes protegees

Les domaines admin utilisent les decorateurs `admin_required` ou
`super_admin_required`. Le frontend React devra donc:

- stocker le JWT apres login;
- envoyer `Authorization: Bearer <token>`;
- bloquer les pages privees sans token;
- verifier le role pour les vues super admin.

## Points de verification terrain

- Tester la camera IP reelle via `/api/access/status/` puis
  `/api/access/verify-code/`.
- Tester une photo etudiant reelle en `photo_base64` pour confirmer l'encodage
  visage cote backend.
- Tester la configuration email et WhatsApp reelle avec
  `/api/notifications/status/`.
- Tester un paiement reel de bout en bout: paiement, profil financier, code
  d'acces, notification.
- Tester un transfert entrant/sortant avec donnees reelles ou jeu de test.

## Prochaines actions recommandees

1. Ajouter des tests avec mocks de services pour les endpoints admin en mode token.
2. Ajouter PDF/Excel si le frontend ou les jurys en ont besoin.
3. Brancher le frontend React sur les routes documentees.
4. Tester reconnaissance faciale, camera IP, email et WhatsApp sur le reseau reel.
