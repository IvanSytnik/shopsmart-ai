# CLAUDE.md — ShopSmart AI

Guidance for Claude Code working in this repository. Read `docs/ROADMAP.md` before starting any task; work only on the task you were given.

## What this is

AI meal-plan and shopping-list generator for Austrian/German supermarkets, plus a price comparison of a user's own list across stores. Current release: v2.1.0 (2026-11-10); the catalog has Billa and Hofer (AT) only.

Three modes:
- **Shopping list** (7 days) and **menu** (1–7 days): `POST /generate`. Input: stores, budget, family size, diets, language, days. Output: a list (and menu) that stays within budget.
- **Compare**: `POST /compare`. A list of concepts priced at each chosen store, plus the cheapest split across stores. **No LLM call**, so no `RATE_LIMIT` or `DAILY_GENERATE_CAP`. Keep it that way.

v2 principle: **the LLM chooses, the server computes.** The model picks products from a price catalog by ID and quantity; prices, totals and budget checks are computed in Python, never trusted from the model. Compare goes further: no model at all, deterministic for a given catalog and date.

## Layout

```
backend/
  app/
    main.py              # FastAPI app factory, middleware, routers
    config.py            # pydantic-settings Settings (env-driven)
    api/                 # routers: health, generate (POST /generate), catalog (GET /api/catalog/meta,
                         #   GET /api/catalog/concepts), compare (POST /compare)
    schemas/             # requests, responses, llm (LLM output), catalog (Product, Concept, Catalog),
                         #   compare (CompareRequest/Response, ConceptSummary)
    services/
      llm.py             # AsyncOpenAI wrapper, structured outputs
      planner.py         # prompt building, repair loop
      pricing.py         # totals, budget trimming, kcal top-up
      portions.py        # menu portions -> packs, eaten kcal, portion scaling
      catalog.py         # ProductCatalog: lookups at today's prices (ended promotions -> regular price)
      comparison.py      # compare(): pack matching, rankings, split basket, recommendation
      limits.py          # rate limit, daily cap
    data/catalog.json    # GENERATED from data_src/ by scripts/build_catalog.py; never edit by hand
  data_src/
    catalog_at.csv       # one row per product (regular price, optional promo_price_eur + promo_valid_until)
    concepts_at.csv      # concept_id,name_en,name_uk,name_de: brand-free name per concept
  scripts/
    build_catalog.py     # both CSVs -> catalog.json, validated; --check fails if the JSON is stale
    price_scanner/       # weekly price/promo scanner, LOCAL ONLY: cli, browser, adapters/ (billa,
                         #   hofer), extractors/llm_extractor.py, updater.py (checks, review file)
  requirements-scraper.txt  # scanner-only deps (Playwright, pypdfium2, Pillow)
  tests/                 # pytest; OpenAI mocked, sockets blocked (conftest.py)
    fixtures/catalog_small.json  # made-up catalog (Lidl, Penny) for pipeline tests
    fixtures/catalog_at.csv      # FROZEN copy of catalog_at.csv as of 2026-10-15, no promotions
  evals/                 # offline eval runner (real OpenAI), fixed cases, reports
frontend/
  src/
    api.ts, types.ts     # API client; types mirror backend schemas (incl. compare)
    components/          # form, results/, compare/ (CompareView, ConceptSearch, CompareResults,
                         #   StoreRankings, SplitChecklist, MatchedItem)
    hooks/               # useCatalogMeta, useConcepts
    share.ts             # share links: #/plan/<data> (whole plan), #/list/<data> (compare list)
    compareList.ts       # compare list in localStorage, validation of stored/shared lists
    translations.ts      # en/uk/de strings
    __tests__/, test/    # Vitest + Testing Library; test/fixtures.ts
deploy/                  # Cloud Run scripts, smoke.sh, deployment guide
docs/                    # API.md, CATALOG.md (catalog + scanner guide), ROADMAP.md, media
```

## Commands

```bash
# backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
pytest -q                                   # 529 tests at v2.1.0
ruff check . && ruff format --check .
python scripts/build_catalog.py             # rebuild app/data/catalog.json after editing data_src/
python scripts/build_catalog.py --check     # CI: fails if catalog.json doesn't match the CSVs

# frontend
cd frontend && npm ci
npm run dev          # http://localhost:3000
npm run build        # runs tsc
npm run lint
npm run test -- --run                       # 146 tests at v2.1.0

# full stack
docker compose up --build

# deployed stack (one real OpenAI call): health, meta, concepts, /compare, /generate, CORS, routes
./deploy/smoke.sh <api_url> <frontend_url>
```

Before saying a task is done, everything CI runs must pass: backend `pytest -q` + `ruff check .` + `ruff format --check .` + `python scripts/build_catalog.py --check`, frontend `npm run lint` + `npm run build` + `npm run test -- --run`. If test counts change, update them in README.md (Tests).

## Code rules

