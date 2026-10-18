# Price catalog

The app prices every plan from `backend/app/data/catalog.json`. That file is generated from the human-editable source `backend/data_src/catalog_at.csv`; edit the CSV, never the JSON.

> **Disclaimer.** These are **reference prices** collected on the date shown in each row. Prices in a store, in another region or after a promotion ends may differ. ShopSmart AI is not affiliated with any of the retailers.

## Current state (v1, Austria)

| | |
|---|---|
| Version | `at-2026-10-15` |
| Collected on | 2026-10-15 |
| Country | AT |
| Stores | **Billa** (46 food, 4 non-food), **Hofer** (31 food) |
| Verified | none yet (`verified=no` on every row, see below) |

### Not included yet

- **Spar**: spar.at and interspar.at refused automated page requests (HTTP 403), and search engines did not return current Spar product pages with prices. No price could be verified, so no Spar products are listed.
- **Lidl Austria**: lidl.at loads its product tiles with JavaScript, so category pages contain no products or prices when fetched as plain HTML, and almost no regular-assortment product pages are indexed. No price could be verified, so no Lidl products are listed.
- **Hofer** only lists fresh categories (bread, dairy, meat, fish) and current promotions online. Fruit, vegetables, pasta, rice, legumes, eggs and household goods are not on hofer.at with prices, so Hofer has none of them here. Plans that combine Hofer with Billa still cover every category.

Spar and Lidl can be added by hand from shelf labels or receipts: one row per product with a source URL to the product page and the date the price was seen.

## Sources

Every row's `source_url` points to the product page on the store's own site, which shows the price:

- Billa: `https://shop.billa.at/produkte/...` (Billa online shop)
- Hofer: `https://www.hofer.at/produkt/...` (Hofer product range pages)

Prices were read from those stores' category listing pages, which show the product name, pack size and price, and each product is linked to its product page. The tests require every `source_url` to be on the store's own domain.

## Method

- **Selection:** everyday staples per category (dairy, eggs, bread, pasta/rice/grains, legumes, vegetables, fruit, meat, fish, frozen, pantry, snacks, beverages) plus a few household items. Store brands (Billa *Clever*, *Ja! Natürlich*, *BILLA Bio*; Hofer *Milsani*, *Happy Harvest*, *Backbox*, *Sonnhof*, *Fairhof*) were preferred because they are the cheapest and most stable.
- **Price:** the regular single-item shelf price shown on the page. Temporary promotions (a struck-through former price, "Aktion", multi-buy prices such as "ab 2 Packungen") were skipped where an equivalent regular-priced product existed. Billa's "Immer clever Preis" is a permanent price, not a promotion.
- **Deposit (Pfand)** is not included in `price_eur`.
- **Loose produce** sold by weight (Billa bananas) is listed as a 1 kg pack at the per-kg price; the name says "per kg".
- **Products without a fixed pack size** (weighed meat, "ab 0,5 kg") were left out.
- **Never estimated:** a product whose current price could not be read on the store's site is left out.

### Nutrition

`kcal_100`, `protein_100`, `fat_100` and `carbs_100` are **typical values per 100 g (or 100 ml)** for the product type from standard nutrition tables, not the label of the exact product. They are close enough for portion planning but can differ from a specific product by roughly 10–20%. The build script converts them to per-pack values with the pack size (1 ml counted as 1 g); products sold by `pcs` or `pack` need `net_weight_g` (eggs: 10 × size M ≈ 530 g edible).

### Diet tags

Tags are assigned conservatively from the product type:

- `vegan` only for products without any animal ingredient (plain plant foods, breads made from flour, water, yeast and salt, plant drinks). Wheat toast and similar bread that often contains milk or butter is only `vegetarian`.
- `gluten_free` only for naturally gluten-free foods (fresh produce, plain meat and fish, milk, eggs, rice, polenta, dried legumes). Oats are **not** tagged because of cross-contamination.
- `lactose_free` for foods without milk, and for dairy explicitly sold as lactose-free.
- A `vegan` row must also be tagged `vegetarian` and `lactose_free`: the diet filter requires every chosen tag, so a missing one hides the product. The build fails and lists the offending rows; tags are never derived automatically.
- Cheese is tagged `vegetarian`, although some cheeses use animal rennet.
- Processed meat (sausages, Extrawurst, cevapcici) is not tagged `gluten_free`.

## CSV columns

| Column | Meaning |
|---|---|
| `id` | `at-<store>-<product>-<size>`, lowercase slug, unique |
| `store` | `Billa`, `Hofer` (later also `Spar`, `Lidl`) |
| `category` | one of the catalog categories (`dairy`, `bread`, `meat`, …, `cleaning`, `hygiene`, `other`) |
| `name_en`, `name_uk`, `name_de` | product name in each UI language |
| `unit`, `pack_size` | `kg`/`l` with the pack size in that unit, or `pcs`/`pack` with a whole number |
| `net_weight_g` | contents of one `pcs`/`pack` food product in grams (empty otherwise) |
| `portion_unit` | optional: `g`, `ml`, `pcs` or `pack`; empty = derived from `unit` |
| `price_eur` | price of one pack, 2 decimals, without deposit |
| `kcal_100` … `carbs_100` | nutrition per 100 g/ml; empty for non-food |
| `diet_tags` | `;`-separated: `vegetarian`, `vegan`, `gluten_free`, `lactose_free` |
| `source_url` | the product page on the store's site |
| `price_date` | date the price was seen (`YYYY-MM-DD`) |
| `verified` | `yes` once a person has checked the row against the store page or shelf; `no` otherwise |

## Verifying rows

All rows start as `verified=no`: they were collected by reading the stores' web pages, and nobody has checked them against a shelf or receipt yet. To verify a row, open its `source_url` (or check the shelf), correct `price_eur`, pack size or name if needed, set `price_date` to that day and `verified` to `yes`. The build prints how many rows are still unverified.

## Updating the catalog

1. Edit `backend/data_src/catalog_at.csv`: add, change or remove rows. Keep ids stable, since saved plans refer to them.
2. Build and check:

   ```bash
   cd backend
   python scripts/build_catalog.py          # writes app/data/catalog.json
   pytest -q tests/test_catalog_at.py       # coverage rules
   ```

   The build fails on any invalid row (including a `vegan` row without `vegetarian` and `lactose_free`) and names the CSV line. The coverage tests require:
   - at least 25 food products per store;
   - at least 12 food candidates for every pair of stores, with no diet and with each diet tag;
   - at most 100 candidates for any pair of stores (the LLM schema's enum limit);
   - unique ids;
   - a `source_url` on the store's own domain for every row;
   - a `catalog.json` that matches the CSV.
3. Commit the CSV and the generated JSON together.

Collect politely: a few dozen page views per store, by hand or with a rate-limited script. No bulk scraping.
