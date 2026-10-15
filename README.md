# 🛒 ShopSmart AI

> Intelligent shopping list generator powered by OpenAI GPT-4o-mini

[![CI](https://github.com/IvanSytnik/shopsmart-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/IvanSytnik/shopsmart-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0-3178c6.svg)](https://www.typescriptlang.org/)

## 📋 About

ShopSmart AI is a web application that generates optimized weekly shopping lists using artificial intelligence. The application analyzes your budget, dietary preferences, and selected supermarkets to create personalized shopping lists with price estimates.

**Author:** Ivan Sytnik (КН-М524)  
**Supervisor:** Kharchenko A.O.  
**Institution:** NTU "KhPI" - 2025

## ✨ Features

- 🏪 **Multi-store support** - Austria or Germany; stores come from the price catalog (`GET /api/catalog/meta`)
- 💰 **Budget optimization** - AI stays within your budget
- 🥗 **Dietary preferences** - Vegetarian, vegan, gluten-free, etc.
- 👨‍👩‍👧‍👦 **Family size scaling** - Portions adjusted for 1-5+ people
- 📊 **Smart categorization** - Items organized by store and category, with per-store subtotals and a budget bar
- ⚠️ **Honest results** - Notices when products were trimmed to fit the budget or a menu is short on food
- ✅ **Progress tracking** - Check off items as you shop
- 📋 **Export options** - Copy to clipboard or print

## 🛠 Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - High-performance web framework
- **Pydantic** - Data validation
- **OpenAI API** - GPT-4o-mini integration
- **Uvicorn** - ASGI server

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Nginx** - Reverse proxy

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- OpenAI API key

### 1. Clone the repository

```bash
git clone https://github.com/IvanSytnik/shopsmart-ai.git
cd shopsmart-ai
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (runtime + dev tooling)
pip install -r requirements.txt -r requirements-dev.txt

# Lint
ruff check .

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional)
cp .env.example .env.local

# Run development server
npm run dev

# Tests (vitest + Testing Library, fetch is mocked)
npm run test -- --run
```

### 4. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=sk-your-key-here

# Build and start containers
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

Access the application at http://localhost

### Individual Containers

```bash
# Backend
cd backend
docker build -t shopsmart-backend .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-xxx shopsmart-backend

# Frontend
cd frontend
docker build --build-arg VITE_API_URL=http://localhost:8000 -t shopsmart-frontend .
docker run -p 80:80 shopsmart-frontend
```

## 📖 API Documentation

### Generate a plan

The model only **chooses** products from the price catalog (by id) and how many packs of each; every price, total and nutrition value is **computed by the server** from the catalog, and the total never exceeds the budget.

```http
POST /generate
Content-Type: application/json

{
  "country": "AT",
  "supermarkets": ["Lidl", "Penny"],
  "budget": 15,
  "family_size": 2,
  "diets": [],
  "preferences": "no pork",
  "language": "en",
  "mode": "menu",
  "days": 1
}
```

| Field | Rules |
|---|---|
| `country` | `AT` or `DE` (default `AT`) |
| `supermarkets` | 1–5 unique store names; each must exist in the catalog for `country` (else `422 unknown_store`; see `GET /api/catalog/meta`) |
| `budget` | 10–1000 (EUR) |
| `family_size` | 1–10 (default 2) |
| `diets` | unique values of `vegetarian`, `vegan`, `gluten_free`, `lactose_free` (default `[]`); food must carry every chosen tag, non-food (cleaning, hygiene) is always allowed |
| `preferences` | ≤ 300 chars after trimming; passed to the model as quoted data, never as instructions |
| `language` | `en`, `uk`, `de` (default `en`): product names, meals and notes |
| `mode` | `shopping` or `menu` (default `shopping`) |
| `days` | 1–7 (default 7), used only for `menu`; shopping lists cover 7 days |

How a plan is made:

1. **Candidates**: catalog products for `country`, `supermarkets` and `diets`. Fewer than 12 food products → `422 not_enough_products`.
   **Tight budgets**: below `TIGHT_BUDGET_PER_PERSON_DAY` (default €7) per person and day (budget / (family_size × days), 7 days in shopping mode), food with a cost per 1000 kcal above the 80th percentile is not offered, keeping at least 12 food products (the cheapest). Vegetables and fruit are exempt (they are chosen for nutrition, not calories) and the percentile is computed over the other food only. Every candidate line in the prompt shows its €/1000 kcal, and the prompt states the budget per person and day.
2. **LLM choice** via OpenAI Structured Outputs: a per-request JSON schema whose product ids are an enum of exactly those candidates (plain strings checked by the server when the enum values in the schema, counted once per place they are used, would exceed `MAX_SCHEMA_ENUM_VALUES`; with the default 500 that is above 500 candidates in shopping mode and above 125 in menu mode, where the ids appear in each of the 4 meals). No prices, no totals from the model.
   - `shopping`: `lines: [{product_id, packs 1–20}]` and notes.
   - `menu`: only dishes (food candidates only). Each meal lists `ingredients: [{product_id, amount_per_person}]`, the amount one person eats in that meal in the product's `portion_unit`: `g`, `ml`, `pcs`, or `pack` = a fraction of one whole pack in steps of 0.25 (e.g. 0.5 of a frozen pizza). Allowed: 5–800 g or ml, 1–6 pcs, 0.25–2 packs; a g/ml portion of 2 or less is read as packs (× pack size, e.g. 1 → 500 g of chicken); the server then clamps a portion outside this range to the nearest bound instead of asking for a repair. The catalog's optional `portion_unit` defaults from `unit` (kg → g, l → ml, pcs → pcs, pack → pack); `pack` is allowed for any unit. The prompt gives typical portions and each candidate's energy per portion unit.
3. **Quantities (menu mode)**: per product, required = Σ `amount_per_person` × `family_size` over all meals; packs = ⌈required / pack size⌉ (at least 1). The model never chooses pack counts in menu mode.
   **kcal normalization**: if the portions give less than `MIN_KCAL_PER_PERSON_DAY` per person and day, all portions are scaled up by min / kcal × 1.05 (at most × 1.6); above `MAX_KCAL_PER_PERSON_DAY` they are scaled down by max / kcal × 0.95. Scaled portions are rounded (g/ml to 5, pcs to 1) and clamped to their range, then the packs are recomputed. Only a menu still outside the range after this goes to the repair step. The prompt also asks for about 450/650/650/250 kcal per person for breakfast/lunch/dinner/snack.
4. **Checks + one repair**: empty list, a menu with fewer days than requested (extra days are dropped without a repair), meals without ingredients, a total more than `TRIM_TOLERANCE` (default 10%) over budget (the repair message states the overshoot in €; in menu mode it also names the 3 most expensive ingredients; a smaller overshoot is not repaired but trimmed in step 5), or, in menu mode, eaten kcal per person and day below `MIN_KCAL_PER_PERSON_DAY` or above `MAX_KCAL_PER_PERSON_DAY` (the message states current vs limit) → one retry telling the model what was wrong. Both attempts share the request deadline. If the retry still misses the budget or kcal range, the earlier valid plan is used. Budget per mode: in `shopping` mode the model is asked to spend 85–98% of the budget; in `menu` mode the budget is only a ceiling and nothing is bought besides what the menu uses.
5. **Pricing**: totals from catalog prices (`Decimal`, rounded half-up to cents). If the plan is still over budget, the server trims it: packs first, then whole lines (snacks, beverages, frozen, cleaning, hygiene, then the rest, most expensive first); in menu mode every line is a menu ingredient, so packs are reduced before any ingredient is removed. Trimmed lines are listed in `trimmed`.

Errors are JSON `{"detail": "<generic text>", "code": "<machine code>"}`; clients should branch on `code`. A `validation_error` also has `errors: [{loc, msg}]`.

| Status | `code` | `detail` | When |
|---|---|---|---|
| `422` | `validation_error` | `Invalid request` | invalid input |
| `422` | `unknown_store` | `Unknown store for the selected country` | a store isn't in the catalog for `country` |
| `422` | `not_enough_products` | `Not enough products for these stores and diets` | fewer than 12 food candidates |
| `429` | `rate_limited` | `Too many requests, please try again later` | over `RATE_LIMIT` for this client IP |
| `502` | `generation_failed` | `Failed to generate plan` | model output still unusable after the repair retry |
| `503` | `ai_unavailable` | `AI service unavailable` | OpenAI API error |
| `503` | `daily_limit` | `Daily limit reached, try tomorrow` | `DAILY_GENERATE_CAP` reached for the current UTC day |
| `504` | `ai_timeout` | `AI service timed out` | OpenAI request timed out, or `REQUEST_DEADLINE_S` passed (the repair retry is skipped when less than `REPAIR_MIN_REMAINING_S` is left; an over-budget plan is then trimmed instead) |
| `500` | `generation_failed` | `Failed to generate plan` | anything else |

The `422 unknown_store` / `not_enough_products` checks run before the daily cap, so they don't use it up.

### Response

Response to the request above with the test catalog (2 of 5 items shown). The menu needs 200 g of chips for 2 people, so the server bought 2 × 175 g; that was over the €15 budget, so it was trimmed to 1 pack. `kcal_per_person_day` is what the menu's portions provide.

```json
{
  "items": [
    {
      "product_id": "at-lidl-milk-1l",
      "name": "Whole milk 3.5%",
      "names": {"en": "Whole milk 3.5%", "uk": "Молоко 3,5%", "de": "Vollmilch 3,5%"},
      "store": "Lidl",
      "category": "dairy",
      "packs": 1,
      "pack_size": 1.0,
      "unit": "l",
      "portion_unit": "ml",
      "unit_price": 1.29,
      "line_total": 1.29,
      "nutrition": {"kcal": 640.0, "protein_g": 34.0, "fat_g": 35.0, "carbs_g": 48.0}
    },
    {
      "product_id": "at-lidl-potato-chips-175g",
      "name": "Potato chips",
      "names": {"en": "Potato chips", "uk": "Картопляні чипси", "de": "Kartoffelchips"},
      "store": "Lidl",
      "category": "snacks",
      "packs": 1,
      "pack_size": 0.175,
      "unit": "kg",
      "portion_unit": "g",
      "unit_price": 1.79,
      "line_total": 1.79,
      "nutrition": {"kcal": 940.0, "protein_g": 11.0, "fat_g": 60.0, "carbs_g": 90.0}
    }
  ],
  "subtotals_by_store": {"Lidl": 11.06, "Penny": 2.29},
  "total": 13.35,
  "budget": 15.0,
  "budget_remaining": 1.65,
  "nutrition_totals": {"kcal": 6150.0, "protein_g": 233.0, "fat_g": 112.0, "carbs_g": 1058.0},
  "kcal_per_person_day": 1601.0,
  "kcal_basis": "menu",
  "trimmed": [
    {
      "product_id": "at-lidl-potato-chips-175g",
      "name": "Potato chips",
      "names": {"en": "Potato chips", "uk": "Картопляні чипси", "de": "Kartoffelchips"},
      "from_packs": 2,
      "to_packs": 1
    }
  ],
  "menu": [
    {
      "day": "Monday",
      "breakfast": {
        "name": "Milk porridge with apple",
        "description": "Rice cooked in milk, topped with grated apple",
        "ingredients": [
          {"product_id": "at-lidl-milk-1l", "amount_per_person": 250},
          {"product_id": "at-penny-rice-1kg", "amount_per_person": 60},
          {"product_id": "at-lidl-apples-1kg", "amount_per_person": 100}
        ]
      },
      "lunch": {
        "name": "Chicken rice bowl",
        "description": "Pan-fried chicken over rice",
        "ingredients": [
          {"product_id": "at-lidl-chicken-breast-500g", "amount_per_person": 150},
          {"product_id": "at-penny-rice-1kg", "amount_per_person": 100}
        ]
      },
      "dinner": {
        "name": "Baked apples",
        "description": "Apples baked with a splash of milk",
        "ingredients": [
          {"product_id": "at-lidl-apples-1kg", "amount_per_person": 250},
          {"product_id": "at-lidl-milk-1l", "amount_per_person": 100}
        ]
      },
      "snack": {
        "name": "Chips",
        "description": "A small bowl",
        "ingredients": [
          {"product_id": "at-lidl-potato-chips-175g", "amount_per_person": 100}
        ]
      }
    }
  ],
  "notes": "Rice and apples are the cheapest calories here.",
  "warnings": ["budget_trimmed"],
  "catalog_version": "test-small-2",
  "price_date": "2026-10-01",
  "generated_at": "2026-10-15T10:30:00Z"
}
```

| Field | Meaning |
|---|---|
| `items[].name` / `names` | product name in the request language / in all languages (`en`, `uk`, `de`) from the catalog, so a client can switch language without a new plan |
| `items[].portion_unit` | what menu portions of this product are counted in: `g`, `ml`, `pcs` or `pack` (a fraction of one pack) |
| `items[].unit_price` / `line_total` | price per pack / for all packs, from the catalog |
| `items[].nutrition` | for all packs; `null` for non-food |
| `subtotals_by_store`, `total`, `budget_remaining` | EUR, 2 decimals; `total` ≤ `budget` always |
| `kcal_per_person_day`, `kcal_basis` | kcal / (`family_size` × days). `kcal_basis: "menu"` (menu mode): what the menu's portions provide, counting only what is bought after trimming. `kcal_basis: "purchased"` (shopping mode, 7 days): `nutrition_totals.kcal` of the purchased packs, an upper bound |
| `trimmed` | lines the server cut to fit the budget, with `name` and `names` like `items` (a removed line isn't in `items`); `to_packs: 0` = removed |
| `menu` | `null` in shopping mode. `ingredients[].product_id` refers to `items` (an ingredient may be missing if it was trimmed); `amount_per_person` is in the item's `portion_unit`. Meal names and descriptions are written by the model in the request language only; they don't change when a client switches language |
| `warnings` | `low_kcal`: menu mode and `kcal_per_person_day` still below `MIN_KCAL_PER_PERSON_DAY` after the final attempt and any trimming; `budget_trimmed`: `trimmed` is not empty |
| `catalog_version`, `price_date` | which reference prices were used |

### Catalog metadata

```http
GET /api/catalog/meta
```

```json
{
  "catalog_version": "test-small-2",
  "price_date": "2026-10-01",
  "countries": {"AT": ["Lidl", "Penny"], "DE": ["Lidl", "Penny"]},
  "diet_tags": ["vegetarian", "vegan", "gluten_free", "lactose_free"],
  "categories": ["vegetables", "fruits", "meat", "fish", "dairy", "bread", "beverages", "snacks", "frozen", "pantry", "cleaning", "hygiene", "other"]
}
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/api/catalog/meta` | Stores per country, diet tags, categories, price date |
| POST | `/generate` | Generate a shopping list or menu |

## 📁 Project Structure

```
shopsmart-ai/
├── backend/
│   ├── app/
│   │   ├── main.py          # App factory (create_app), middleware, routers
│   │   ├── config.py        # Settings (env-driven, pydantic-settings)
│   │   ├── api/             # Routers: health, generate; dependencies
│   │   ├── schemas/         # Request, response and LLM output models
│   │   └── services/        # OpenAI client, prompts + repair loop, rate limit/daily cap
│   ├── requirements.txt     # Python runtime dependencies
│   ├── requirements-dev.txt # Test + lint tooling
│   ├── tests/               # pytest suite (mocked OpenAI)
│   ├── pyproject.toml       # ruff + pytest config
│   ├── Dockerfile          # Backend container
│   └── .env.example        # Environment template
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── ShopForm.tsx      # catalog-driven form (country, stores, diets)
│   │   │   ├── results/          # summary, warnings, export, results container
│   │   │   ├── ShoppingList.tsx  # items grouped by store
│   │   │   ├── MealPlan.tsx      # menu with ingredients resolved from items
│   │   │   ├── History.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── ErrorBanner.tsx   # error code -> translated message
│   │   ├── hooks/          # useCatalogMeta
│   │   ├── App.tsx         # Main component
│   │   ├── api.ts          # API client (typed ApiError with `code`)
│   │   ├── history.ts      # localStorage history ("shopsmart-history-v2")
│   │   ├── types.ts        # mirrors backend schemas
│   │   ├── constants.ts    # Constants
│   │   └── index.css       # Global styles
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile          # Frontend container
├── docker-compose.yml      # Container orchestration
└── README.md
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
OPENAI_API_KEY=sk-your-api-key            # required
OPENAI_MODEL=gpt-4o-mini                   # default
OPENAI_TEMPERATURE=0.7                     # default
OPENAI_MAX_TOKENS=4000                     # default
OPENAI_TIMEOUT_S=25                        # default; per OpenAI request
OPENAI_MAX_RETRIES=0                       # default; SDK retries on connection/5xx errors
REQUEST_DEADLINE_S=55                      # default; total time for one POST /generate
REPAIR_MIN_REMAINING_S=20                  # default; skip the repair retry if less is left
CATALOG_PATH=app/data/catalog.json         # default; price catalog, validated at startup
MIN_KCAL_PER_PERSON_DAY=1600               # default; menu mode repairs plans below this
MAX_KCAL_PER_PERSON_DAY=3500               # default; menu mode repairs portions above this
TIGHT_BUDGET_PER_PERSON_DAY=7.0            # default; below it costly calories aren't offered (0 = off)
TRIM_TOLERANCE=0.10                        # default; up to 10% over budget is trimmed, not repaired
MAX_SCHEMA_ENUM_VALUES=500                 # default; above it product ids aren't an enum in the LLM schema
CORS_ORIGINS=http://localhost:3000         # comma-separated; "*" is rejected
RATE_LIMIT=10/minute                       # default; per client IP on POST /generate
DAILY_GENERATE_CAP=200                     # default; POST /generate calls per UTC day
ENVIRONMENT=development                    # development | production
FORWARDED_ALLOW_IPS=127.0.0.1              # read by uvicorn; proxies trusted for X-Forwarded-For
```

Docker Compose sets `CORS_ORIGINS=http://localhost,http://localhost:3000` by default.

#### Price catalog

`app/data/catalog.json` is generated from the human-editable source `backend/data_src/catalog_at.csv` (Austria; currently Billa and Hofer, see [docs/CATALOG.md](docs/CATALOG.md) for sources and the disclaimer). Don't edit the JSON by hand:

```bash
cd backend
python scripts/build_catalog.py          # validate the CSV and write app/data/catalog.json
python scripts/build_catalog.py --check  # validate, and fail if catalog.json is out of date (CI)
```

The script validates every row with the app's schema, converts nutrition from per 100 g/ml to per pack, fails on any error and prints counts per store, category and diet. Tests use the separate made-up catalog `tests/fixtures/catalog_small.json` (Lidl and Penny in AT and DE), which also works for local development: `CATALOG_PATH=tests/fixtures/catalog_small.json`.

`RATE_LIMIT` and `DAILY_GENERATE_CAP` are kept in memory and are **per process**: with several workers or instances the effective limits multiply, and counters reset on restart. That is fine for the single-instance deployment. Behind a reverse proxy, set `FORWARDED_ALLOW_IPS` to the proxy's address (or `*` if the container is reachable only through the proxy) so the rate limit uses the real client IP; otherwise all clients share the proxy's limit.

#### Frontend (.env.local)
```env
VITE_API_URL=http://localhost:8000
```

`VITE_API_URL` is read at build time. `npm run dev` falls back to `http://localhost:8000` when it is unset; production builds (including the Docker image, via the `VITE_API_URL` build arg, default `http://localhost:8000` in Compose) must set it.

## 🧪 Testing

```bash
cd backend
pytest -q                         # OpenAI is mocked; tests never touch the network
ruff check . && ruff format --check .
python scripts/build_catalog.py --check   # catalog.json matches data_src/catalog_at.csv

cd frontend
npm run lint && npm run build && npm run test -- --run
```

CI (`.github/workflows/ci.yml`) runs exactly these on every push and pull request to `main`; it needs no secrets.

### Offline evals (real OpenAI calls, not in CI)

```bash
cd backend
.venv/bin/python -m evals.run                # 20 scenarios from evals/cases.yaml
.venv/bin/python -m evals.run --cases 2      # only the first 2
.venv/bin/python -m evals.run --repeat 3     # every scenario 3 times
```

The scenarios cover shopping and menu mode, 1/3/7 days, households of 1–5, budgets €15–150, every diet, one and both stores, en/de/uk and two deliberately tight budgets. The runner calls the planner in-process (not via HTTP), one request at a time, with `OPENAI_API_KEY` from the environment or `backend/.env`, and the real catalog. A full run makes 20–40 OpenAI calls.

It writes `evals/results/<timestamp>.json` (every run) and `evals/report.md`:
- **summary:** valid output rate, first-attempt acceptance and repair rate per mode, budget adherence, diet violations, kcal-in-range rate for menus, p50/p95 latency, average cost per request;
- **per-case table:** status, attempts, candidates dropped on a tight budget, scaling, trimming, total vs budget, €/1000 kcal of the final plan, kcal, tokens and cost.

The exit code is 1 if any plan is over budget or contains a product that breaks a requested diet. Cost uses the gpt-4o-mini price in `evals/run.py` (`PRICES_PER_M_TOKENS`).

## 📊 Performance

- **API Response Time:** 3-8 seconds (GPT-4o-mini)
- **Typical Request Size:** ~2KB
- **Typical Response Size:** ~5KB
- **Concurrent Users:** 100+ (with proper scaling)

## 🔒 Security

- Input validation with Pydantic (enums, bounds, length limits)
- CORS restricted to `CORS_ORIGINS`
- Per-IP rate limit and a daily call cap on `POST /generate`
- Generic error messages to clients; details are logged server-side only
- No sensitive data stored

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- German supermarket pricing research
- NTU "KhPI" Department of Project Management in IT

## 📞 Contact

**Ivan Sytnik**
- Email: ivan.sytnik02@gmail.com
- GitHub: [@IvanSytnik](https://github.com/IvanSytnik)

---

Made with ❤️ at NTU "KhPI" | 2025