### Backend
- Python 3.11+, type hints everywhere, Pydantic v2.
- Use `AsyncOpenAI`; never call the sync client inside `async def`.
- LLM output must use **Structured Outputs** with a Pydantic model via the SDK's `parse()` helper (`client.chat.completions.parse(..., response_format=Model)` — check the installed `openai` version; don't use `beta.` if it's deprecated there). No string-splitting of ``` fences, no `json.loads` on free text.
- Model name, temperature, max tokens, CORS origins, rate limits come from `Settings`, never hardcoded.
- Enum-like fields are `Literal[...]`; all numeric inputs bounded (`days` 1–7, `family_size` 1–10, `budget` 10–1000, `preferences` ≤ 300 chars; compare: ≤ 50 items, `quantity` 1–50, ≤ 5 stores, `min_split_savings_eur` 0–1000).
- Money is `Decimal` in Python, a number rounded to cents in JSON.
- Prices come from `ProductCatalog` lookups (`get`, `candidates`, `products_for_concept`), which re-price by today's date. Don't read `catalog.catalog.products` for prices: it holds prices as of the catalog's `price_date`.
- Errors: return generic `detail` to clients; log the real exception. Never `detail=str(e)`.
- Never log the API key or full prompts at INFO level.
- Tests mock OpenAI (fixture returning parsed schema objects). No network in tests.

### Catalog
- Edit `data_src/catalog_at.csv` / `concepts_at.csv`, then run `build_catalog.py`; commit the CSVs and `catalog.json` together. Keep product ids stable.
- A new `concept_id` needs a brand-free name in `concepts_at.csv` (the build fails without one; tests reject store brands). Products sharing a concept need the same unit and category. If the set of concepts sold by both stores changes, update `SHARED_CONCEPTS` in `tests/test_catalog_at.py`.
- `data_src/catalog_at.csv` changes with every weekly price scan. Tests that depend on prices, dates or promotions must use `tests/fixtures/catalog_at.csv` (`FROZEN_CATALOG_AT` in conftest) or `catalog_small.json`, never the live CSV. Don't update the frozen fixture to follow a scan.
- Details: `docs/CATALOG.md`.

### Price scanner (`scripts/price_scanner/`)
- Local only: its dependencies stay in `requirements-scraper.txt`, never in `requirements.txt` or the Docker image; nothing in `app/` may import it.
- Don't run a real scan (browser + OpenAI costs, needs the user's `--login` profile) unless asked. Its tests use a fake browser session and a mocked OpenAI client.
- Never commit `backend/.browser_profile/`, `backend/.scanner/` or `data_src/scanner_review.json` (git-ignored).
- The updater's checks (confidence ≥ 0.85, regular price change ≤ 50 %, promotion started and not ended, review kinds such as `page_mismatch`, `dead_product_url`) are documented in `docs/CATALOG.md`; keep both in sync.

### Frontend
- API base URL only from `import.meta.env.VITE_API_URL`.
- Strict TypeScript; no `any`. Types in `types.ts` mirror backend response schemas exactly.
- All user-visible strings go through i18n (`en`, `uk`, `de`); add keys to all three languages.
- Tailwind only; keep existing dark-mode support working.
- A compare share link (`#/list/`) carries only the list (concept ids, quantities, stores, diets, threshold, country), never prices; plan links (`#/plan/`) carry the whole priced plan. Both payloads carry a version `v` (`share.ts`) that is checked when a link is opened.

### General
- Small, focused changes. Don't refactor outside the task scope; note opportunities in the final summary instead.
- Don't add dependencies without saying why in the summary.
- Keep README (and `docs/API.md`, `docs/CATALOG.md`, `deploy/README.md` where relevant) in sync when commands, env vars, endpoints or checks change.

## Git

- Conventional commits: `feat(backend): ...`, `fix(frontend): ...`, `refactor:`, `test:`, `chore:`, `docs:`, `ci:`.
- **Do not add `Co-Authored-By` trailers, session links, or any AI attribution to commits or PR descriptions.**
- Author identity: Ivan Sytnik. Don't change git config.
- One logical change per commit. Don't commit `.env`, `node_modules`, `.venv`, `dist`.

## Environment variables

| Var | Where | Example |
|---|---|---|
| `OPENAI_API_KEY` | backend, scanner | `sk-...` |
| `OPENAI_MODEL` | backend | `gpt-4o-mini` |
| `CORS_ORIGINS` | backend | `http://localhost:3000,https://shopsmart.example` |
| `RATE_LIMIT` | backend (`POST /generate` only) | `10/minute` |
| `DAILY_GENERATE_CAP` | backend (`POST /generate` only) | `200` |
| `ENVIRONMENT` | backend | `development` / `production` |
| `CATALOG_PATH` | backend | `app/data/catalog.json` |
| `SCANNER_MODEL`, `SCANNER_*` | scanner only (ignored by the app) | `gpt-4o-mini` |
| `VITE_API_URL` | frontend (build-time) | `http://localhost:8000` |

Full list with defaults: README.md (Backend environment variables) and `backend/.env.example`.
