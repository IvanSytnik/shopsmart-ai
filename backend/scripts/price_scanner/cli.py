"""Weekly price scan for data_src/catalog_at.csv: python -m scripts.price_scanner.cli

    --login                      open the shops in a visible browser once (cookies, login, PLZ)
    (no flags)                   scan Billa and Hofer in the browser and print the changes
    --store billa|hofer|all      which store(s) to scan (default: all)
    --from-files PATH...         read flyer pages (PNG/JPEG/WebP/PDF) or saved text instead
                                 of the browser; needs --store billa or hofer
    --last-run                   reuse the offers of the previous scan: no browser, no OpenAI
    --dry-run                    print old -> new prices, change nothing (the default)
    --apply                      write catalog_at.csv and rebuild app/data/catalog.json
    --min-confidence 0.85        offers below it go to data_src/scanner_review.json

Typical week: scan (dry run), read the table and the review file, then
`--last-run --apply` writes exactly what was shown, without scanning again. Product pages
that answer HTTP 404 or 410 are listed as dead URLs (also in the review file): their
`source_url` in catalog_at.csv needs a new link.
"""

import argparse
import asyncio
import logging
import re
import shutil
import sys
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from scripts.build_catalog import DEFAULT_OUTPUT, DEFAULT_SOURCE, BuildError, read_rows
from scripts.price_scanner.adapters import ADAPTERS, FLYER_PORTALS, StoreAdapter
from scripts.price_scanner.browser import BrowserSession, login, run_folder
from scripts.price_scanner.capture import Capture
from scripts.price_scanner.config import (
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_REVIEW_FILE,
    RUNS_DIR,
    ScannerError,
    ScannerSettings,
)
from scripts.price_scanner.extractors.llm_extractor import LLMExtractor
from scripts.price_scanner.schemas import Failure, ScanLog
from scripts.price_scanner.updater import (
    REVIEW_LABELS,
    apply_updates,
    dead_product_urls,
    format_updates,
    plan_updates,
    save_catalog,
    store_products,
    write_review,
)

logger = logging.getLogger("price_scanner")

LAST_OFFERS = "last_offers.json"
RUN_FOLDER = re.compile(r"^\d{8}-\d{6}$")
KEEP_RUNS = 8  # screenshot folders kept in .scanner


def confidence(value: str) -> float:
    number = float(value)
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return number


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.price_scanner.cli",
        description="Scan Billa and Hofer prices and promotions into data_src/catalog_at.csv.",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="open the shops in a visible browser to accept cookies, log in and pick a PLZ",
    )
    parser.add_argument("--store", choices=[*ADAPTERS, "all"], default="all")
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--from-files",
        nargs="+",
        type=Path,
        metavar="PATH",
        help="flyer pages (PNG/JPEG/WebP), flyer PDFs, saved page text (.txt/.json/.md) "
        "or folders of them, instead of the browser",
    )
    source.add_argument(
        "--last-run",
        action="store_true",
        help="reuse the offers of the previous scan (no browser, no OpenAI calls)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="print the changes, write nothing to the catalog (the default)",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="write catalog_at.csv and rebuild app/data/catalog.json",
    )
    parser.add_argument(
        "--min-confidence",
        type=confidence,
        default=DEFAULT_MIN_CONFIDENCE,
        help="offers the model is less sure of go to the review file (default: %(default)s)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="show the browser while scanning (if a shop blocks the headless one)",
    )
    paths = parser.add_argument_group("paths")
    paths.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    paths.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    paths.add_argument("--review-file", type=Path, default=DEFAULT_REVIEW_FILE)
    paths.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    args = parser.parse_args(argv)
    if args.login and (args.from_files or args.last_run or args.apply):
        parser.error("--login only opens the browser; run the scan afterwards")
    if args.from_files and args.store == "all":
        parser.error("--from-files needs --store billa or --store hofer: whose flyer is it?")
    return args


def load_settings() -> ScannerSettings:
    try:
        return ScannerSettings()
    except ValidationError as e:
        raise ScannerError(
            "OPENAI_API_KEY is not set (environment or backend/.env)"
            if any(error["loc"] == ("openai_api_key",) for error in e.errors())
            else f"invalid SCANNER_* setting:\n{e}"
        ) from e


async def capture_pages(
    adapters: Sequence[StoreAdapter],
    rows: Sequence[dict[str, str]],
    args: argparse.Namespace,
    started: datetime,
) -> tuple[dict[str, list[Capture]], list[Failure]]:
    """Each store's pages, from the files given or the browser."""
    if args.from_files:
        adapter = adapters[0]
        return {adapter.key: adapter.read_files(args.from_files)}, []
    captures: dict[str, list[Capture]] = {}
    failures: list[Failure] = []
    folder = run_folder(args.runs_dir, started)
    async with BrowserSession(folder, headed=args.headed) as session:
        for adapter in adapters:
            products = store_products(rows, adapter.store)
            captures[adapter.key], failed = await adapter.scan(session, products)
            failures += failed
    logger.info("Screenshots: %s", folder)
    return captures, failures


async def scan(
    adapters: Sequence[StoreAdapter],
    rows: Sequence[dict[str, str]],
    args: argparse.Namespace,
    *,
    client: AsyncOpenAI | None,
    settings: ScannerSettings | None,
    today: date,
) -> tuple[ScanLog, list[Failure]]:
    """Capture the pages, then read the offers off them."""
    settings = settings or load_settings()
    captures, failures = await capture_pages(adapters, rows, args, datetime.now())
    own_client = client is None
    client = client or AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.scanner_timeout_s,
        max_retries=settings.scanner_max_retries,
    )
    extractor = LLMExtractor(client, settings, today)
    log = ScanLog(scanned_on=today, offers=[])
    try:
        for adapter in adapters:
            pages = captures.get(adapter.key, [])
            logger.info(
                "Reading %d %s page(s) with %s", len(pages), adapter.store, settings.scanner_model
            )
            offers, failed = await extractor.extract(
                adapter.store, adapter.hints, store_products(rows, adapter.store), pages
            )
            log.offers += offers
            failures += failed
    finally:
        if own_client:
            await client.close()
    return log, failures


