# CLAUDE.md — ShopSmart AI

Guidance for Claude Code working in this repository. Read `docs/ROADMAP.md` before starting any task; work only on the task you were given.

## What this is

AI meal-plan and shopping-list generator for Austrian/German supermarkets. Input: stores, budget, family size, diet, language, days. Output: a shopping list (and optionally a 1–7 day menu) that stays within budget.

v2 principle: **the LLM chooses, the server computes.** The model picks products from a price catalog by ID and quantity; prices, totals and budget checks are computed in Python, never trusted from the model.

## Layout (target for v2)

```
backend/
  app/
    main.py            # FastAPI app factory, middleware, routers
    config.py          # pydantic-settings Settings (env-driven)
    api/               # routers: health.py, generate.py, catalog.py
    schemas/           # Pydantic request/response + LLM output schemas
    services/
      llm.py           # AsyncOpenAI wrapper, structured outputs, retries
      planner.py       # prompt building, repair loop
      pricing.py       # catalog lookup, totals, budget enforcement
    data/catalog.json  # product price catalog (seed)
  tests/               # pytest; OpenAI is always mocked
  evals/               # offline eval script + fixed cases
frontend/
  src/ (api/, components/, i18n/, hooks/, types.ts)
```

## Commands

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
pytest -q
ruff check . && ruff format --check .

# frontend
cd frontend && npm ci
npm run dev          # http://localhost:3000
npm run build        # runs tsc
npm run lint
npm run test -- --run

# full stack
docker compose up --build
```

Before saying a task is done: backend `pytest -q` + `ruff check .`, frontend `npm run build` + `npm run lint` + `npm run test -- --run` must pass.

## Code rules

### Backend
- Python 3.11+, type hints everywhere, Pydantic v2.
- Use `AsyncOpenAI`; never call the sync client inside `async def`.
- LLM output must use **Structured Outputs** with a Pydantic model via the SDK's `parse()` helper (`client.chat.completions.parse(..., response_format=Model)` — check the installed `openai` version; don't use `beta.` if it's deprecated there). No string-splitting of ``` fences, no `json.loads` on free text.
- Model name, temperature, max tokens, CORS origins, rate limits come from `Settings`, never hardcoded.
- Enum-like fields are `Literal[...]`; all numeric inputs bounded (`days` 1–7, `family_size` 1–10, `budget` 10–1000, `preferences` ≤ 300 chars).
- Errors: return generic `detail` to clients; log the real exception. Never `detail=str(e)`.
- Never log the API key or full prompts at INFO level.
- Tests mock OpenAI (fixture returning parsed schema objects). No network in tests.

### Frontend
- API base URL only from `import.meta.env.VITE_API_URL`.
- Strict TypeScript; no `any`. Types in `types.ts` mirror backend response schemas exactly.
- All user-visible strings go through i18n (`en`, `uk`, `de`); add keys to all three languages.
- Tailwind only; keep existing dark-mode support working.

### General
- Small, focused changes. Don't refactor outside the task scope; note opportunities in the final summary instead.
- Don't add dependencies without saying why in the summary.
- Keep README in sync when commands, env vars or endpoints change.

## Git

- Conventional commits: `feat(backend): ...`, `fix(frontend): ...`, `refactor:`, `test:`, `chore:`, `docs:`, `ci:`.
- **Do not add `Co-Authored-By` trailers, session links, or any AI attribution to commits or PR descriptions.**
- Author identity: Ivan Sytnik. Don't change git config.
- One logical change per commit. Don't commit `.env`, `node_modules`, `.venv`, `dist`.

## Environment variables

| Var | Where | Example |
|---|---|---|
| `OPENAI_API_KEY` | backend | `sk-...` |
| `OPENAI_MODEL` | backend | `gpt-4o-mini` |
| `CORS_ORIGINS` | backend | `http://localhost:3000,https://shopsmart.example` |
| `RATE_LIMIT` | backend | `10/minute` |
| `ENVIRONMENT` | backend | `development` / `production` |
| `VITE_API_URL` | frontend (build-time) | `http://localhost:8000` |
