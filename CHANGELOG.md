# Changelog

All notable changes to this project are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-11-10

v2.1 adds list comparison across stores, promotions and a weekly price scanner. As in v2, every number is computed from the catalog; the compare mode makes no LLM call at all. Details: [docs/API.md](docs/API.md), [docs/CATALOG.md](docs/CATALOG.md).

### Added
- **Compare mode** (frontend): a third tab next to the shopping list and menu modes.
  - Build a list of products with autocomplete over concept and product names in any UI language, with a category filter.
  - Set quantities in reference packs (`2 × 250 g (500 g)`), stores, diets and the split threshold.
  - Results show the recommendation and savings, items no store sells, and each store's total with prices per kg, l or piece and running promotions.
  - The cheapest split comes as a checklist per store.
  - The list is kept in localStorage and can be shared as a `#/list/` link that opens with current prices.
- **`POST /compare`**: prices a list of concepts at each chosen store (fewest whole packs that hold the requested amount, lowest line total) and finds the cheapest split across stores.
  - Stores rank by missing items, then total.
  - The split is recommended only when it saves at least `min_split_savings_eur` (default €3.00).
  - Computed from the catalog only: no OpenAI call, so no rate limit or daily cap.
- **`GET /api/catalog/concepts`**: the concepts sold in a country, with their display name, products' names (for search), stores and reference pack size.
- **Concepts**: every product has a `concept_id`, shared by interchangeable products across stores (same unit and category); 11 of 68 concepts are sold by both Billa and Hofer.
- **`backend/data_src/concepts_at.csv`**: a neutral, brand-free name for every concept in en, uk and de (`Butter`, not `Clever Teebutter`). The build fails on a concept without a name; tests reject names with a store brand.
- **Promotions**: `promo_price_eur` and `promo_valid_until` next to the regular price. In `catalog.json`, `price_eur` is the effective price on the catalog's `price_date` and `regular_price_eur` the shelf price. The running app re-prices by today's date, so an ended promotion falls back to the regular price without a rebuild.
- **Weekly price and promotion scanner** (`python -m scripts.price_scanner.cli`, local only):
  - Reads the stores' product and offer pages with Playwright on a browser profile saved once with `--login` (cookies, captcha, PLZ), or flyer PDFs and screenshots with `--from-files`.
  - An OpenAI model reads the offers via Structured Outputs, matched to the store's product ids.
  - Confident, plausible offers update `catalog_at.csv`; the rest go to `data_src/scanner_review.json` with the reason.
  - Dry run by default; `--last-run --apply` writes what the dry run showed and rebuilds `catalog.json`.
  - Its dependencies are in `backend/requirements-scraper.txt`, not in the app or its Docker image.

### Changed
- Shopping lists and menus are priced with the promo price while a promotion runs.
- The catalog build validates concepts (unit and category per concept, a name for each) and promotions (promo below the regular price, end date not before `price_date`).

## [2.0.1] - 2026-10-19

### Added
- Eval results record the LLM's lines per attempt and the final basket per case (`llm_attempts`, `items`, `trimmed`).

### Fixed
- Vegan products missing the lactose-free tag (9 breads and bakery products were hidden from lactose-free plans); the catalog build now rejects a `vegan` row without `vegetarian` and `lactose_free`.

## [2.0.0] - 2026-10-17

v2 rebuilds the app around one principle: **the LLM chooses, the server computes**. Details: [docs/ROADMAP.md](docs/ROADMAP.md), [docs/API.md](docs/API.md), [backend/evals/report.md](backend/evals/report.md).

### Added
- Grounded price catalog for Austria (Billa, Hofer; reference prices from 2026-10-15), built and validated from `backend/data_src/catalog_at.csv`; `GET /api/catalog/meta` for stores, diet tags and price date.
- Server-side pricing: line totals, per-store subtotals, totals and nutrition computed from the catalog with `Decimal`.
- Structured Outputs with a per-request JSON schema whose product ids are an enum of the request's candidates; unknown ids are rejected.
- Budget trimming: an over-budget plan is cut packs-first, then whole lines, so the total never exceeds the budget; cuts are reported in `trimmed`.
- Menu mode with portions per person converted to packs, and kcal normalization that scales portions into the 1600–3500 kcal per person and day range.
- Deterministic kcal top-up in shopping mode: packs of the food with the most kcal per € are added while the budget allows (`kcal_topped_up` warning).
- `low_kcal` warning in both modes when the kcal floor can't be reached within the budget.
- Repair loop: one retry with a precise error message (missing days, budget overshoot, kcal out of range); small overshoots are trimmed instead.
- Budget-aware candidates: on tight budgets the most expensive calories are not offered.
- Per-IP rate limit and a daily generation cap on `POST /generate`; request deadline and per-call timeout.
- pytest suite with mocked OpenAI, Vitest + Testing Library frontend tests, GitHub Actions CI.
- Offline eval harness (20 fixed scenarios) with JSON results and a Markdown report.
- Deployment: API on Google Cloud Run (europe-west1, key in Secret Manager), frontend on Cloudflare Pages, with deploy and smoke-test scripts.
- Share links: the plan compressed into the URL fragment, opened read-only.
- Security headers and a strict Content-Security-Policy; `/docs` disabled in production.

### Changed
- Backend restructured into the `app/` package with env-driven settings and `AsyncOpenAI`.
- Strict input validation (`Literal` enums, bounded numbers, ≤ 300-char preferences) and generic error responses with machine-readable `code`.
- Frontend: catalog-driven form, budget bar and price date, product names in the UI language, accessibility fixes, mobile layout, plural forms for en/uk/de, weekly budget label in shopping mode.
- API base URL read from `VITE_API_URL`.

### Removed
- LLM-invented prices, totals and nutrition.
- Hardcoded German store list and production API URL; legacy hosting.

### Security
- OpenAI key removed from git history and rotated; separate OpenAI project with a spend limit.

## [1.0.0] - 2025

Diploma version (MSc project, NTU "KhPI"). The LLM generated a complete shopping list or menu, including prices and nutrition, as free-text JSON; React + FastAPI, English/Ukrainian/German, dark theme and local history.
