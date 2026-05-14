# Statut backend Django

Date: 2026-05-08

Le backend Django est pret pour commencer le frontend React.

## Fonctionnalites couvertes

- Authentification JWT.
- Protection des routes admin et super admin.
- Dashboard.
- Etudiants, photos et reconnaissance faciale a l'inscription.
- Facultes, departements et promotions.
- Finances, paiements, codes d'acces, annees academiques et periodes d'examen.
- Donnees academiques: notes/cours, documents, resume, telechargement fichier.
- Controle d'acces ESP32 et camera IP.
- Notifications email et WhatsApp.
- Transferts inter-universitaires admin et API partenaire.
- Rapports JSON et exports CSV.
- Documentation API frontend.
- Tests de fumee backend.
- Settings securite configurables pour production.

## Verifications automatiques

- `python manage.py check`: OK.
- `python manage.py test`: OK.
- `python -m compileall -q apps web_config manage.py`: OK.
- `python manage.py check --deploy` avec variables production: OK.

## Verifications terrain encore necessaires

Ces points dependent du materiel ou de secrets reels, donc ils doivent etre
valides sur la machine/reseau final:

- Camera IP disponible et image fraiche.
- Reconnaissance faciale avec une vraie photo et un vrai flux camera.
- Envoi email avec les identifiants SMTP reels.
- Envoi WhatsApp avec Ultramsg/Twilio reel.
- Test ESP32 physique sur le reseau.

Ces points ne bloquent pas le debut du frontend React: les endpoints existent et
repondent.

