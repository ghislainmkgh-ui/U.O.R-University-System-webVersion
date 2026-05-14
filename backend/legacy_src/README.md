# Web-local service snapshot

This folder contains the service modules that the Django backend needs from the
desktop codebase: `app`, `core`, `config`, and `access_server.py`.

At runtime, Django imports these modules from this folder, not from the project
root. This keeps `Web_app_migration` autonomous while the migration is still
reusing desktop business logic.
