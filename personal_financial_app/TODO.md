# TODO — Pending issues

Working checklist of known bugs and improvements. Check items off as they are
solved, and add notes/PR links under each one.

## 🐞 Bugs

### 1. Dashboard: totals for income and spending are wrong
- [ ] Reproduce: open the dashboard with real statement data loaded
- [ ] Confirm expected vs. actual numbers (write both down here)
- [ ] Check the backend aggregation (which endpoint feeds the totals?)
- [ ] Check sign convention: are expenses stored negative or positive?
- [ ] Check currency handling — totals must not mix currencies
- [ ] Check date range / period filter used by the query
- [ ] Add a regression test for the totals calculation

Notes:

---

### 2. Movements: stale data and HTTP 500
- [ ] Reproduce the 500 and capture the full traceback (backend logs)
- [ ] Identify the failing endpoint and view/serializer
- [ ] Check for pending or conflicting migrations (there are unapplied ones in
      `backend/finance_api/migrations/` — 0013, 0023 merge, 0024 drop ghost columns)
- [ ] Verify the DB schema matches the models (`makemigrations --check`)
- [ ] Fix the 500
- [ ] Verify the list refreshes after importing a new statement (cache /
      query invalidation on the frontend)
- [ ] Add a test covering the endpoint

Notes:

---

### 3. Division by zero when the dashboard retrieves information
- [ ] Locate the exact division (percentage? average? ratio vs. total?)
- [ ] Reproduce with the empty/zero case (no statements, zero income, one month)
- [ ] Guard the denominator and decide the fallback value (0, null, "—")
- [ ] Make sure the UI renders that fallback nicely
- [ ] Add a test with zero/empty data
- [ ] Check whether this is the same root cause as item 1

Notes:

---

## ⚙️ Improvements

### 4. Connect an API key to speed up the review process
- [ ] Define the goal: what should be automated (statement parsing? categorising
      transactions? code review?)
- [ ] Choose the provider/model
- [ ] Store the key safely — environment variable, never committed
- [ ] Add the key to `.env.example` (name only, no value) and document it
- [ ] Implement the integration behind a service/module
- [ ] Handle failures: rate limits, timeouts, missing key
- [ ] Document usage in the README / DOCUMENTATION.md

Notes:

---

## Suggested order

1. Item 2 (500 blocks everything downstream, and migrations may be the cause)
2. Item 3 (crash on the dashboard)
3. Item 1 (wrong numbers — likely related to 3)
4. Item 4 (improvement, no rush)
