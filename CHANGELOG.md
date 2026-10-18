# Changelog

All notable changes to this project are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Vegan products missing the lactose-free tag.

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
