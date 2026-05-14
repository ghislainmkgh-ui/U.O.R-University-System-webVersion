# Frontend React

Client React de la migration web U.O.R.

## Demarrage

```powershell
cd Web_app_migration
.\start_frontend.ps1
```

Ou directement:

```powershell
cd Web_app_migration\frontend
npm install
npm run dev -- --port 5173
```

URL locale: `http://127.0.0.1:5173`

Le backend Django doit tourner sur `http://127.0.0.1:8000`.

## Structure

```text
src/
  api/          client HTTP
  components/   composants reutilisables
  hooks/        chargements API
  layout/       shell admin
  pages/        pages metier
  routes/       routes protegees
  state/        authentification
```