def prune_runs(runs_dir: Path, keep: int = KEEP_RUNS) -> None:
    """Delete all but the newest `keep` screenshot folders."""
    if not runs_dir.is_dir():
        return
    folders = sorted(p for p in runs_dir.iterdir() if p.is_dir() and RUN_FOLDER.match(p.name))
    for folder in folders[:-keep]:
        shutil.rmtree(folder)


def unread_products(
    adapters: Sequence[StoreAdapter],
    rows: Sequence[dict[str, str]],
    log: ScanLog,
    failures: Sequence[Failure],
) -> list[str]:
    """Products whose own page was read but brought no offer for them: a captcha, a changed
    page or a product no longer sold. (Offers from other pages don't count.)"""
    named = {(o.source, o.offer.product_id) for o in log.offers}
    failed = {f.source for f in failures}
    unread = []
    for adapter in adapters:
        products = store_products(rows, adapter.store)
        read = set(adapter.product_pages(products)) - failed
        unread += [
            p.id for p in products if p.source_url in read and (p.source_url, p.id) not in named
        ]
    return unread


def run(
    args: argparse.Namespace,
    *,
    client: AsyncOpenAI | None,
    settings: ScannerSettings | None,
    today: date,
) -> int:
    adapters = list(ADAPTERS.values()) if args.store == "all" else [ADAPTERS[args.store]]
    if args.login:
        urls = [url for adapter in adapters for url in adapter.login_pages]
        asyncio.run(login([*urls, *FLYER_PORTALS]))
        return 0

    rows = read_rows(args.source)
    stores = {adapter.store for adapter in adapters}
    last_offers = args.runs_dir / LAST_OFFERS
    if args.last_run:
        if not last_offers.is_file():
            raise ScannerError(f"no previous scan in {last_offers}")
        log = ScanLog.model_validate_json(last_offers.read_text(encoding="utf-8"))
        log.offers = [o for o in log.offers if o.store in stores]
        failures = log.failures
        print(f"Offers of the scan on {log.scanned_on}: {len(log.offers)}")
    else:
        log, failures = asyncio.run(
            scan(adapters, rows, args, client=client, settings=settings, today=today)
        )
        log.failures = failures
        args.runs_dir.mkdir(exist_ok=True)
        last_offers.write_text(log.model_dump_json(indent=2) + "\n", encoding="utf-8")
        prune_runs(args.runs_dir)
        print(f"Offers read: {len(log.offers)}; pages that failed: {len(failures)}")
        for failure in failures:
            print(f"  {failure.source}: {failure.problem}")

    plan = plan_updates(rows, log.offers, min_confidence=args.min_confidence, today=log.scanned_on)
    changed = [u for u in plan.updates if u.change != "confirmed"]
    if changed:
        print(format_updates(changed))
    else:
        print("No price changes.")
    if confirmed := len(plan.updates) - len(changed):
        print(f"Unchanged prices confirmed: {confirmed} (price_date -> {log.scanned_on})")
    dead = dead_product_urls((row for row in rows if row["store"] in stores), failures)
    write_review(
        args.review_file,
        plan.review,
        scanned_on=log.scanned_on,
        min_confidence=args.min_confidence,
        dead_urls=dead,
    )
    if plan.review:
        counts: dict[str, int] = {}
        for item in plan.review:
            counts[REVIEW_LABELS[item.kind]] = counts.get(REVIEW_LABELS[item.kind], 0) + 1
        summary = ", ".join(f"{label} {n}" for label, n in counts.items())
        print(f"For review: {len(plan.review)} offers in {args.review_file} ({summary})")
    if plan.ignored:
        print(f"Ignored: {plan.ignored} offers for other products on product pages (carousels)")
    if dead:
        print(
            f"Dead product URLs (HTTP 404/410): {len(dead)}; update their source_url in "
            f"{args.source.name}:"
        )
        width = max(len(d.product_id) for d in dead)
        for d in dead:
            print(f"  {d.product_id.ljust(width)}  HTTP {d.http_status}  {d.source_url}")
    if not args.last_run and not args.from_files:
        if unread := unread_products(adapters, rows, log, failures):
            print(
                f"No price read for {len(unread)} product page(s) (captcha, changed page or "
                f"no longer sold? see the screenshots; --login again if needed): "
                + ", ".join(unread)
            )

    if not args.apply:
        print(
            "Dry run: catalog unchanged. To write this: "
            "python -m scripts.price_scanner.cli --last-run --apply"
        )
        return 0
    if not plan.updates:
        print("Nothing to apply.")
        return 0
    build_report = save_catalog(apply_updates(rows, plan.updates), args.source, args.output)
    print(build_report)
    print(f"Updated {len(plan.updates)} row(s) in {args.source} and rebuilt {args.output}")
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    client: AsyncOpenAI | None = None,
    settings: ScannerSettings | None = None,
    today: date | None = None,
) -> int:
    """Run the scanner. `client`, `settings` and `today` are for tests."""
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per OpenAI call
    try:
        return run(args, client=client, settings=settings, today=today or date.today())
    except BuildError as e:
        print(f"Catalog build failed, nothing written:\n{e}", file=sys.stderr)
    except (ScannerError, OSError) as e:
        print(f"Price scanner: {e}", file=sys.stderr)
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
