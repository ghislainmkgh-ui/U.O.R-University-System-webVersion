# U.O.R University System - Web Version

Version web du systeme de gestion universitaire U.O.R. Cette application reprend les fonctions principales de la version desktop dans une architecture web autonome, avec un backend Django et un frontend React.

## Apercu

L'application permet de gerer les etudiants, les annees academiques, les paiements, les periodes d'examens, les demandes d'acces administrateur, les transferts et la validation d'acces par camera/ESP32.

Objectif important du projet: le dossier `Web_app_migration` doit rester autonome. Les dependances, configurations, scripts, fichiers runtime et copies de services necessaires a la version web doivent rester dans ce dossier.

## Fonctionnalites

- Authentification des utilisateurs avec restauration de la derniere page ouverte.
- Tableau de bord web responsive avec indicateurs et graphiques.
- Gestion des etudiants par faculte, departement, promotion et annee academique active.
- Ajout et modification d'etudiants avec photo, validation de visage et messages clairs pour l'utilisateur.
- Gestion des annees academiques avec une seule annee active a la fois.
- Copie d'etudiants d'une annee academique vers une autre sans supprimer les anciens dossiers.
- Configuration des frais et seuils par promotion.
- Historique financier structure par faculte, departement et promotion.
- Gestion des periodes d'examens.
- Validation/rejet des demandes d'acces administrateur par le super admin.
- Serveur local pour camera et ESP32 demarre avec le backend afin d'eviter les requetes echouees.
- Interface avec theme et langue configurables.

## Technologies

```text
Backend   Django 5, Django REST style views, MySQL, JWT, OpenCV, face-recognition
Frontend  React 19, Vite, React Router, lucide-react
Runtime   PowerShell scripts, local storage web, services camera/ESP32
```

## Structure

```text
Web_app_migration/
  backend/                 API Django et logique web
  backend/legacy_src/      Copie locale des services metier utiles au web
  frontend/                Application React/Vite
  logs/                    Journaux runtime web
  storage/                 Fichiers generes et uploads web
  .env.example             Exemple de configuration backend web
  start_backend.ps1        Script de demarrage backend
  start_frontend.ps1       Script de demarrage frontend
```

## Prerequis

- Python 3.11 ou plus recent.
- Node.js 20 ou plus recent.
- MySQL avec la base utilisee par le projet.
- Git.

Pour la reconnaissance faciale, certaines installations Windows peuvent demander les dependances natives de `face-recognition`/`dlib`.

## Configuration

Copier le fichier d'exemple puis adapter les valeurs locales:

```powershell
cd Web_app_migration
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

Variables principales:

```text
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=uor_university
DB_PORT=3306

WEB_FRONTEND_URL=http://127.0.0.1:5173
WEB_BACKEND_PUBLIC_URL=http://127.0.0.1:8000
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Les fichiers `.env`, `frontend/.env`, `logs/`, `storage/`, `frontend/dist/`, `frontend/node_modules/` et `venv/` ne doivent pas etre pousses sur GitHub.

## Installation Backend

```powershell
cd Web_app_migration
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Verifier la configuration Django:

```powershell
.\venv\Scripts\python.exe backend\manage.py check
```

## Installation Frontend

```powershell
cd Web_app_migration\frontend
npm install
npm run build
```

## Lancement

Backend:

```powershell
cd Web_app_migration
.\start_backend.ps1
```

Frontend:

```powershell
cd Web_app_migration
.\start_frontend.ps1
```

URLs locales:

```text
Frontend  http://127.0.0.1:5173
Backend   http://127.0.0.1:8000
Health    http://127.0.0.1:8000/api/health/
```

## Services Automatiques

Au demarrage du backend, l'application peut aussi lancer:

- le serveur ESP32/camera sur le port configure par `ESP32_PORT`;
- le tunnel de validation super admin pour approuver ou rejeter les demandes d'acces.

Ces options sont configurees dans `.env`:

```text
ACCESS_SERVER_AUTOSTART=True
ESP32_PORT=5050
ACCESS_APPROVAL_AUTOSTART=True
ACCESS_APPROVAL_TUNNEL_AUTOSTART=True
ACCESS_APPROVAL_BASE_URL=
ACCESS_APPROVAL_TUNNEL_SUBDOMAIN=
```

Si `ACCESS_APPROVAL_BASE_URL` est vide, le backend peut utiliser `localtunnel` pour generer une URL publique temporaire.

## Commandes Utiles

Build frontend:

```powershell
cd Web_app_migration\frontend
npm run build
```

Check backend:

```powershell
cd Web_app_migration
.\venv\Scripts\python.exe backend\manage.py check
```

Compilation Python rapide:

```powershell
cd Web_app_migration
.\venv\Scripts\python.exe -m compileall -q backend
```

## Notes De Developpement

- Garder la version web autonome dans `Web_app_migration`.
- Ne pas importer directement les dossiers de la version desktop au runtime.
- Utiliser `backend/legacy_src/` pour les services metier repris par le web.
- Eviter les messages techniques dans l'interface utilisateur; les erreurs visibles doivent etre claires et comprehensibles.
- Toute inscription d'etudiant doit utiliser l'annee academique active.

## Licence

Projet academique U.O.R. Utilisation et distribution selon les regles du proprietaire du depot.
