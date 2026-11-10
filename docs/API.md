# API reference

Backend endpoints, the generation pipeline step by step, errors and the response format. Overview: [README](../README.md).

## Generate a plan

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
6. **kcal top-up (shopping mode)**: if the purchased food is below `MIN_KCAL_PER_PERSON_DAY` per person over 7 days, the server adds one pack at a time while the budget allows: the food with the most kcal per € among the list's products and the other candidates (same stores and diets); a product already in the list wins instead if it has at least `TOP_UP_IN_LIST_MIN_RATIO` (default 0.7) of that kcal per €. Beverages, snacks, `other` and non-food are never added, nor are trimmed products; at most `TOP_UP_MAX_PACKS_PER_PRODUCT` (default 3) packs are added per product, and no product may exceed `TOP_UP_MAX_KCAL_SHARE` (default 35%) of the target kcal (`MIN_KCAL_PER_PERSON_DAY` × people × 7). Deterministic, no LLM call; reported as the `kcal_topped_up` warning.

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

## Response

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
| `warnings` | `low_kcal`: `kcal_per_person_day` still below `MIN_KCAL_PER_PERSON_DAY` (menu: after the final attempt and any trimming; shopping: after the kcal top-up); `budget_trimmed`: `trimmed` is not empty; `kcal_topped_up`: shopping mode, the server added packs to reach the kcal floor (included in `items` and totals) |
| `catalog_version`, `price_date` | which reference prices were used |

## Catalog metadata

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

## Concepts

```http
GET /api/catalog/concepts?country=AT
```

Every concept sold in `country` (default `AT`), sorted by id, for the compare form's autocomplete. `name` is the concept's own name, without store brands, to display; `names` are the names of its products in the country (catalog order, no repeats), worth searching too since they carry brands and variants. `reference_pack_size` is what `quantity: 1` means in `POST /compare`: the concept's smallest pack in the country, in `unit`.

```json
{
  "country": "AT",
  "concepts": [
    {
      "concept_id": "yogurt_natural",
      "name": {"en": "Natural yogurt", "uk": "Натуральний йогурт", "de": "Naturjoghurt"},
      "names": [
        {"en": "Natural yogurt 3.6%", "uk": "Натуральний йогурт 3,6%", "de": "Naturjoghurt 3,6% Fett"},
        {"en": "Natural yogurt 3.6%", "uk": "Натуральний йогурт 3,6%", "de": "Clever Joghurt Natur 3,6%"}
      ],
      "category": "dairy",
      "unit": "kg",
      "stores": ["Billa", "Hofer"],
      "reference_pack_size": 0.25
    }
  ]
}
```

## Compare a shopping list

Prices a list of concepts at each chosen store and works out the cheapest split across them. Computed from the catalog only: **no LLM call**, so it is not subject to `RATE_LIMIT` or `DAILY_GENERATE_CAP`.

```http
POST /compare
Content-Type: application/json

{
  "items": [{"concept_id": "yogurt_natural", "quantity": 2}, {"concept_id": "milk_whole", "quantity": 1}],
  "stores": ["Billa", "Hofer"],
  "diet_tags": ["lactose_free"],
  "min_split_savings_eur": 3.00,
  "country": "AT"
}
```

| Field | Rules |
|---|---|
| `items` | 1–50, unique `concept_id`s; `quantity` 1–50. An unknown concept is reported as missing at every store |
| `stores` | 1–5 unique store names of `country` (else `422 unknown_store`) |
| `diet_tags` | optional, unique: `vegetarian`, `vegan`, `gluten_free`, `lactose_free`; filter products within each concept (cleaning and hygiene products fit every diet) |
| `min_split_savings_eur` | 0–1000, 2 decimals, default `3.00` |
| `country` | `AT` (default) or `DE` |

How it is computed:

- **Quantity** counts the concept's reference pack (`reference_pack_size`, its smallest pack in the country). Each store buys the fewest whole packs that hold at least that much, so every basket has at least the requested amount: 2 × yogurt (smallest pack 250 g) is 2 × 250 g at Billa and 1 × 500 g at Hofer. No store buys more than `quantity` packs.
- **Which product:** within a store (and across stores for the split basket) the lowest `line_total_eur` for that amount wins; ties go to the lower `price_per_base_unit_eur`, then the store name and product id. A cheaper-per-kg 1 kg pack doesn't win when 250 g were asked for and a 250 g pack costs less.
- **Prices** are today's: the promo price while a promotion runs, the regular price after `promo_valid_until`.
- **Ranking:** fewest `missing_concepts` first, then the lowest `total_eur`, then the store name. The first is the best single store.
- **Savings** compare the same items: `split_extra_savings_eur` is what the best store charges above the split basket for the items it has; `total_savings_vs_worst_eur` is the largest such difference over all stores.
- **Recommendation:** `split_basket` when the split uses more than one store and `split_extra_savings_eur ≥ min_split_savings_eur`; otherwise `single_store` with `recommended_store` (`null` if no store has any item).

| Field | Meaning |
|---|---|
| `single_store_rankings[]` | per store: `items`, `total_eur`, `promo_savings_eur` (regular minus promo price over all packs), `missing_concepts` |
| `items[]` | `concept_id`, `product_id`, `names`, `store`, `packs_needed`, `pack_size`, `unit`, `price_eur` (per pack, today), `regular_price_eur`, `promo_price_eur` and `promo_valid_until` (only while a promotion runs, else `null`), `line_total_eur`, `price_per_base_unit_eur` (per 1 kg, 1 l, 1 piece or 1 pack: the item's `unit`) |
| `split_basket` | `stores[]` (only stores with items, by name: `store`, `items`, `total_eur`), `total_eur`, `missing_concepts` (sold by none of the stores), `total_savings_vs_worst_eur` |
| `recommended_strategy`, `recommended_store`, `split_extra_savings_eur` | see above |
| `catalog_version`, `price_date` | which reference prices were used |

Money is a number rounded to cents. Errors use the same format as `/generate`: `422 validation_error`, `422 unknown_store`.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check: `{"status": "healthy", "catalog_version": "..."}` |
| GET | `/api/catalog/meta` | Stores per country, diet tags, categories, price date |
| GET | `/api/catalog/concepts` | Concepts per country for the compare form |
| POST | `/generate` | Generate a shopping list or menu |
| POST | `/compare` | Price a shopping list at each store, plus the cheapest split (no LLM) |
