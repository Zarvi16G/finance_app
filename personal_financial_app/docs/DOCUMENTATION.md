# Project Documentation

In-depth documentation for the Personal Financial App. For quick-start instructions see the [root README](../README.md); for the REST API reference see [backend/README.md](../backend/README.md).

Companion documents: [OpenAPI schema (Swagger)](openapi.yaml) for the full machine-readable API contract, and the [frontend record](frontend/architecture-design.md) for the React app's architecture, routes, data flows and known gaps.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Layout](#backend-layout)
3. [Frontend Layout](#frontend-layout)
4. [Data Model](#data-model)
5. [Authentication & Sessions (JWT)](#authentication--sessions-jwt)
6. [AI Provider Integration](#ai-provider-integration)
7. [Bank Statement Processing Pipeline](#bank-statement-processing-pipeline)
8. [Analytics & Snapshots](#analytics--snapshots)
9. [Development Workflows](#development-workflows)
10. [Configuration Reference](#configuration-reference)

---

## Architecture Overview

A classic two-tier setup: a React SPA talks JSON over HTTP to a Django REST API. The API owns all business logic (parsing, analytics, AI calls, encryption); the frontend is a thin, typed client.

```
Browser (React SPA :5173)
   │  axios → /api/*  (Vite dev proxy → :8000)
   ▼
Django REST API (:8000)  ── JWT auth on every endpoint
   ├── finance_api/models/      ORM entities
   ├── finance_api/services/    business logic
   │     ├── statement_parser.py   PDF extraction (pdfplumber)
   │     ├── statement_detection.py
   │     ├── analytics_service.py  ratios & dashboard data
   │     ├── snapshot_service.py   monthly financial snapshots
   │     ├── analysis_service.py   AI analysis reports
   │     ├── chat_service.py       AI chat + rule fallback
   │     └── ai/                   providers, settings, key validation
   ├── finance_api/views/       DRF views (request/response)
   ├── finance_api/crypto.py    Fernet encryption for API keys
   └── DB: SQLite (default) / MySQL — media/ holds uploaded PDFs
```

Design conventions:

- **One module per domain** — `models/`, `views/`, `serializers/` and `services/` all mirror the same domains (records, goals, statements, debts, snapshots, settings).
- **Thin views, fat services** — views validate and serialize; services contain all logic (AI calls, parsing, analytics) so it stays testable.
- **JWT everywhere** — the default DRF permission is `IsAuthenticated` with SimpleJWT; only auth endpoints are `AllowAny`, and they are throttled.
- **Secrets never leak** — AI API keys are encrypted at rest (Fernet), masked in every response, and only the provider that owns them can use them.

## Backend Layout

```
backend/
├── manage.py                  Django entry point
├── config/
│   ├── settings.py            ALL configuration + .env loading
│   ├── urls.py                routes /api/* → finance_api
│   └── asgi.py / wsgi.py
├── finance_api/               the single Django app
│   ├── models/                FinancialRecord, ExpectedGoal, BankStatement,
│   │                          ExtractedTransaction, Debt, FinancialSnapshot,
│   │                          UserSetting, CustomType, CustomCategory, Choice,
│   │                          CategorizationMemory
│   ├── views/                 auth.py, records.py, goals.py, statements.py,
│   │                          debts.py, snapshots.py, analysis.py, analytics.py,
│   │                          ai.py, exports.py, profile.py, choices.py, extracted.py
│   ├── serializers/           auth.py, records.py, goals.py, statements.py,
│   │                          debts.py, snapshots.py
│   ├── services/
│   │   ├── ai/                providers.py (Gemini/OpenAI/Anthropic calls),
│   │   │                      settings.py (per-user AI config + keys),
│   │   │                      key_validation.py (live key checks)
│   │   ├── auth_service.py    register/login/logout helpers, token issuance
│   │   ├── statement_parser.py, statement_detection.py
│   │   ├── categorization.py, chat_service.py
│   │   ├── analysis_service.py, analytics_service.py, snapshot_service.py
│   │   └── filters.py         shared query-param filtering
│   ├── crypto.py              Fernet encryption helpers + masking
│   ├── management/commands/detect_statement_types.py
│   └── migrations/            schema history (12 migrations)
└── db.sqlite3, media/, .env, venv/
```

## Frontend Layout

```
frontend/
├── vite.config.ts             dev proxy: /api → http://localhost:8000
└── src/
    ├── main.tsx / App.tsx     providers + router table
    ├── api/                   axios client + one typed module per resource
    │   ├── client.ts          shared instance; attaches Bearer token,
    │   │                      queues concurrent 401s, single /auth/refresh/
    │   ├── auth.ts, records?, analytics.ts, statements.ts, debts.ts,
    │   └── goals.ts, profile.ts, ai.ts
    ├── auth/                  AuthContext (user state), tokenStorage,
    │                          ProtectedRoute / PublicOnlyRoute guards
    ├── layouts/FullLayout.tsx sidebar shell + theme toggle + user menu
    ├── pages/                 Login.tsx, Register.tsx
    ├── components/            analytics/, statements/, debts/, goals/,
    │                          analysis/, profile/, provider/, shared/, ui/
    └── types/index.ts         shared TypeScript interfaces
```

Key frontend mechanics:

- **Silent re-auth** — `api/client.ts` intercepts 401 responses: concurrent failed requests are queued, a single `POST /auth/refresh/` is fired, and the queue is replayed with the new access token. If refresh fails, tokens are cleared and a custom `auth:unauthorized` event signs the user out.
- **Session restore** — `AuthContext` validates the stored access token against `GET /auth/me/` on page load.
- **Route guards** — `/login` and `/register` are `PublicOnlyRoute`; every dashboard route is behind `ProtectedRoute` inside `FullLayout`.
- **Env var** — `VITE_API_URL` overrides the API base URL (default `/api`, proxied in dev).

## Data Model

### FinancialRecord
The core ledger entry, created manually or by confirming extracted transactions.

| Field | Notes |
|-------|-------|
| `type` | `income` / `expense` |
| `category` | free string, default `"Other"` (fed from the user's vocabulary) |
| `amount` | Decimal(12, 2) |
| `date` | transaction date |
| `description` | free text |
| `account_bank` | `credit_card, debit_card, cash_loan, bank_loan, cash, business_card, bre_b, other` (+ free-text `account_bank_other`) |
| `created_at` | audit timestamp |

### BankStatement
One uploaded PDF.

| Field | Notes |
|-------|-------|
| `id` | UUID |
| `file` / `original_filename` | stored under `media/` |
| `content_hash` | SHA-256 of file content — duplicate uploads are rejected |
| `bank_name` | detected or user-supplied |
| `password` | optional, for encrypted PDFs |
| `statement_type` | `savings, checking, credit_card, loan, investment, other` |
| `statement_period_start/end` | parsed from the document |
| `status` | `uploaded → processing → extracted → review_pending → completed / failed` |
| `total_transactions_extracted / imported` | counts for the UI |
| `error_message` | failure details |

### ExtractedTransaction
A transaction pulled from a statement, pending confirmation.

| Field | Notes |
|-------|-------|
| `statement` | FK to BankStatement |
| `raw_description` / `cleaned_description` | raw PDF text vs. normalized |
| `amount`, `date`, `transaction_type` | parsed values |
| `suggested_category` + `confidence_score` | from AI or rule-based categorization |
| `needs_review` / `is_reviewed` | review workflow flags |
| `user_confirmed_category / type`, `reviewed_at` | applied on confirm |

### Debt
| Field | Notes |
|-------|-------|
| `name`, `debt_type` (7 kinds), `creditor` | identity |
| `original_amount`, `current_balance` | money |
| `interest_rate` (annual %), `minimum_payment` | payoff math |
| `due_date` (1–31), `start_date`, `end_date` | scheduling |
| `status` | `active, paid_off, defaulted, in_grace` |
| properties | `monthly_interest`, `payoff_months_remaining` (computed) |

### ExpectedGoal
`title`, `target_amount`, `current_amount`, `start_date`, `end_date`, `category`, `status` (`pending/ongoing/achieved/failed`), `description`.

### FinancialSnapshot
Monthly (one per month start, `date` unique) precomputed analytics cache:
`total_income`, `total_expenses`, `net_savings`, `savings_rate`, liquidity ratios (`current`, `quick`, `cash`), profitability (`net_profit_margin`, `expense_ratio`), solvency (`debt_to_income`, `debt_to_asset`), YoY growth metrics, `expenses_per_category` JSON, `total_liabilities/assets`, `net_worth`. Built by `snapshot_service` and served by `/api/analytics/`.

### Settings & Vocabulary
- **UserSetting** — single row (pk=1) holding `ai_provider`, `ai_model`, `ai_keys` (encrypted JSON keyed by provider), plus currency/category config.
- **CustomType / CustomCategory / Choice** — the user's vocabulary. `Choice` is the denormalized list of all types/categories (seeded by migration `0009_seed_choices.py`); `CategorizationMemory` learns patterns (min `hit_count` 2) used to improve future AI suggestions.
- **CategorizationMemory** — stores `pattern → category/type` associations the user confirmed, used as context in AI prompts.

## Authentication & Sessions (JWT)

- **Flow**: `POST /api/auth/register/` or `login/` returns `{access, refresh, user}`. The client sends `Authorization: Bearer <access>` on every request.
- **Lifetimes**: access 30 min, refresh 7 days (both env-configurable). `ROTATE_REFRESH_TOKENS` and `BLACKLIST_AFTER_ROTATION` are on: each refresh invalidates the old refresh token.
- **Logout**: `POST /api/auth/logout/` with `{refresh}` blacklists the refresh token server-side.
- **Rate limits**: login `10/min`, register `10/hour` (`THROTTLE_LOGIN` / `THROTTLE_REGISTER`); throttling is disabled during test runs.
- **Password rules**: Django default validators (min length, not common/numeric, not similar to username).

## AI Provider Integration

### Supported providers

| Provider | API used | Default model | Key prefix |
|----------|----------|---------------|------------|
| Gemini (Google) | `generativelanguage.googleapis.com/v1beta` | `gemini-2.5-flash` | `AIza…` |
| OpenAI | `api.openai.com/v1` | `gpt-4o-mini` | `sk-…` |
| Anthropic | `api.anthropic.com/v1` | `claude-3-5-haiku-latest` | `sk-ant-…` |

A custom model string overrides the per-provider default. A single user may store keys for multiple providers and switch at any time.

### Storage & encryption (`finance_api/crypto.py`)

- Keys live in `UserSetting.ai_keys` as a JSON dict `{"gemini": "<ciphertext>", ...}`.
- Encrypted with **Fernet**; the Fernet key is derived from `SHA-256(DJANGO_SECRET_KEY)` — so keys become undecryptable if `DJANGO_SECRET_KEY` changes.
- `GET /api/ai-settings/` never returns plaintext; only `mask_secret()` output (`••••` + last 4 chars).
- Fallback: if no stored Gemini key exists, `GEMINI_API_KEY` from `.env` is used.

### Live validation (`services/ai/key_validation.py`)

When a key is submitted via `PUT /api/ai-settings/`, the backend performs a real authenticated call to the provider before persisting:

- Gemini: `GET /v1beta/models?key=…`
- OpenAI: `GET /v1/models` with `Authorization: Bearer …`
- Anthropic: `GET /v1/models` with `x-api-key: …`
- 10s timeout; verdict codes: `invalid_key`, `rate_limit`, `billing_error`, `permission_denied`, `network_error`, `unknown_error`.
- Only `valid` keys are encrypted and stored; invalid ones return 400 with `{error, error_code}`.

### Feature endpoints & fallbacks

| Feature | Endpoint | Behavior when AI unavailable |
|---------|----------|------------------------------|
| Financial analysis | `POST /api/analysis/` | Rule-based report (flagged to the user) |
| Transaction categorization | `POST /api/ai-categorize/` | 503 (client keeps existing suggestions) |
| Chat assistant | `POST /api/ai-chat/` | Rule-engine answer (`fallback_chat`) |
| Key validation | `PUT /api/ai-settings/` | Rejected with `network_error` |

All AI calls share a uniform adapter (`services/ai/providers.py:call_ai`) that resolves provider/model/key from stored settings and supports `json_mode` for structured outputs (e.g. category suggestions).

## Bank Statement Processing Pipeline

```
Upload PDF (POST /api/statements/)            ← status: uploaded
   │ content_hash SHA-256 dedupe
   ▼
Parse (services/statement_parser.py)          ← status: processing
   │ pdfplumber text extraction (optional password)
   │ line-item detection (date, amount, description)
   ▼
Detect bank & statement type                  ← status: extracted
   │ (services/statement_detection.py; re-runnable via
   │  manage.py detect_statement_types --all)
   ▼
Categorize transactions                       ← status: review_pending
   │ rule-based first, AI suggestions with confidence scores
   ▼
User reviews (frontend /statements/:id/review)
   │ confirm single rows or bulk; AI Categorize batch; chat assistant
   ▼
Confirm → ExtractedTransaction becomes a FinancialRecord  ← status: completed
```

- Uploads are processed synchronously when fast enough; otherwise the statement stays `processing` and can be **Reprocessed** from the list page.
- Confirmed transactions also feed `CategorizationMemory`, so the model learns the user's naming conventions over time.

## Analytics & Snapshots

- `POST /api/snapshots/generate/` computes a `FinancialSnapshot` for a month: totals, savings rate, liquidity/profitability/solvency ratios, YoY growth, category breakdown, net worth.
- `GET /api/analytics/?start_date=&end_date=` serves the dashboard: snapshot-cached breakdowns/ratios/debt summary with a live-records fallback so the dashboard always renders.
- The dashboard itself calls `/analytics/` (snapshots/ratios) and `/records/` (live series) in parallel.

## Development Workflows

### Backend

```bash
cd backend
source venv/bin/activate

python manage.py runserver                # dev server on :8000
python manage.py test                     # full test suite (throttling auto-disabled)
python manage.py makemigrations finance_api
python manage.py migrate

# Re-run statement type detection (default: only statements typed "other")
python manage.py detect_statement_types [--all] [--dry-run]

# Create a superuser for the Django admin (available at /admin/)
python manage.py createsuperuser
```

### Frontend

```bash
cd frontend
npm run dev        # dev server on :5173 (proxies /api → :8000)
npm run lint       # oxlint
npm run build      # tsc -b && vite build
npm run preview    # serve the production build
```

### Conventions

- Views stay thin; logic goes in `services/`.
- New domains add a module in each of `models/`, `views/`, `serializers/`, `services/` (and an API client + component folder in the frontend).
- URL paths are mirrored exactly between `finance_api/urls.py` and `frontend/src/api/*.ts`.
- Test: extend `finance_api/tests.py` (auth, statements, debts, AI settings/key validation are covered).

## Configuration Reference

All backend config lives in `backend/.env` (loaded by `config/settings.py`; gitignored — never commit it). See the root README for the full table. Highlights:

| Variable | Default | Effect |
|----------|---------|--------|
| `DJANGO_SECRET_KEY` | dev fallback | Session/encryption security — **must** be set and stable in production (changing it loses access to stored AI keys) |
| `GEMINI_API_KEY` | "" | Fallback Gemini key when no per-user key is stored |
| `DB_ENGINE` | `sqlite` | `mysql` switches to MySQL using `DB_NAME/USER/PASSWORD/HOST/PORT` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173, …:5174` | Comma-separated frontend origins |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | 30 / 7 | Token lifetimes |
| `THROTTLE_LOGIN` / `THROTTLE_REGISTER` | `10/min` / `10/hour` | Auth rate limits |
| `DJANGO_DEBUG` | `true` | Set `false` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts Django will serve |
