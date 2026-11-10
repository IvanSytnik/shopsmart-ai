"""Weekly price and promotion scanner for data_src/catalog_at.csv (local tool).

    cd backend
    python -m scripts.price_scanner.cli --login                 # once: cookies, login, PLZ
    python -m scripts.price_scanner.cli                         # scan, print changes (dry run)
    python -m scripts.price_scanner.cli --last-run --apply      # write what the scan found
    python -m scripts.price_scanner.cli --store billa --from-files flyer.pdf

Pipeline: an adapter (adapters/) captures pages, from the browser (browser.py, Playwright
with a saved profile) or from local flyer files (capture.py); the LLM extractor
(extractors/llm_extractor.py) reads offers off them and matches them to our product ids;
the updater (updater.py) turns confident offers into CSV changes, queues the rest in
data_src/scanner_review.json and, with --apply, rebuilds app/data/catalog.json.

Isolated from the app: nothing in app/ imports this package, its extra dependencies are in
requirements-scraper.txt only, and Playwright and pypdfium2 are imported where they're
used, so the tests run without them. See docs/CATALOG.md, "Weekly price updates".
"""
