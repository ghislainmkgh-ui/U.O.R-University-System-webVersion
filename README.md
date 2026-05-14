# U.O.R Web App Migration

Migration progressive de l'application desktop vers une architecture web.

Objectif actuel: demarrer par un backend Django isole, sans supprimer ni modifier
l'application desktop existante. Le dossier `Web_app_migration` doit rester
autonome: configuration web, environnement Python, frontend et stockage runtime
vivent dans ce dossier.

Le cahier des charges de la migration est dans
[`MIGRATION_BRIEF.md`](MIGRATION_BRIEF.md). Toute modification importante doit
respecter ce document.

Le statut backend est dans [`backend/BACKEND_STATUS.md`](backend/BACKEND_STATUS.md)
et le contrat API pour le frontend est dans
[`backend/API_REFERENCE.md`](backend/API_REFERENCE.md).

## Structure

```text
Web_app_migration/
  backend/   API Django + pont vers les services metier existants
  frontend/  futur client React
```

Le backend reutilise la base MySQL actuelle (`uor_university`) et declare les
modeles Django en `managed = False`. Django ne doit donc pas creer ou remplacer
les tables metier existantes.

## Configuration

Le desktop conserve son `.env` a la racine du projet. La migration web ne charge
pas ce fichier: elle utilise son propre fichier:

```text
Web_app_migration/.env
```

Le backend Django charge les variables web dans cet ordre:

1. `Web_app_migration/.env`, configuration principale web;
2. `Web_app_migration/backend/.env`, surcharge locale backend optionnelle.

Les fichiers uploades et journaux runtime web restent aussi dans le dossier web:

```text
Web_app_migration/storage/
Web_app_migration/logs/
```

Pendant la migration, le backend reutilise une copie locale de la logique metier
desktop dans:

```text
Web_app_migration/backend/legacy_src/
```

Au runtime, Django importe cette copie locale, pas les dossiers `app`, `core` ou
`config` situes a la racine du projet desktop.

## Demarrage backend

```powershell
cd Web_app_migration
.\venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Ou avec le script local:

```powershell
cd Web_app_migration
.\start_backend.ps1
```

Au demarrage du backend web, Django lance aussi les services runtime suivants:

- serveur ESP32/camera (`access_server.py`) sur `ESP32_PORT` pour eviter que
  les requetes du materiel echouent pendant que le logiciel est ouvert;
- tunnel public de validation Super Admin pour les liens e-mail
  approuver/rejeter des demandes d'acces.

Ces services restent configurables dans `Web_app_migration/.env`:

```text
ACCESS_SERVER_AUTOSTART=True
ESP32_PORT=5050
ACCESS_APPROVAL_AUTOSTART=True
ACCESS_APPROVAL_TUNNEL_AUTOSTART=True
ACCESS_APPROVAL_BASE_URL=
ACCESS_APPROVAL_TUNNEL_SUBDOMAIN=
```

Si `ACCESS_APPROVAL_BASE_URL` est vide, le backend tente de demarrer
`localtunnel` avec `npx --yes localtunnel` et injecte l'URL publique obtenue
pour les e-mails Super Admin. Pour une URL stable, renseigner soit
`ACCESS_APPROVAL_BASE_URL=https://votre-sous-domaine.loca.lt`, soit
`ACCESS_APPROVAL_TUNNEL_SUBDOMAIN=votre-sous-domaine`.

Premiere installation backend:

```powershell
cd Web_app_migration
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Endpoints principaux:

- `GET /api/health/`
- `POST /api/auth/login/`
- `GET /api/dashboard/summary/`
- `GET /api/students/`
- `GET /api/finance/overview/`
- `GET /api/reports/summary/`
- `GET /api/reports/students/?format=csv`
- `GET /api/academics/students/<id>/summary/`
- `POST /api/academics/students/<id>/records/`
- `POST /api/academics/students/<id>/documents/`
- `POST /verify_code/` compatible ESP32
- `POST /api/v1/transfer/receive/` compatible API transfert

## Demarrage frontend

```powershell
cd Web_app_migration
.\start_frontend.ps1
```

URL locale: `http://127.0.0.1:5173`
