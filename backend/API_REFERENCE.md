# Reference API backend Django

Base locale: `http://127.0.0.1:8000`

Toutes les routes admin privees demandent:

```http
Authorization: Bearer <jwt>
Content-Type: application/json
```

Le JWT est obtenu via `POST /api/auth/login/`.

## Authentification

### `POST /api/auth/login/`

```json
{
  "identifier": "admin@example.com",
  "password": "mot-de-passe"
}
```

Retourne `token`, `token_type`, `expires_in` et `user`.

### `GET /api/auth/me/`

Retourne l'utilisateur courant a partir du JWT.

### `POST /api/auth/request-access/`

```json
{
  "username": "admin2",
  "email": "admin2@example.com",
  "password": "mot-de-passe"
}
```

## Dashboard

- `GET /api/dashboard/summary/`
- `GET /api/dashboard/recent-activities/?limit=8`
- `GET /api/dashboard/faculty-stats/?with_photos=true`
- `GET /api/dashboard/finance-snapshot/?limit=200`

## Etudiants

### `GET /api/students/`

Liste les etudiants actifs avec informations financieres et academiques de base.

### `POST /api/students/`

```json
{
  "student_number": "STU2026-001",
  "firstname": "Jean",
  "lastname": "Banza",
  "email": "jean@example.com",
  "phone_number": "+243000000000",
  "promotion_id": 1,
  "academic_year_id": 1,
  "threshold_required": 300,
  "photo_base64": "data:image/jpeg;base64,...",
  "photo_extension": ".jpg"
}
```

`photo_base64` est obligatoire a la creation. La photo est stockee en base (`passport_photo_blob`) et sur disque avec un nom unique, puis refusee si elle ne contient pas exactement un visage net, bien cadre et compatible avec la reconnaissance faciale.

- `GET /api/students/<id>/`
- `PATCH /api/students/<id>/`
- `DELETE /api/students/<id>/`
- `GET /api/students/<id>/photo/`
- `GET|POST /api/students/faculties/`
- `GET|POST /api/students/departments/`
- `GET|POST /api/students/promotions/`

## Donnees Academiques

### `GET /api/academics/students/<id>/summary/`

Retourne le resume academique: nombre de cours, documents, credits, moyenne,
reussites/echecs et elements transferes.

### `GET /api/academics/students/<id>/records/`

Liste les notes/cours d'un etudiant.

### `POST /api/academics/students/<id>/records/`

```json
{
  "course_name": "Programmation Python",
  "course_code": "PY101",
  "credits": 4,
  "grade": 16.5,
  "semester": "1",
  "exam_date": "2026-05-08",
  "professor_name": "Prof. Kambale",
  "status": "PASSED",
  "remarks": "Tres bien"
}
```

La note doit etre entre `0` et `20`. Si `grade_letter` est absent, le backend le
calcule.

- `GET /api/academics/records/<record_id>/`
- `PATCH /api/academics/records/<record_id>/`
- `DELETE /api/academics/records/<record_id>/`

### `GET /api/academics/students/<id>/documents/`

Liste les documents d'un etudiant, sans exposer les blobs.

### `POST /api/academics/students/<id>/documents/`

```json
{
  "document_type": "CERTIFICATE",
  "title": "Certificat de scolarite",
  "description": "Document administratif",
  "author": "U.O.R",
  "category": "Administration",
  "issue_date": "2026-05-08",
  "status": "ACTIVE",
  "file_base64": "data:application/pdf;base64,...",
  "file_extension": ".pdf"
}
```

`file_base64` est optionnel. Si fourni, le fichier est aussi stocke dans
`storage/student_documents/<student_id>/`.

- `GET /api/academics/documents/<document_id>/`
- `PATCH /api/academics/documents/<document_id>/`
- `DELETE /api/academics/documents/<document_id>/`
- `GET /api/academics/documents/<document_id>/download/`

## Finances

### `POST /api/finance/payments/`

```json
{
  "student_id": 1,
  "amount": 150
}
```

Routes principales:

- `GET /api/finance/overview/?limit=200`
- `GET /api/finance/students/<id>/history/`
- `GET /api/finance/students/<id>/access-code/`
- `GET|POST /api/finance/academic-years/`
- `GET|POST /api/finance/exam-periods/`
- `GET /api/finance/promotions/`
- `POST /api/finance/academic-year-migration/`
- `GET /api/finance/academic-year-migration/audit/`

## Controle d'Acces ESP32 et Camera IP

Routes web:

- `GET /api/access/status/`
- `POST /api/access/validate-code/`
- `POST /api/access/verify-code/`
- `GET /api/access/logs/`

Routes compatibles ESP32:

- `GET /status/`
- `POST /validate_code/`
- `POST /verify_face/`
- `POST /verify_code/`

Payload code:

```json
{
  "code": "123456"
}
```

## Notifications

- `GET /api/notifications/status/`
- `POST /api/notifications/send-email/`
- `POST /api/notifications/send-whatsapp/`

Email:

```json
{
  "recipient": "student@example.com",
  "subject": "Notification U.O.R",
  "message": "Votre message"
}
```

WhatsApp:

```json
{
  "phone": "+243000000000",
  "message": "Votre message"
}
```

## Rapports et Exports

- `GET /api/reports/summary/`
- `GET /api/reports/students/?status=eligible`
- `GET /api/reports/students/?format=csv`
- `GET /api/reports/finance/?limit=500&format=csv`
- `GET /api/reports/access-logs/?limit=500&status=DENIED`

Statuts rapport etudiants: `all`, `eligible`, `non_eligible`, `paid`,
`never_paid`.

## Transferts

Routes admin:

- `GET /api/transfers/pending/`
- `GET /api/transfers/history/`
- `POST /api/transfers/outgoing/`
- `POST /api/transfers/incoming/<request_id>/approve/`
- `POST /api/transfers/incoming/<request_id>/reject/`
- `GET /api/transfers/partners/`
- `GET|PATCH /api/transfers/partners/<university_code>/api-url/`
- `GET /api/transfers/packages/<transfer_code>/`

API partenaire:

- `GET /api/v1/health/`
- `POST /api/v1/auth/token/`
- `POST /api/v1/transfer/receive/`
- `POST /api/v1/transfer/send/`
- `GET /api/v1/transfer/status/<transfer_code>/`
- `GET /api/v1/universities/`
