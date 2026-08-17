# Finance API — Backend README

Django REST API for the Personal Financial App. Handles authentication (JWT), financial records, bank statement PDF extraction, debts, goals, analytics snapshots, exports, and AI-powered analysis/categorization/chat (Gemini / OpenAI / Anthropic).

- **Python 3.14** (3.12+ works), **Django 6.0**, **Django REST Framework 3.17**, **SimpleJWT 5.5**
- SQLite by default; MySQL supported via env vars
- PDF parsing via `pdfplumber`; PDF reports via `reportlab`
- AI keys: live-validated, Fernet-encrypted at rest

## Table of Contents

- [Setup](#setup)
- [Run](#run)
- [Configuration (`.env`)](#configuration-env)
- [Auth](#auth)
  - [Register](#register)
  - [Login](#login)
  - [Refresh / Verify](#refresh--verify)
  - [Logout](#logout)
  - [Me](#me)
- [Records](#records)
- [Statements & Extraction](#statements--extraction)
- [Extracted Transactions](#extracted-transactions)
- [Debts](#debts)
- [Goals](#goals)
- [Snapshots & Analytics](#snapshots--analytics)
- [AI Endpoints](#ai-endpoints)
- [Exports](#exports)
- [Profile & Choices](#profile--choices)
- [Data Models](#data-models)
- [Errors & Throttling](#errors--throttling)
- [Tests](#tests)

---

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

pip install django \
  djangorestframework \
  djangorestframework-simplejwt \
  django-cors-headers \
  python-dotenv \
  cryptography \
  requests \
  pdfplumber \
  reportlab \
  pillow

cp .env.example .env   # if present, otherwise create .env manually (see below)
```

There is no `requirements.txt` — the package list above is the complete dependency set.

## Run

```bash
python manage.py migrate
python manage.py runserver        # API at http://localhost:8000/api/
```

Admin site: `python manage.py createsuperuser`, then `/admin/`. Management command for statement re-detection: `python manage.py detect_statement_types [--all] [--dry-run]`.

## Configuration (`.env`)

`.env` lives next to `manage.py` and is loaded by `config/settings.py`. Everything is optional except `DJANGO_SECRET_KEY` for non-dev use.

| Variable | Default | Notes |
|----------|---------|-------|
| `DJANGO_SECRET_KEY` | dev fallback | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. Changing it invalidates stored (encrypted) AI keys. |
| `DJANGO_DEBUG` | `true` | `false` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | comma-separated |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174` | comma-separated frontend origins |
| `GEMINI_API_KEY` | *(empty)* | fallback Gemini key when no per-user key is stored |
| `JWT_ACCESS_MINUTES` | `30` | access token lifetime |
| `JWT_REFRESH_DAYS` | `7` | refresh token lifetime |
| `THROTTLE_LOGIN` | `10/min` | login rate limit |
| `THROTTLE_REGISTER` | `10/hour` | register rate limit |
| `DB_ENGINE` | `sqlite` | `mysql` switches the DB; then set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |

## Auth

All endpoints except those marked **public** require `Authorization: Bearer <access_token>`. All responses return JSON.

### Register

`POST /api/auth/register/` — **public**, throttled (`10/hour`)

```json
{ "username": "alice", "password": "supersecret", "email": "alice@example.com" }
```

→ `201` — user is signed in immediately:

```json
{
  "refresh": "eyJhbGci...",
  "access": "eyJhbGci...",
  "user": { "id": 1, "username": "alice", "email": "alice@example.com", "is_staff": false, "date_joined": "..." }
}
```

`400` on validation errors with `{ "error": "...", "field_errors": {...} }` (username is case-insensitively unique; Django password validators apply).

### Login

`POST /api/auth/login/` — **public**, throttled (`10/min`)

```json
{ "username": "alice", "password": "supersecret" }
```

→ `200` with the same shape as register.

### Refresh / Verify

- `POST /api/auth/refresh/` — **public** — `{ "refresh": "..." }` → `{ "access": "...", "refresh": "..." }`. Rotating: each refresh issues a new refresh token and blacklists the old one.
- `POST /api/auth/verify/` — **public** — `{ "token": "..." }` → `200` (or `401`).

### Logout

`POST /api/auth/logout/` — **authenticated**

```json
{ "refresh": "..." }
```

→ `200 { "message": "Logged out successfully." }` — blacklists the refresh token server-side.

### Me

`GET /api/auth/me/` — **authenticated** → `200` user payload (see register response).

---

## Records

`/api/records/` — full CRUD, all endpoints authenticated, always scoped to the requesting user.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/records/` | list (filters below) |
| POST | `/api/records/` | create |
| GET | `/api/records/{id}/` | retrieve |
| PUT / PATCH | `/api/records/{id}/` | update |
| DELETE | `/api/records/{id}/` | delete |

**Fields:** `type` (`income`\|`expense`), `category`, `amount`, `date`, `description`, `account_bank` (`credit_card`, `debit_card`, `cash_loan`, `bank_loan`, `cash`, `business_card`, `bre_b`, `other`), `account_bank_other` (free text when `other`), `created_at`.

**Filters** (query params, same helper used by exports & analysis):

| Param | Meaning |
|-------|---------|
| `type` | `income` \| `expense` |
| `category` | exact category match |
| `account_bank` | account type |
| `start_date` / `end_date` | `date__gte` / `date__lte` (ISO `YYYY-MM-DD`) |
| `min_amount` / `max_amount` | amount range |

---

## Statements & Extraction

`/api/statements/` — CRUD for uploaded bank statement PDFs.

### Create (upload)

`POST /api/statements/` — **multipart/form-data**: `file` (PDF required), optional `statement_type` and `password` (for encrypted PDFs). Content is deduplicated by SHA-256; duplicate uploads are rejected. The statement is parsed synchronously when fast enough and returned with a `status` of `processing` or later.

### Read / update / delete

- `GET /api/statements/` — list
- `GET /api/statements/{id}/` — retrieve
- `DELETE /api/statements/{id}/` — delete
- `PUT /api/statements/{id}/` — update (e.g. correct `statement_type`, `bank_name`)

### Custom actions

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/statements/extracted-transactions/` | all extracted transactions (alias, also under `/api/extracted/`) |
| GET | `/api/statements/{id}/file/` | download the original PDF |
| POST | `/api/statements/{id}/reprocess/` | re-run extraction (clears old extracted transactions, resets counts) |

**Status lifecycle:** `uploaded → processing → extracted → review_pending → completed | failed`. Failed statements carry an `error_message`.

---

## Extracted Transactions

`/api/extracted/` — transactions extracted from statements, awaiting review.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/extracted/` | list — filters: `statement_id`, `needs_review` |
| PATCH | `/api/extracted/{id}/` | adjust description / suggested category etc. |
| POST | `/api/extracted/{id}/confirm/` | confirm one transaction → creates/updates the `FinancialRecord`, marks reviewed, records categorization memory |
| POST | `/api/extracted/bulk_confirm/` | body `{ "transactions": [{ "id", "category", "type", "description" }, ...] }` — confirm many at once |

Confirming imports the transaction into the ledger: `statement.total_transactions_imported` increments and the statement flips to `completed` when all extracted rows are confirmed.

---

## Debts

`/api/debts/` — CRUD (fields: `name`, `debt_type`, `creditor`, `original_amount`, `current_balance`, `interest_rate`, `minimum_payment`, `due_date`, `start_date`, `end_date`, `status`, `notes`).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/debts/{id}/make_payment/` | `{ "amount": 250 }` — reduces balance, applies interest logic |
| GET | `/api/debts/payoff_strategy/` | computed payoff plan across all debts |

---

## Goals

`/api/goals/` — CRUD (fields: `title`, `target_amount`, `current_amount`, `start_date`, `end_date`, `category`, `status`, `description`).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/goals/analysis/` | goal progress summary (overall %, achieved vs total) |

---

## Snapshots & Analytics

### Snapshots

`/api/snapshots/` — read-only list of precomputed monthly financial snapshots.

`POST /api/snapshots/generate/` — computes the snapshot for the current (or provided) month: totals, `savings_rate`, liquidity ratios (current/quick/cash), profitability (`net_profit_margin`, `expense_ratio`), solvency (`debt_to_income`, `debt_to_asset`), YoY growth, category breakdown, `net_worth`.

### Analytics

`GET /api/analytics/?start_date=&end_date=` — dashboard payload: snapshot-cached breakdowns, ratios and debt summary with a live-records fallback.

---

## AI Endpoints

### Provider config & API keys

`GET /api/ai-settings/` — **authenticated** — returns the user's AI config with **masked** keys only:

```json
{
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "keys": { "gemini": "••••abcd" },
  "default_models": { "gemini": "gemini-2.5-flash", "openai": "gpt-4o-mini", "anthropic": "claude-3-5-haiku-latest" }
}
```

`PUT /api/ai-settings/` — body accepts any of `{ "provider"?, "model"?, "api_key"? }`.

- **`api_key` is validated live** against the provider before saving:
  - Gemini: `GET https://generativelanguage.googleapis.com/v1beta/models?key=…`
  - OpenAI: `GET https://api.openai.com/v1/models` (Bearer)
  - Anthropic: `GET https://api.anthropic.com/v1/models` (`x-api-key`)
- Valid keys are **Fernet-encrypted** (key derived from `DJANGO_SECRET_KEY`) and stored per-provider in `UserSetting.ai_keys`; they are never returned in plaintext.
- Invalid key → `400` `{ "error": "...", "error_code": "invalid_key" }` (other codes: `rate_limit`, `billing_error`, `permission_denied`, `network_error`, `unknown_error`).

### Financial analysis

`POST /api/analysis/` — `{ "start_date"?, "end_date"?, "type"?, "category"?, "account_bank"? }` → rich-text AI report (executive health audit, budget leak analysis, actionable steps). Falls back to a rule-based report when no AI provider responds.

### Transaction categorization

`POST /api/ai-categorize/` — body `{ "transaction_ids": [...] }` or `{ "descriptions": [...] }` → `{ "results": [{ "id", "description", "suggested_category", "suggested_type", "confidence", "reasoning" }] }`. Uses the user's category/type vocabulary + learned `CategorizationMemory` patterns. `503` when the AI service is unavailable.

### Chat assistant

`POST /api/ai-chat/` — body `{ "message": "...", "transaction_ids": [...], "history": [...] }` → `{ "reply": "...", "actions": [...] }`. The model can answer questions about transactions and propose category/type actions; a rule-engine fallback answers when the AI is unreachable.

---

## Exports

Both respect the same filters as `/api/records/` (see above).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/export/csv/` | CSV download (`financial_bank_extract.csv`) |
| GET | `/api/export/pdf/` | PDF extract (ReportLab) with income/expense/balance summary + ledger table |

---

## Profile & Choices

| Method | Path | Purpose |
|--------|------|---------|
| GET / PUT | `/api/profile/` | user settings: currency code, custom types/categories |
| GET / POST | `/api/custom-categories/` | custom categories; `DELETE /{pk}/` |
| GET / POST | `/api/custom-types/` | custom transaction types; `DELETE /{pk}/` |
| GET | `/api/choices/` | full category + type vocabulary (seeded + custom) |
| DELETE | `/api/choices/{pk}/` | remove a custom choice |

---

## Data Models

| Model | Purpose | Key fields |
|-------|---------|-----------|
| `FinancialRecord` | ledger entry | `type`, `category`, `amount`, `date`, `description`, `account_bank` |
| `BankStatement` | uploaded PDF | `file`, `content_hash`, `bank_name`, `password`, `statement_type`, `statement_period_*`, `status`, `error_message` |
| `ExtractedTransaction` | pending import | `statement`, `raw/cleaned_description`, `amount`, `date`, `suggested_category`, `confidence_score`, `needs_review`, `is_reviewed` |
| `Debt` | liability | `name`, `current_balance`, `interest_rate`, `minimum_payment`, `due_date`, `status` (+ computed `monthly_interest`, `payoff_months_remaining`) |
| `ExpectedGoal` | savings goal | `title`, `target_amount`, `current_amount`, `status` |
| `FinancialSnapshot` | monthly analytics cache | `date`, totals, ratios, YoY growth, `net_worth`, `expenses_per_category` |
| `UserSetting` | per-user config | `ai_provider`, `ai_model`, `ai_keys` (encrypted dict), currency |
| `CustomType` / `CustomCategory` / `Choice` | vocabulary | seeded defaults + user additions |
| `CategorizationMemory` | learned patterns | `pattern` → `category`/`type`, `hit_count` |

Models live in `finance_api/models/` (one module per domain); serializers in `finance_api/serializers/`.

## Errors & Throttling

- Errors are JSON `{ "error": "...", "field_errors"?: {...}, "error_code"?: "..." }`.
- AI failures: `503` `{ "error": "AI service unavailable: ..." }`.
- Throttling: `429` for login/register rate limits (disabled during test runs).
- Default auth failure: `401` from SimpleJWT.

## Tests

```bash
python manage.py test
```

The suite covers auth, statement processing, debt payment logic, AI settings, and live key-validation mocking (no external calls during tests).
