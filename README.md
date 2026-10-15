# 🛒 ShopSmart AI

> Intelligent shopping list generator powered by OpenAI GPT-4o-mini

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
2. **LLM choice** via OpenAI Structured Outputs: a per-request JSON schema whose product ids are an enum of exactly those candidates (plain strings checked by the server when the enum values in the schema, counted once per place they are used, would exceed `MAX_SCHEMA_ENUM_VALUES`; with the default 500 that is above 100 candidates). The model returns an optional menu whose meals list `ingredient_ids` (first, so it designs the meals before buying for them), `lines: [{product_id, packs 1–20}]`, and notes. No prices.
3. **Completing the list**: in menu mode, every meal ingredient missing from `lines` is added by the server with 1 pack and listed in `auto_added`. The completed plan goes through the checks below.
4. **Checks + one repair**: empty list, missing/wrong-length menu, a total over budget (the repair message states the overshoot in € and names any auto-added ingredients), or, in menu mode, fewer than `MIN_KCAL_PER_PERSON_DAY` kcal per person and day (the message states current vs required) → one retry telling the model what was wrong. Both attempts share the request deadline. If the retry still misses the budget or kcal target, the earlier valid plan is used. Budget per mode: in `shopping` mode the model is asked to spend 85–98% of the budget; in `menu` mode the budget is only a ceiling and the model buys just what the menu needs, with no filler items.
5. **Pricing**: totals from catalog prices (`Decimal`, rounded half-up to cents). If the plan is still over budget, the server trims it: packs first, then whole lines (snacks, beverages, frozen, cleaning, hygiene, then the rest, most expensive first), menu ingredients last. Trimmed lines are listed in `trimmed`.

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

Response to the request above with the test catalog (2 of 4 items shown). The model left the chicken for lunch out of `lines`, so the server added it (`auto_added`); it also picked chips, which were trimmed to fit the €15 budget; the menu ingredients were kept.

```json
{
  "items": [
    {
      "product_id": "at-lidl-milk-1l",
      "name": "Whole milk 3.5%",
      "names": {"en": "Whole milk 3.5%", "uk": "Молоко 3,5%", "de": "Vollmilch 3,5%"},
      "store": "Lidl",
      "category": "dairy",
      "packs": 2,
      "pack_size": 1.0,
      "unit": "l",
      "unit_price": 1.29,
      "line_total": 2.58,
      "nutrition": {"kcal": 1280.0, "protein_g": 68.0, "fat_g": 70.0, "carbs_g": 96.0}
    },
    {
      "product_id": "at-lidl-apples-1kg",
      "name": "Apples",
      "names": {"en": "Apples", "uk": "Яблука", "de": "Äpfel"},
      "store": "Lidl",
      "category": "fruits",
      "packs": 2,
      "pack_size": 1.0,
      "unit": "kg",
      "unit_price": 1.99,
      "line_total": 3.98,
      "nutrition": {"kcal": 1040.0, "protein_g": 6.0, "fat_g": 4.0, "carbs_g": 280.0}
    }
  ],
  "subtotals_by_store": {"Lidl": 12.55, "Penny": 2.29},
  "total": 14.84,
  "budget": 15.0,
  "budget_remaining": 0.16,
  "nutrition_totals": {"kcal": 6370.0, "protein_g": 259.0, "fat_g": 89.0, "carbs_g": 1156.0},
  "kcal_per_person_day": 3185.0,
  "trimmed": [
    {
      "product_id": "at-lidl-potato-chips-175g",
      "name": "Potato chips",
      "names": {"en": "Potato chips", "uk": "Картопляні чипси", "de": "Kartoffelchips"},
      "from_packs": 2,
      "to_packs": 0
    }
  ],
  "auto_added": ["at-lidl-chicken-breast-500g"],
  "menu": [
    {
      "day": "Monday",
      "breakfast": {
        "name": "Milk porridge with apple",
        "description": "Rice cooked in milk, topped with grated apple",
        "ingredient_ids": ["at-lidl-milk-1l", "at-penny-rice-1kg", "at-lidl-apples-1kg"]
      },
      "lunch": {
        "name": "Chicken rice bowl",
        "description": "Pan-fried chicken over rice",
        "ingredient_ids": ["at-lidl-chicken-breast-500g", "at-penny-rice-1kg"]
      },
      "dinner": {
        "name": "Baked apples",
        "description": "Apples baked with a splash of milk",
        "ingredient_ids": ["at-lidl-apples-1kg", "at-lidl-milk-1l"]
      },
      "snack": null
    }
  ],
  "notes": "Rice and apples are the cheapest calories here.",
  "warnings": ["budget_trimmed"],
  "catalog_version": "test-small-2",
  "price_date": "2026-10-01",
  "generated_at": "2026-10-14T21:30:00Z"
}
```

| Field | Meaning |
|---|---|
| `items[].name` / `names` | product name in the request language / in all languages (`en`, `uk`, `de`) from the catalog, so a client can switch language without a new plan |
| `items[].unit_price` / `line_total` | price per pack / for all packs, from the catalog |
| `items[].nutrition` | for all packs; `null` for non-food |
| `subtotals_by_store`, `total`, `budget_remaining` | EUR, 2 decimals; `total` ≤ `budget` always |
| `kcal_per_person_day` | `nutrition_totals.kcal / (family_size × days)`; `days` is 7 in shopping mode. Based on the purchased packs, so an upper bound of the food available, not what the menu's meals actually consume |
| `trimmed` | lines the server cut to fit the budget, with `name` and `names` like `items` (a removed line isn't in `items`); `to_packs: 0` = removed |
| `auto_added` | meal ingredients the model left out of its list; the server added 1 pack each (before any trimming). Always `[]` in shopping mode |
| `menu` | `null` in shopping mode; `ingredient_ids` refer to `items` (an ingredient may be missing if it was trimmed). Meal names and descriptions are written by the model in the request language only; they don't change when a client switches language |
| `warnings` | `low_kcal`: menu mode and `kcal_per_person_day` still below `MIN_KCAL_PER_PERSON_DAY` after the final attempt; `budget_trimmed`: `trimmed` is not empty |
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
MAX_SCHEMA_ENUM_VALUES=500                 # default; above it product ids aren't an enum in the LLM schema
CORS_ORIGINS=http://localhost:3000         # comma-separated; "*" is rejected
RATE_LIMIT=10/minute                       # default; per client IP on POST /generate
DAILY_GENERATE_CAP=200                     # default; POST /generate calls per UTC day
ENVIRONMENT=development                    # development | production
FORWARDED_ALLOW_IPS=127.0.0.1              # read by uvicorn; proxies trusted for X-Forwarded-For
```

Docker Compose sets `CORS_ORIGINS=http://localhost,http://localhost:3000` by default.

`app/data/catalog.json` is an empty placeholder until the real price catalog lands (Phase 2C): the app starts, but every `/generate` returns `unknown_store`. For local development use the test catalog: `CATALOG_PATH=tests/fixtures/catalog_small.json` (made-up prices, Lidl and Penny in AT and DE).

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
```

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
