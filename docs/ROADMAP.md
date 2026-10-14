# ShopSmart AI — Roadmap to MVP v2

Status legend: ⬜ todo · 🟨 in progress · ✅ done

## Audit of v1 (2026-10-14, commit c804c03)

**Works:** TypeScript builds (`tsc` clean). Shopping-list and 1–7 day menu modes, EN/UK/DE, dark theme, localStorage history, Dockerfiles, Railway deploy history.

**Problems, by severity:**

| # | Issue | Where |
|---|---|---|
| 1 | Prices, totals and nutrition are invented by the LLM; budget not enforced server-side | `backend/main.py` |
| 2 | No rate limiting + CORS `*` + public OpenAI-backed endpoint → anyone can burn the API key | `main.py` |
| 3 | Sync `openai.OpenAI` inside `async def` blocks the event loop | `main.py` |
| 4 | JSON parsed by splitting on ``` — no Structured Outputs, no retry | `main.py` |
| 5 | `detail=str(e)` leaks internal errors | `main.py` |
| 6 | `mode` is a free string, `days` unbounded, `preferences` unbounded (prompt-injection / cost surface) | `UserInput` |
| 7 | Prod API URL hardcoded; `VITE_API_URL` ignored | `frontend/src/api.ts` |
| 8 | No tests at all, although README documents `pytest` and `vitest` | repo |
| 9 | `npm run lint` fails — no ESLint config | `frontend/` |
| 10 | No CI | `.github/` |
| 11 | Leftover file `translations_history.txt`; `total_nutrition` in TS types never returned by backend | `frontend/src` |
| 12 | Dev deps mixed into prod `requirements.txt`, `httpx` listed twice, `pydantic-settings` unused, old pins | `backend/` |
| 13 | README inaccuracies: "CORS configured for specific origins", wrong email/GitHub handle, tests section; name spelled "Sytnyk" in package.json/compose/scripts | docs |
| 14 | `docker-compose.yml`: obsolete `version`, unused volume | root |
| 15 | Stores are German only (Lidl/Aldi/Edeka/Rewe/Kaufland); no Austrian chains | `constants.ts` |

## MVP v2 definition

A user opens a live link, picks stores (AT or DE), budget, family size, diet and days, and within ~10 s gets a menu + shopping list where **every price comes from a dated catalog**, the **total is computed by the server** and **never exceeds the budget**. Lists can be shared via link. The repo has tests, CI, an eval report and an honest README with a demo GIF.

**Out of scope for v2:** accounts/auth, live price scraping, payments, mobile app, streaming, server-side storage of shared lists.

---

## Phase 0 — Hygiene (½ day)
- ✅ 0.0 Security: OpenAI key found in early commits (history rewritten); key revoked and rotated, spend cap set, legacy Railway backend stopped.
- ✅ 0.1 Split `requirements.txt` / `requirements-dev.txt`, update pins, add `ruff` config.
- ✅ 0.2 Frontend: ESLint flat config so `npm run lint` passes; delete `translations_history.txt`; `api.ts` reads `VITE_API_URL`.
- ✅ 0.3 Unify name spelling "Sytnik", fix README contact/GitHub, drop compose `version` and unused volume.
- ⬜ 0.4 Add `CLAUDE.md` and this roadmap.

## Phase 1 — Backend restructure + safety (1–2 days)
- ⬜ 1.1 Move to `app/` package layout (see CLAUDE.md); `Settings` via pydantic-settings.
- ⬜ 1.2 `AsyncOpenAI` + Structured Outputs with Pydantic LLM schemas; one repair retry on validation failure. Call: `await client.chat.completions.parse(model=..., messages=..., response_format=Model)` → `choices[0].message.parsed` (verified on openai 3.31.0; `beta.chat.completions` is only an alias).
- ⬜ 1.3 Input hardening: `Literal` modes/languages/stores, bounds, generic error responses.
- ⬜ 1.4 Rate limiting (slowapi, per IP) + CORS from env + request timeout.
- ⬜ 1.5 pytest suite with mocked OpenAI: happy path, invalid input, LLM invalid output → retry → 502.

## Phase 2 — Grounded pricing (2–3 days) — the core of v2
- ⬜ 2.1 `data/catalog.json`: ~150 common products × chains (AT: Hofer, Billa, Spar, Lidl AT; DE: Aldi, Lidl, Rewe, Edeka, Kaufland) with `id, name_{en,uk,de}, category, unit, price, store, kcal_per_unit, diet_tags, price_date`. Prices are manually collected reference prices, labeled with date.
- ⬜ 2.2 `pricing.py`: filter catalog by chosen stores + diet → pass compact candidate list to the LLM; LLM returns `[{product_id, quantity}]` + menu.
- ⬜ 2.3 Server computes line totals, list total, nutrition; if over budget → deterministic trimming (drop/reduce lowest-priority items) or one LLM repair call; final total ≤ budget guaranteed.
- ⬜ 2.4 Reject unknown `product_id`s; tests for budget enforcement and diet filtering.
- ⬜ 2.5 `GET /api/catalog/meta` (stores, countries, price_date) for the UI.

## Phase 3 — Frontend v2 (2 days)
- ⬜ 3.1 Country switch AT/DE → store list from `/api/catalog/meta`.
- ⬜ 3.2 Show "reference prices as of <date>", per-store subtotals, budget bar (used/remaining).
- ⬜ 3.3 Align `types.ts` with new response; remove dead fields.
- ⬜ 3.4 Share link: result compressed into URL fragment (`/l#<payload>`) → read-only "snapshot" view; no backend storage. History stays in localStorage.
- ⬜ 3.5 vitest + Testing Library: form validation, list rendering, budget bar.

## Phase 4 — Quality evidence (1 day)
- ⬜ 4.1 `evals/run.py`: 20 fixed scenarios → metrics: valid output rate, budget adherence, diet violations, avg latency, avg cost. Writes `evals/report.md`.
- ⬜ 4.2 GitHub Actions: backend lint+tests, frontend lint+build+tests on every push/PR.

## Phase 5 — Ship (½–1 day)
- ⬜ 5.1 Deploy: frontend → Cloudflare Pages, backend → Google Cloud Run (EU Tier 1 region, max-instances=1). Env vars/secrets set, health check green, OpenAI hard spend limit + GCP budget alert configured.
- ⬜ 5.2 README rewrite: problem → demo link + GIF → architecture diagram → "LLM chooses, server computes" → eval results → run locally.
- ⬜ 5.3 Tag `v2.0.0` release.

## Later (not MVP)
- Price updates from public sources/scraper with freshness checks.
- Accounts + saved plans server-side.
- Streaming partial results.
- Recipe steps per meal.
- Short share links with server-side storage (Neon Postgres) — URL-encoded snapshots are enough for v2.
- ESLint 9 upgrade (with typescript-eslint 8, react-hooks plugin 5+); Phase 0 kept ESLint 8.57 with flat config.
