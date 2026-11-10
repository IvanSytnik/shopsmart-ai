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
- **Price:** the regular single-item shelf price shown on the page. Temporary promotions (a struck-through former price, "Aktion", multi-buy prices such as "ab 2 Packungen") were skipped where an equivalent regular-priced product existed. Billa's "Immer clever Preis" is a permanent price, not a promotion. Promotions are now recorded separately, see [Promotions](#promotions).
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

### Concepts

`concept_id` names the kind of product, in snake_case and without the pack size: `milk_whole`, `cheese_gouda`, `minced_meat`. Products a shopper would buy in place of each other share it, in any store (and later country), so a shopping list can be compared across stores by price per kg, l or piece.

- Name: the product first, then what sets it apart: `cheese_gouda`, `yogurt_high_protein`, `bread_toast_wholegrain`.
- One concept, whatever the pack size, form or brand: fresh and UHT milk (`milk_whole`), Gouda in a block or sliced (`cheese_gouda`), chicken breast fillet or strips (`chicken_breast`), 500 g or 1 kg of mixed mince (`minced_meat`), spaghetti or fusilli (`pasta`), organic or not.
- Different concepts when the product itself differs: beef or mixed mince (`minced_beef`, `minced_meat`), white or wholegrain toast, dried or canned legumes (their price per kg isn't comparable), smoked or fresh fish.
- Products sharing a concept must have the same `unit` and `category`, or the build fails. Their diet tags may differ (`butter` holds a lactose-free and a regular butter): diets filter the products within a concept.
- Products sold by the `pack` compare per pack, so their id says what one pack holds: `toilet_paper_10_rolls`. A size that isn't the pack size stays too: `bin_bags_30l`, sold by the piece.
- Every concept has a name in `backend/data_src/concepts_at.csv` (`concept_id,name_en,name_uk,name_de`, sorted by id), shown when shoppers build a list to compare. Name the kind of product, neutrally: no store or own brand, no variant of one product (`Butter`, not `Clever Teebutter`; `Vollmilch`, not `Haltbar-Vollmilch 3,5%`; `Nudeln`, not `Fusilli`). A product whose concept has no name fails the build; the tests also reject names of concepts without products and names with a known store brand.

Billa and Hofer currently share 11 of 68: `milk_whole`, `cheese_gouda`, `yogurt_natural`, `butter`, `oat_drink`, `bread_toast`, `bread_rolls`, `minced_meat`, `chicken_breast`, `ham_cooked`, `salmon_fillet`.

### Promotions

A promotion is recorded next to the regular price: `promo_price_eur` and `promo_valid_until` (its last day). `price_date` is the day it was seen; the promotion counts from then.

In `catalog.json`, `price_eur` is the price every plan uses: the promo price while the promotion runs on the catalog's `price_date`, the regular price otherwise. The CSV `price_eur` becomes `regular_price_eur`. The running app also checks the date: once a promotion has ended, plans use the regular price without a rebuild. The build lists running and ended promotions; clear the columns of ended ones when you next edit the CSV.

## CSV columns

| Column | Meaning |
|---|---|
| `id` | `at-<store>-<product>-<size>`, lowercase slug, unique |
| `concept_id` | kind of product without pack size, shared by interchangeable products, see [Concepts](#concepts) |
| `store` | `Billa`, `Hofer` (later also `Spar`, `Lidl`) |
| `category` | one of the catalog categories (`dairy`, `bread`, `meat`, …, `cleaning`, `hygiene`, `other`) |
| `name_en`, `name_uk`, `name_de` | product name in each UI language |
| `unit`, `pack_size` | `kg`/`l` with the pack size in that unit, or `pcs`/`pack` with a whole number |
| `net_weight_g` | contents of one `pcs`/`pack` food product in grams (empty otherwise) |
| `portion_unit` | optional: `g`, `ml`, `pcs` or `pack`; empty = derived from `unit` |
| `price_eur` | regular price of one pack, 2 decimals, without deposit |
| `promo_price_eur` | optional: promotional price of one pack, below `price_eur` |
| `promo_valid_until` | last day of the promotion (`YYYY-MM-DD`), set together with `promo_price_eur`, not before `price_date` |
| `kcal_100` … `carbs_100` | nutrition per 100 g/ml; empty for non-food |
| `diet_tags` | `;`-separated: `vegetarian`, `vegan`, `gluten_free`, `lactose_free` |
| `source_url` | the product page on the store's site |
| `price_date` | date the price was seen (`YYYY-MM-DD`) |
| `verified` | `yes` once a person has checked the row against the store page or shelf; `no` otherwise |

## Verifying rows

All rows start as `verified=no`: they were collected by reading the stores' web pages, and nobody has checked them against a shelf or receipt yet. To verify a row, open its `source_url` (or check the shelf), correct `price_eur`, pack size or name if needed, set `price_date` to that day and `verified` to `yes`. The build prints how many rows are still unverified.

## Updating the catalog

1. Edit `backend/data_src/catalog_at.csv`: add, change or remove rows. Keep ids stable, since saved plans refer to them. A new `concept_id` needs a row in `backend/data_src/concepts_at.csv`; remove the row of a concept whose last product you remove.
2. Build and check:

   ```bash
   cd backend
   python scripts/build_catalog.py          # writes app/data/catalog.json
   pytest -q tests/test_catalog_at.py       # coverage rules
   ```

   The build fails on any invalid row (including a `vegan` row without `vegetarian` and `lactose_free`, an invalid promotion, or a product whose unit or category differs from another with the same `concept_id`) and names the CSV line. The coverage tests require:
   - at least 25 food products per store;
   - at least 12 food candidates for every pair of stores, with no diet and with each diet tag;
   - at most 100 candidates for any pair of stores (the LLM schema's enum limit);
   - unique ids;
   - a `source_url` on the store's own domain for every row;
   - a `concept_id` without the pack size, and exactly the known set of concepts shared between stores (update `SHARED_CONCEPTS` when it grows);
   - a brand-free name in `concepts_at.csv` for exactly the concepts of the products;
   - a `catalog.json` that matches the CSV.
3. Commit the CSVs and the generated JSON together.

Collect politely: a few dozen page views per store, by hand or with a rate-limited script. No bulk scraping.

## Weekly price updates

`backend/scripts/price_scanner` reads current prices and promotions off the stores' pages and flyers (Flugblätter) and writes them into `catalog_at.csv`. It runs on your computer only: it uses a browser profile with your cookie consent and PLZ, and its dependencies (`backend/requirements-scraper.txt`: Playwright, pypdfium2, Pillow) are neither in `requirements.txt` nor in the Docker image (`.dockerignore` leaves the scanner out, and nothing in `app/` imports it).

1. **Pages.** For each store, the scanner opens the `source_url` of every product in the CSV, then the store's offers page (Billa `shop.billa.at/aktionen`, Hofer `www.hofer.at/de/angebote.html`). It reads in one tab, one page after another, with 3–7 s pauses and some scrolling so lazy-loaded prices appear. That is about 50 pages for Billa and 30 for Hofer, roughly 10 minutes a week. Instead of the browser it can read flyer files you saved (`--from-files`).
2. **Reading.** An OpenAI model (`gpt-4o-mini`, Structured Outputs) reads each page's text, or each flyer page's image: regular price, promo price and dates, a confidence, and the matching product id. The model reads prices; it never computes them. Pages are read in one of two ways:
   - **A product's own page** (a row's `source_url`). The model gets only that product (id, German name, pack size) and reads only the page's main product, ignoring "Ähnliche Produkte" carousels, recommendations and the footer. Its reply holds at most one offer, and the id can only be that product's or `null` (the page shows another product or pack size).
   - **Offers pages and flyers** (and `--from-files`). The model gets the store's product list and returns every offer it finds, at most 30. Each id can only be one of that store's ids or `null`.
3. **Checking.** An offer changes the CSV only if it names one of the store's products, its confidence is at least `--min-confidence` (0.85) and its prices pass these checks:
   - the regular price moved by at most 50 % (a bigger jump usually means another pack size);
   - prices are above 0;
   - the promo price is below the regular price;
   - the promotion has a last day, has started and hasn't ended;
   - the row wasn't checked after the scan.

   When several offers name one product, the one from its own page wins over offers pages and flyers, even when it is less confident; among equals, the most confident one wins. If it shows no promotion, a promotion seen on an offers page or flyer at the same regular price (or with none shown) is added to it, without a conflict. A product page counts for its own product only: other products read there (carousels in scans made before product pages were read this way) are ignored and counted ("Ignored: … carousels").

   Everything else goes to `backend/data_src/scanner_review.json` (git-ignored) with the reason:
   - promotions of products not in the catalog;
   - a product page showing another product or pack size (the row's data or link may be out of date);
   - offers below the confidence threshold;
   - offers that failed a check;
   - a second offer for a product that disagrees with the one applied.

   Product pages that answer HTTP 404 or 410 are listed in the scan's output and under `dead_product_url` in the review file, with the product id and status: their `source_url` needs a new link.
4. **Writing** (`--apply`). The changed rows are built with `build_catalog.py`'s validation first; only if that passes are `catalog_at.csv` and `app/data/catalog.json` written. A failing build writes neither.

What a changed row says is what the shelf showed on the scan day:

| Column | Written as |
|---|---|
| `price_eur` | the regular price seen, 2 decimals; kept when only a promo price was shown |
| `promo_price_eur`, `promo_valid_until` | the promotion seen; cleared when the page shows none ("promo ended") |
| `price_date` | the scan day; an unchanged price only moves the date ("confirmed") |
| `verified`, `source_url`, names, nutrition | unchanged |

### Setup (once)

```bash
cd backend && source .venv/bin/activate
pip install -r requirements-scraper.txt
python -m playwright install chromium
python -m scripts.price_scanner.cli --login
```

`--login` opens a visible browser with the Billa online shop, Hofer, Roksh and Marktguru. In each tab:
- accept the cookie banner;
- solve the captcha if there is one;
- log in if you want to;
- pick your PLZ or store.

Then close the window. Aktionsfinder has been offline since May 2026, so `--login` doesn't open it. The profile is saved in `backend/.browser_profile/`. It is git-ignored and left out of the Docker image; it holds your shop sessions, so don't share it. Run `--login` again when a scan reports product pages without a price (a cookie banner or captcha came back). If a shop blocks the headless browser, scan with `--headed`.

### Each week

```bash
cd backend
python -m scripts.price_scanner.cli                      # scan both stores: prints the changes, writes nothing
python -m scripts.price_scanner.cli --last-run --apply   # write exactly what that run showed
```

A dry run prints the changed rows, then a summary:

```
Offers read: 92; pages that failed: 0
Store  Product                 Price EUR     Promo EUR                   Conf.  Change
-----  ----------------------  ------------  --------------------------  -----  ------
Hofer  at-hofer-whole-milk-1l  1.32 -> 1.39  -                           0.96   price
Hofer  at-hofer-gouda-450g     3.99          - -> 3.49 until 2026-11-14  0.93   promo
Unchanged prices confirmed: 61 (price_date -> 2026-11-10)
For review: 9 offers in data_src/scanner_review.json (not in the catalog 7, low confidence 2)
Dead product URLs (HTTP 404/410): 1; update their source_url in catalog_at.csv:
  at-hofer-protein-yogurt-500g  HTTP 410  https://www.hofer.at/produkt/milsani-high-protein-naturjoghurt-000000000000517851
```

`--last-run` reuses the offers and failed pages saved by the previous scan (`backend/.scanner/last_offers.json`), so applying needs no second scan and no OpenAI calls, and writes what you saw. Page screenshots of the last 8 runs are in `backend/.scanner/<date-time>/`; review items name theirs.

After applying, check `git diff data_src/catalog_at.csv` and go through `scanner_review.json`. Add rows for new products worth keeping by hand (with a `concepts_at.csv` name for a new concept), then commit the CSVs and `catalog.json` together, as with any catalog change.

### Flyers (`--from-files`)

Save the flyer as a PDF (from the store's site or Marktguru) or take screenshots of its pages, then name the store:

```bash
python -m scripts.price_scanner.cli --store billa --from-files ~/Downloads/billa-flugblatt.pdf
python -m scripts.price_scanner.cli --store hofer --from-files ~/Desktop/hofer-pages/
```

It reads PDFs (one 144 dpi image per page), PNG, JPEG, WebP and folders of them, as well as text saved from a shop page (`.txt`, `.json`, `.md`). Each page is one OpenAI call; an image page costs more than a text page (with `gpt-4o-mini`, roughly half a cent per flyer page; a full browser scan costs a few cents). Flyers often show next week's offers: promotions that haven't started yet go to review. Scan a flyer on or after its first day.

### Options

| Flag | |
|---|---|
| `--login` | open the shops in a visible browser to accept cookies, log in and pick a PLZ |
| `--store billa\|hofer\|all` | stores to scan (default `all`; `--from-files` needs one store) |
| `--from-files PATH...` | read flyer files instead of the browser |
| `--last-run` | reuse the previous scan's offers |
| `--dry-run` | print the changes, write nothing (default) |
| `--apply` | write `catalog_at.csv` and rebuild `catalog.json` |
| `--min-confidence 0.85` | offers below it go to review |
| `--headed` | show the browser while scanning |
| `--source`, `--output`, `--review-file`, `--runs-dir` | other paths (tests, experiments) |

The OpenAI key comes from `OPENAI_API_KEY` in the environment or `backend/.env`. These optional settings can go in the same places:
- `SCANNER_MODEL` (default `gpt-4o-mini`);
- `SCANNER_TEMPERATURE` (0);
- `SCANNER_MAX_TOKENS` (6000);
- `SCANNER_TIMEOUT_S` (120);
- `SCANNER_MAX_RETRIES` (2);
- `SCANNER_CONCURRENCY` (3 calls at once).

### Running it every week

A scheduled dry run prepares the week's changes; you then read the log and apply them with `--last-run --apply`. For example, run it on Thursday morning, after the new flyers start. With cron (`crontab -e`):

```cron
0 8 * * 4  cd /path/to/shopsmart-ai-full/backend && mkdir -p .scanner && .venv/bin/python -m scripts.price_scanner.cli >> .scanner/cron.log 2>&1
```

Add `--apply` to the job to write the changes as well. They then wait in `git diff` until you commit them.

On macOS, cron skips jobs while the Mac sleeps. A launchd agent catches up after wake instead. Save this as `~/Library/LaunchAgents/at.shopsmart.price-scanner.plist`, with your paths, create `backend/.scanner/` for its log, and run `launchctl load ~/Library/LaunchAgents/at.shopsmart.price-scanner.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>at.shopsmart.price-scanner</string>
  <key>WorkingDirectory</key><string>/path/to/shopsmart-ai-full/backend</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/shopsmart-ai-full/backend/.venv/bin/python</string>
    <string>-m</string><string>scripts.price_scanner.cli</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>8</integer></dict>
  <key>StandardOutPath</key><string>/path/to/shopsmart-ai-full/backend/.scanner/scheduled.log</string>
  <key>StandardErrorPath</key><string>/path/to/shopsmart-ai-full/backend/.scanner/scheduled.log</string>
</dict>
</plist>
```

The scanner stays within the polite-collection rule above. Each week it reads one tab at a time, with pauses: each product's own page plus the first offers page per store. It uses no parallel requests and makes no attempt to hide that it is a browser driven by a script.
