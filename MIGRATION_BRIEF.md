# Cahier des charges migration web U.O.R

Ce document sert de rappel principal pour la migration du logiciel desktop vers une
application web moderne. Il doit guider toutes les prochaines modifications dans
`Web_app_migration`.

## Objectif

Migrer progressivement l'application desktop existante vers une application web
sans perdre la logique metier, les donnees, les integrations, ni les parcours
utilisateur deja fonctionnels.

## Regles non negociables

- Ne pas supprimer le code desktop tant que l'application web n'a pas reproduit
  les memes fonctionnalites.
- Ne pas changer ni recreer la base de donnees existante contenant les donnees
  importantes.
- Utiliser Django pour le backend.
- Utiliser React pour le frontend.
- Garder une structure de fichiers claire: pas de gros fichiers monolithiques,
  chaque fonctionnalite doit avoir son module.
- Proteger les pages et les APIs sensibles: pas d'acces direct aux pages privees
  depuis le navigateur sans authentification.
- Conserver la meme interface utilisateur et les memes pages que l'application
  desktop.
- Conserver les fonctionnalites reseau avec ESP32 et camera IP.
- Le resultat final doit etre responsive, dynamique, rapide, performant et
  hautement securise.

## Fonctionnalites a conserver

- Dashboard complet, avec les memes informations que le logiciel desktop.
- Gestion des etudiants.
- Gestion financiere.
- Gestion des acces.
- Reconnaissance faciale.
- Communication ESP32 et camera IP.
- Notifications par email.
- Notifications WhatsApp.
- APIs de transfert inter-universitaire.
- Authentification, roles et protection des pages.
- Historique, logs et activites recentes.

## Strategie

1. Commencer par le backend Django dans `Web_app_migration/backend`.
2. Brancher Django sur la base existante avec des modeles `managed = False`.
3. Exposer les fonctionnalites desktop via des APIs propres et separees.
4. Tester chaque endpoint contre la logique metier existante.
5. Ajouter le frontend React dans `Web_app_migration/frontend`.
6. Reproduire les pages desktop une par une dans React.
7. Valider que l'application web produit les memes resultats que le desktop.
8. Garder le desktop intact jusqu'a validation complete.

## Etat actuel du backend

- Le backend Django existe dans `Web_app_migration/backend`.
- La configuration Django reutilise la base MySQL existante.
- Les modeles Django de donnees sont non geres par Django.
- Les routes principales existent pour:
  - sante backend;
  - authentification;
  - dashboard;
  - etudiants;
  - finances;
  - controle d'acces;
  - transferts;
  - notifications;
  - compatibilite ESP32.
- Le backend doit demarrer avec l'environnement virtuel local
  `Web_app_migration/venv`, sans utiliser l'environnement virtuel racine du
  projet desktop.

## Priorites backend immediates

1. Faire un audit de couverture: fonctionnalites desktop existantes versus APIs
   Django disponibles. L'audit courant est dans
   `backend/API_COVERAGE_AUDIT.md`.
2. Ajouter des tests backend pour les endpoints critiques.
3. Renforcer la securite de configuration: `SECRET_KEY`, middleware CSRF quand
   applicable, CORS, HTTPS et settings de production.
4. Verifier les endpoints de reconnaissance faciale avec camera IP reelle.
5. Verifier les notifications email et WhatsApp avec configuration reelle.
6. Documenter les routes API et leurs payloads.
7. Garder les fichiers backend courts et separes par domaine.
