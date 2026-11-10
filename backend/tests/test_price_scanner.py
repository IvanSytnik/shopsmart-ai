"""The weekly price scanner (scripts/price_scanner): which offers reach catalog_at.csv, the
review queue, reading offers with a mocked OpenAI, and the CLI's dry run and apply.

Runs without Playwright, pypdfium2 or pillow (requirements-scraper.txt): nothing here opens
a browser or renders a PDF.
"""

import asyncio
import json
import shutil
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from scripts.build_catalog import BACKEND, DEFAULT_SOURCE, BuildError, read_rows
from scripts.price_scanner import cli
from scripts.price_scanner.adapters import HoferAdapter
from scripts.price_scanner.browser import BrowserSession
from scripts.price_scanner.capture import Capture, PageImage, clean_text, load_files
from scripts.price_scanner.config import HttpStatusError, ScannerError, ScannerSettings
from scripts.price_scanner.extractors.llm_extractor import LLMExtractor
from scripts.price_scanner.schemas import ExtractedOffer, Failure, ScanLog, ScannedOffer
from scripts.price_scanner.updater import (
    DeadUrl,
    PriceState,
    UpdatePlan,
    apply_updates,
    dead_product_urls,
    format_updates,
    money,
    plan_updates,
    save_catalog,
    store_products,
    write_review,
    write_rows,
)
from tests.conftest import FROZEN_CATALOG_AT, FakeOpenAI

TODAY = date(2026, 11, 10)
ROWS = read_rows(FROZEN_CATALOG_AT)  # every row has price_date 2026-10-15, no promotion
MILK = "at-hofer-whole-milk-1l"  # Hofer, €1.32
GOUDA = "at-hofer-gouda-450g"  # Hofer, €3.99
BANANAS = "at-billa-bananas-1kg"  # Billa
MILK_PAGE = "https://www.hofer.at/produkt/milsani-vollmilch-laenger-frisch-000000000000106876"
OFFERS_PAGE = "https://www.hofer.at/de/angebote.html"  # offers of many products
PROTEIN = "at-hofer-protein-yogurt-500g"
PROTEIN_PAGE = next(row["source_url"] for row in ROWS if row["id"] == PROTEIN)
HOFER = store_products(ROWS, "Hofer")


def offer(
    product_id: str | None = MILK,
    *,
    regular: str | None = None,
    promo: str | None = None,
    start: date | None = None,
    until: date | None = None,
    confidence: float = 0.95,
) -> ExtractedOffer:
    return ExtractedOffer(
        product_id=product_id,
        raw_name_de="Milsani Vollmilch 3,5%",
        pack_size_desc="1 l",
        regular_price_eur=Decimal(regular) if regular is not None else None,
        promo_price_eur=Decimal(promo) if promo is not None else None,
        promo_valid_from=start,
        promo_valid_until=until,
        confidence=confidence,
        notes=None,
    )


PAGES = {row["id"]: row["source_url"] for row in ROWS}


def seen(o: ExtractedOffer, store: str = "Hofer", source: str | None = None) -> ScannedOffer:
    """`o` as read on `source`: by default its product's own page, else the offers page."""
    page = source or PAGES.get(o.product_id or "", OFFERS_PAGE)
    return ScannedOffer(store=store, source=page, offer=o)


def plan(
    *offers: ExtractedOffer,
    rows: list[dict[str, str]] = ROWS,
    min_confidence: float = 0.85,
) -> UpdatePlan:
    return plan_updates(rows, [seen(o) for o in offers], min_confidence=min_confidence, today=TODAY)


def with_row(product_id: str, **changes: str) -> list[dict[str, str]]:
    return [{**row, **changes} if row["id"] == product_id else row for row in ROWS]


# --- updater: what an offer changes --------------------------------------------------------


def test_a_new_regular_price_updates_price_and_price_date() -> None:
    result = plan(offer(regular="1.39"))

    assert result.review == []
    [update] = result.updates
    assert (update.product_id, update.change) == (MILK, "price")
    assert update.old == PriceState("1.32", "", "", "2026-10-15")
    assert update.new == PriceState("1.39", "", "", "2026-11-10")


def test_a_promotion_is_written_next_to_the_regular_price() -> None:
    [update] = plan(offer(regular="1.32", promo="0.99", until=date(2026, 11, 14))).updates

    assert update.new == PriceState("1.32", "0.99", "2026-11-14", "2026-11-10")
    assert update.change == "promo"


def test_a_promotion_with_a_new_regular_price_changes_both() -> None:
    [update] = plan(offer(regular="1.35", promo="0.99", until=date(2026, 11, 14))).updates

    assert update.new == PriceState("1.35", "0.99", "2026-11-14", "2026-11-10")
    assert update.change == "price, promo"


def test_a_promo_price_alone_keeps_the_regular_price() -> None:
    [update] = plan(offer(promo="1.09", start=TODAY, until=date(2026, 11, 14))).updates

    assert update.new == PriceState("1.32", "1.09", "2026-11-14", "2026-11-10")


def test_prices_are_written_with_two_decimals() -> None:
    [update] = plan(offer(regular="1.4", promo="0.899", until=date(2026, 11, 14))).updates

    assert (update.new.price_eur, update.new.promo_price_eur) == ("1.40", "0.90")
    assert [money(Decimal(v)) for v in ("2", "2.675", "0.005")] == ["2.00", "2.68", "0.01"]


def test_an_unchanged_price_is_confirmed_with_the_new_date() -> None:
    [update] = plan(offer(regular="1.32")).updates

    assert update.change == "confirmed"
    assert update.new == PriceState("1.32", "", "", "2026-11-10")


def test_a_shelf_without_a_promotion_ends_the_old_one() -> None:
    rows = with_row(
        MILK, promo_price_eur="0.99", promo_valid_until="2026-11-14", price_date="2026-11-03"
    )
    [update] = plan(offer(regular="1.32"), rows=rows).updates

    assert update.new == PriceState("1.32", "", "", "2026-11-10")
    assert update.change == "promo ended"


# --- updater: what goes to review ----------------------------------------------------------


@pytest.mark.parametrize(
    ("confidence", "min_confidence", "applied"),
    [(0.85, 0.85, True), (0.849, 0.85, False), (0.2, 0.85, False), (0.85, 0.9, False)],
)
def test_offers_below_the_minimum_confidence_go_to_review(
    confidence: float, min_confidence: float, applied: bool
) -> None:
    result = plan(offer(regular="1.39", confidence=confidence), min_confidence=min_confidence)

    assert len(result.updates) == int(applied)
    assert [item.kind for item in result.review] == ([] if applied else ["low_confidence"])


def test_offers_without_a_product_go_to_review() -> None:
    new = offer(None, regular="4.99", promo="3.49", until=date(2026, 11, 14), confidence=0.99)

    [item] = plan_updates(
        ROWS, [seen(new, source=OFFERS_PAGE)], min_confidence=0.85, today=TODAY
    ).review

    assert (item.kind, item.catalog, item.scanned.offer) == ("not_in_catalog", None, new)


def test_a_product_page_showing_another_product_goes_to_review_with_its_row() -> None:
    other = offer(None, regular="1.49", confidence=0.95)  # e.g. now sold as 0.75 l

    result = plan_updates(ROWS, [seen(other, source=MILK_PAGE)], min_confidence=0.85, today=TODAY)

    assert result.updates == []
    [item] = result.review
    assert (item.kind, item.catalog) == ("page_mismatch", PriceState("1.32", "", "", "2026-10-15"))
    assert item.reason == f"the page of {MILK} shows another product or pack size"


@pytest.mark.parametrize("product_id", [BANANAS, "at-hofer-no-such-product"])
def test_ids_of_other_stores_or_unknown_ids_go_to_review(product_id: str) -> None:
    result = plan(offer(product_id, regular="1.59"))

    assert result.updates == []
    assert [(i.kind, i.catalog) for i in result.review] == [("unknown_product", None)]


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({}, "no price"),
        ({"regular": "0.001"}, "regular price 0.001 is not above 0"),
        ({"regular": "2.49"}, "regular price 1.32 -> 2.49 moved more than 50%"),
        ({"regular": "0.59"}, "regular price 1.32 -> 0.59 moved more than 50%"),
        ({"promo": "0.99"}, "promotion without a last day"),
        ({"promo": "0.99", "until": date(2026, 11, 9)}, "promotion ended on 2026-11-09"),
        (
            {"promo": "0.99", "start": date(2026, 11, 12), "until": date(2026, 11, 18)},
            "promotion starts on 2026-11-12",
        ),
        (
            {"regular": "1.29", "promo": "1.29", "until": date(2026, 11, 14)},
            "promo price 1.29 is not below the regular price 1.29",
        ),
        (  # below the price seen, but not below the catalog's regular price
            {"promo": "1.49", "until": date(2026, 11, 14)},
            "promo price 1.49 is not below the regular price 1.32",
        ),
    ],
)
def test_implausible_offers_go_to_review(kwargs: dict[str, Any], reason: str) -> None:
    result = plan(offer(**kwargs))

    assert result.updates == []
    [item] = result.review
    assert item.kind == "rejected"
    assert reason in item.reason
    assert item.catalog == PriceState("1.32", "", "", "2026-10-15")


def test_a_row_checked_after_the_scan_is_not_overwritten() -> None:
    result = plan(offer(regular="1.39"), rows=with_row(MILK, price_date="2026-11-12"))

    assert result.updates == []
    assert "price_date 2026-11-12 is after the scan" in result.review[0].reason


def test_the_most_confident_offer_wins_and_a_differing_one_goes_to_review() -> None:
    flyer = seen(offer(regular="1.35", confidence=0.9), source="flyer.pdf#page=2")
    page = seen(offer(regular="1.39", confidence=0.97))
    same = seen(offer(regular="1.39", confidence=0.88), source="flyer.pdf#page=5")

    result = plan_updates(ROWS, [flyer, page, same], min_confidence=0.85, today=TODAY)

    [update] = result.updates
    assert (update.new.price_eur, update.source) == ("1.39", MILK_PAGE)
    [item] = result.review  # the one agreeing with the applied offer is dropped
    assert (item.kind, item.scanned) == ("conflict", flyer)
    assert MILK_PAGE in item.reason


def test_other_products_read_on_a_product_page_are_ignored() -> None:
    on_milk_page = [
        offer(regular="1.32"),
        offer(GOUDA, regular="3.49", promo="2.99", until=date(2026, 11, 14)),
        offer(None, regular="2.29"),  # not ours, next to the page's own product
    ]

    result = plan_updates(
        ROWS, [seen(o, source=MILK_PAGE) for o in on_milk_page], min_confidence=0.85, today=TODAY
    )

    assert [u.product_id for u in result.updates] == [MILK]
    assert (result.review, result.ignored) == ([], 2)


def test_the_own_product_page_wins_over_a_more_confident_offers_page() -> None:
    page = seen(offer(regular="1.32", confidence=0.86))
    listing = seen(offer(regular="1.39", confidence=0.99), source=OFFERS_PAGE)

    result = plan_updates(ROWS, [listing, page], min_confidence=0.85, today=TODAY)

    [update] = result.updates
    assert (update.new.price_eur, update.source, update.change) == ("1.32", MILK_PAGE, "confirmed")
    [item] = result.review
    assert (item.kind, item.scanned) == ("conflict", listing)
    assert item.reason == f"another offer was applied: {MILK_PAGE} (0.86)"


def test_an_offers_page_adds_its_promotion_to_the_product_page_without_a_conflict() -> None:
    until = date(2026, 11, 14)
    page = seen(offer(regular="1.32", confidence=0.97))
    listing = seen(
        offer(regular="1.32", promo="0.99", until=until, confidence=0.9), source=OFFERS_PAGE
    )
    flyer = seen(offer(promo="0.99", until=until, confidence=0.88), source="flyer.pdf#page=1")

    result = plan_updates(ROWS, [page, listing, flyer], min_confidence=0.85, today=TODAY)

    [update] = result.updates
    assert update.new == PriceState("1.32", "0.99", "2026-11-14", "2026-11-10")
    assert (update.source, update.promo_source, update.change) == (MILK_PAGE, OFFERS_PAGE, "promo")
    assert result.review == []  # the flyer shows no regular price: nothing against it


def test_a_promotion_at_another_regular_price_is_not_added() -> None:
    page = seen(offer(regular="1.32", confidence=0.97))
    listing = seen(
        offer(regular="1.39", promo="0.99", until=date(2026, 11, 14), confidence=0.99),
        source=OFFERS_PAGE,
    )

    result = plan_updates(ROWS, [page, listing], min_confidence=0.85, today=TODAY)

    [update] = result.updates
    assert (update.new, update.promo_source) == (PriceState("1.32", "", "", "2026-11-10"), None)
    assert [(i.kind, i.scanned) for i in result.review] == [("conflict", listing)]


def test_without_its_product_page_the_most_confident_offer_wins() -> None:
    flyer = seen(offer(regular="1.35", confidence=0.9), source="flyer.pdf#page=2")
    listing = seen(offer(regular="1.39", confidence=0.97), source=OFFERS_PAGE)

    result = plan_updates(ROWS, [flyer, listing], min_confidence=0.85, today=TODAY)

    assert [(u.new.price_eur, u.source) for u in result.updates] == [("1.39", OFFERS_PAGE)]
    assert [(i.kind, i.scanned) for i in result.review] == [("conflict", flyer)]


def test_dead_product_urls_are_the_product_pages_gone_with_404_or_410() -> None:
    failures = [
        Failure(source=PROTEIN_PAGE, problem="HTTP 410", http_status=410),
        Failure(source=MILK_PAGE, problem="HTTP 503", http_status=503),  # may come back
        Failure(source=OFFERS_PAGE, problem="HTTP 404", http_status=404),  # not a product
        Failure(source=f"{MILK_PAGE}?x", problem="Timeout 45000ms exceeded"),
    ]

    assert dead_product_urls(ROWS, failures) == [DeadUrl(PROTEIN, "Hofer", 410, PROTEIN_PAGE)]


def test_updates_follow_the_csv_order() -> None:
    result = plan(offer(GOUDA, regular="4.19"), offer(MILK, regular="1.39"))

    assert [u.product_id for u in result.updates] == [MILK, GOUDA]


def test_the_review_file_lists_each_offer_with_its_reason_and_the_catalog_row(
    tmp_path: Path,
) -> None:
    new_product = offer(None, regular="2.99", promo="1.99", until=date(2026, 11, 14))
    result = plan_updates(
        ROWS,
        [seen(offer(regular="1.39", confidence=0.6)), seen(new_product, source=OFFERS_PAGE)],
        min_confidence=0.85,
        today=TODAY,
    )
    path = tmp_path / "scanner_review.json"
    dead = [DeadUrl(PROTEIN, "Hofer", 410, PROTEIN_PAGE)]

    write_review(path, result.review, scanned_on=TODAY, min_confidence=0.85, dead_urls=dead)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert (data["scanned_on"], data["min_confidence"]) == ("2026-11-10", 0.85)
    assert data["dead_product_url"] == [
        {"product_id": PROTEIN, "store": "Hofer", "http_status": 410, "source_url": PROTEIN_PAGE}
    ]
    low, new = data["items"]
    assert low["kind"] == "low_confidence"
    assert low["reason"] == "confidence 0.60 < 0.85"
    assert (low["store"], low["source"]) == ("Hofer", MILK_PAGE)
    assert low["offer"]["regular_price_eur"] == "1.39"  # exact cents, as a string
    assert low["catalog"] == {
        "price_eur": "1.32",
        "promo_price_eur": "",
        "promo_valid_until": "",
        "price_date": "2026-10-15",
    }
    assert new["kind"] == "not_in_catalog"
    assert new["catalog"] is None
    assert (new["offer"]["promo_price_eur"], new["offer"]["promo_valid_until"]) == (
        "1.99",
        "2026-11-14",
    )


def test_the_table_shows_old_and_new_prices() -> None:
    result = plan(offer(regular="1.39"), offer(GOUDA, promo="3.49", until=date(2026, 11, 14)))

    lines = format_updates(result.updates).splitlines()

    assert lines[0].split() == [
        "Store",
        "Product",
        "Price",
        "EUR",
        "Promo",
        "EUR",
        "Conf.",
        "Change",
    ]
    assert set(lines[1]) == {"-", " "}
    assert lines[2].split() == ["Hofer", MILK, "1.32", "->", "1.39", "-", "0.95", "price"]
    assert lines[3].split() == [
        "Hofer", GOUDA, "3.99", "-", "->", "3.49", "until", "2026-11-14", "0.95", "promo"
    ]  # fmt: skip


# --- updater: writing the CSV and catalog.json ---------------------------------------------


@pytest.mark.parametrize("source", [FROZEN_CATALOG_AT, DEFAULT_SOURCE])
def test_unchanged_rows_are_written_back_byte_for_byte(tmp_path: Path, source: Path) -> None:
    path = tmp_path / "catalog_at.csv"

    write_rows(path, read_rows(source))

    assert path.read_bytes() == source.read_bytes()


def test_applying_rewrites_only_the_changed_rows_and_rebuilds_the_catalog(
    tmp_path: Path,
) -> None:
    source = shutil.copy(FROZEN_CATALOG_AT, tmp_path / "catalog_at.csv")
    output = tmp_path / "catalog.json"
    result = plan(
        offer(regular="1.32", promo="0.99", until=date(2026, 11, 14)),
        offer(GOUDA, regular="4.19"),
    )

    build_report = save_catalog(apply_updates(ROWS, result.updates), source, output)

    before = FROZEN_CATALOG_AT.read_bytes().split(b"\r\n")
    after = source.read_bytes().split(b"\r\n")
    changed = [new.decode() for old, new in zip(before, after, strict=True) if old != new]
    assert [line.split(",")[0] for line in changed] == [MILK, GOUDA]
    assert ",1.32,0.99,2026-11-14," in changed[0] and changed[0].endswith(",2026-11-10,no")
    assert ",4.19,,," in changed[1]
    products = {p["id"]: p for p in json.loads(output.read_text(encoding="utf-8"))["products"]}
    milk = products[MILK]
    assert [milk[f] for f in ("price_eur", "regular_price_eur", "promo_price_eur")] == [
        0.99,
        1.32,
        0.99,
    ]
    assert (milk["promo_valid_until"], milk["price_date"]) == ("2026-11-14", "2026-11-10")
    assert products[GOUDA]["price_eur"] == 4.19
    assert "version at-2026-11-10" in build_report
    assert "Promotions running on 2026-11-10: 1" in build_report


def test_a_failing_build_writes_nothing(tmp_path: Path) -> None:
    source = shutil.copy(FROZEN_CATALOG_AT, tmp_path / "catalog_at.csv")
    output = tmp_path / "catalog.json"
    broken = with_row(MILK, promo_price_eur="0.99")  # no promo_valid_until

    with pytest.raises(BuildError, match=r"catalog_at\.csv:2 \(at-hofer-whole-milk-1l\)"):
        save_catalog(broken, source, output)

    assert source.read_bytes() == FROZEN_CATALOG_AT.read_bytes()
    assert not output.exists()


# --- LLM extractor (OpenAI mocked) ---------------------------------------------------------


def scanner_settings(**overrides: Any) -> ScannerSettings:
    values: dict[str, Any] = {
        "openai_api_key": "sk-test-not-a-real-key",
        "scanner_model": "test-model",
        "scanner_concurrency": 1,  # calls in capture order, for the scripted replies
        **overrides,
    }
    return ScannerSettings(_env_file=None, **values)


def reply_offer(**fields: Any) -> dict[str, Any]:
    return {
        "product_id": MILK,
        "raw_name_de": "Milsani Vollmilch 3,5%",
        "pack_size_desc": "1 l",
        "regular_price_eur": 1.32,
        "promo_price_eur": None,
        "promo_valid_from": None,
        "promo_valid_until": None,
        "confidence": 0.96,
        "notes": None,
        **fields,
    }


def queue_offers(fake_llm: FakeOpenAI, *offers: dict[str, Any]) -> None:
    fake_llm.queue_raw(json.dumps({"offers": list(offers)}))


def extract(
    fake_llm: FakeOpenAI, captures: list[Capture], **settings: Any
) -> tuple[list[ScannedOffer], list[Any]]:
    extractor = LLMExtractor(fake_llm.client, scanner_settings(**settings), TODAY)
    return asyncio.run(extractor.extract("Hofer", "Hofer hint.", HOFER, captures))


def test_the_extractor_parses_offers_into_decimals_and_dates(fake_llm: FakeOpenAI) -> None:
    queue_offers(
        fake_llm,
        reply_offer(promo_price_eur=0.99, promo_valid_until="2026-11-14"),
        reply_offer(product_id=None, raw_name_de="Bergkäse", regular_price_eur=12.9),
    )

    offers, failures = extract(fake_llm, [Capture(source=OFFERS_PAGE, text="Vollmilch € 1,32")])

    assert failures == []
    assert [(o.store, o.source) for o in offers] == [("Hofer", OFFERS_PAGE)] * 2
    milk, cheese = (o.offer for o in offers)
    assert (milk.product_id, milk.regular_price_eur, milk.promo_price_eur) == (
        MILK,
        Decimal("1.32"),
        Decimal("0.99"),
    )
    assert milk.promo_valid_until == date(2026, 11, 14)
    assert (cheese.product_id, cheese.regular_price_eur) == (None, Decimal("12.9"))


def test_the_extractor_sends_a_strict_schema_with_the_store_ids(fake_llm: FakeOpenAI) -> None:
    queue_offers(fake_llm)

    extract(fake_llm, [Capture(source=OFFERS_PAGE, text="Vollmilch € 1,32")])

    request = fake_llm.requests[0]
    assert (request["model"], request["temperature"]) == ("test-model", 0.0)
    schema = request["response_format"]["json_schema"]
    assert schema["strict"] is True
    product_id = schema["schema"]["$defs"]["ExtractedOffer"]["properties"]["product_id"]
    assert product_id["anyOf"][0]["enum"] == [p.id for p in HOFER]
    assert product_id["anyOf"][1] == {"type": "null"}
    system, user = request["messages"]
    assert "Austrian supermarket Hofer" in system["content"]
    assert "Return every product from our list" in system["content"]
    assert "Today is 2026-11-10" in system["content"]
    assert system["content"].endswith("Hofer hint.")
    products, page = (part["text"] for part in user["content"])
    assert f"{MILK} | Vollmilch 3,5% länger frisch | milk_whole | 1 l | 1.32" in products
    assert BANANAS not in products
    assert page == f"Page: {OFFERS_PAGE}\n\nVollmilch € 1,32"


def queue_product_page(fake_llm: FakeOpenAI, found: dict[str, Any] | None) -> None:
    fake_llm.queue_raw(json.dumps({"offer": found}))


def test_a_product_page_is_read_for_its_own_product_only(fake_llm: FakeOpenAI) -> None:
    queue_product_page(fake_llm, reply_offer(promo_price_eur=0.99, promo_valid_until="2026-11-14"))
    queue_offers(fake_llm, reply_offer(product_id=GOUDA, regular_price_eur=3.99))
    page_text = "Milsani Vollmilch 1 l € 1,32\nÄhnliche Produkte\nHolländischer Gouda € 3,99"

    offers, failures = extract(
        fake_llm,
        [Capture(source=MILK_PAGE, text=page_text), Capture(source=OFFERS_PAGE, text="Gouda")],
    )

    assert failures == []
    assert [(o.source, o.offer.product_id) for o in offers] == [
        (MILK_PAGE, MILK),
        (OFFERS_PAGE, GOUDA),
    ]
    assert offers[0].offer.promo_price_eur == Decimal("0.99")
    product_page, offers_page = fake_llm.requests
    # One offer, and only for this product: carousel products can't be returned.
    schema = product_page["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["offer"]
    assert schema["properties"]["offer"]["anyOf"][1] == {"type": "null"}
    product_id = schema["$defs"]["ExtractedOffer"]["properties"]["product_id"]
    assert product_id["anyOf"] == [{"type": "string", "enum": [MILK]}, {"type": "null"}]
    system, user = product_page["messages"]
    assert "Read only the page's main product" in system["content"]
    assert "Ähnliche Produkte" in system["content"]
    assert system["content"].endswith("Hofer hint.")
    ours, page = (part["text"] for part in user["content"])
    # The product's id, name and pack size, but not our price: the page's price is read.
    assert ours == f"Our product:\n{MILK} | Vollmilch 3,5% länger frisch | 1 l"
    assert page == f"Page: {MILK_PAGE}\n\n{page_text}"
    listing = offers_page["response_format"]["json_schema"]["schema"]
    assert listing["required"] == ["offers"]


def test_a_product_page_without_its_product_gives_no_offer(fake_llm: FakeOpenAI) -> None:
    queue_product_page(fake_llm, None)

    offers, failures = extract(fake_llm, [Capture(source=MILK_PAGE, text="Captcha")])

    assert (offers, failures) == ([], [])


def test_a_product_page_reply_naming_another_product_is_refused(fake_llm: FakeOpenAI) -> None:
    queue_product_page(fake_llm, reply_offer(product_id=GOUDA))

    offers, failures = extract(fake_llm, [Capture(source=MILK_PAGE, text="Gouda € 3,99")])

    assert offers == []
    assert [(f.source, f.problem) for f in failures] == [
        (MILK_PAGE, "reply didn't match the schema")
    ]


def test_flyer_images_are_sent_as_data_urls(fake_llm: FakeOpenAI) -> None:
    queue_offers(fake_llm)
    image = PageImage(b"\x89PNG fake", "image/png")

    extract(fake_llm, [Capture(source="flyer.pdf#page=1", images=(image,))])

    content = fake_llm.messages(0)[1]["content"]
    assert content[1]["text"] == "Page: flyer.pdf#page=1"
    assert content[2] == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,iVBORyBmYWtl", "detail": "high"},
    }


def test_long_page_text_is_cut(fake_llm: FakeOpenAI) -> None:
    queue_offers(fake_llm)

    extract(fake_llm, [Capture(source="page.txt", text="q" * 20_000)])

    page = fake_llm.messages(0)[1]["content"][1]["text"]
    assert page.endswith("q" * 100 + "\n[page text cut]")
    assert page.count("q") == 15_000


def test_a_failed_page_is_reported_and_the_others_are_still_read(fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_raw(None, refusal="I can't help with that.")
    fake_llm.queue_raw(json.dumps({"offers": [{"product_id": "not-a-hofer-id"}]}))
    fake_llm.queue_raw(json.dumps({"offers": []}), finish_reason="length")
    fake_llm.queue_status(500)
    queue_offers(fake_llm, reply_offer())
    captures = [Capture(source=f"page-{n}", text="Milch") for n in range(5)]

    offers, failures = extract(fake_llm, captures)

    assert [(f.source, f.problem) for f in failures] == [
        ("page-0", "model refused: I can't help with that."),
        ("page-1", "reply didn't match the schema"),
        ("page-2", "reply cut off at SCANNER_MAX_TOKENS"),
        ("page-3", "OpenAI error: InternalServerError"),
    ]
    assert [(o.source, o.offer.product_id) for o in offers] == [("page-4", MILK)]


@pytest.mark.parametrize(
    ("status", "message"), [(401, "rejected the API key"), (404, "refused model 'test-model'")]
)
def test_a_rejected_key_or_model_stops_the_scan(
    fake_llm: FakeOpenAI, status: int, message: str
) -> None:
    fake_llm.queue_status(status)

    with pytest.raises(ScannerError, match=message):
        extract(fake_llm, [Capture(source="page", text="Milch")] * 3)

    assert fake_llm.calls == 1  # the other pages were not sent


# --- browser pages (session mocked) ---------------------------------------------------------


class FakeSession:
    """Answers 410 for the protein yogurt's page, the page's URL as text otherwise."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    async def capture(self, url: str) -> Capture:
        self.urls.append(url)
        if url == PROTEIN_PAGE:
            raise HttpStatusError(410)
        return Capture(source=url, text=url)


def test_a_store_scan_reads_every_product_page_then_the_offers_page() -> None:
    session = FakeSession()

    captures, failures = asyncio.run(HoferAdapter().scan(session, HOFER))  # type: ignore[arg-type]

    assert session.urls == [*(p.source_url for p in HOFER), OFFERS_PAGE]
    assert len(captures) == len(HOFER)  # all but the gone page
    assert failures == [Failure(source=PROTEIN_PAGE, problem="HTTP 410", http_status=410)]


def test_a_product_counts_as_read_only_with_an_offer_from_its_own_page() -> None:
    log = ScanLog(
        scanned_on=TODAY,
        offers=[
            seen(offer(GOUDA, regular="3.99"), source=HOFER[1].source_url),
            seen(offer(MILK, promo="0.99", until=date(2026, 11, 14)), source=OFFERS_PAGE),
        ],
    )
    failures = [Failure(source=PROTEIN_PAGE, problem="HTTP 410", http_status=410)]

    unread = cli.unread_products([HoferAdapter()], ROWS, log, failures)

    assert HOFER[1].id == GOUDA
    assert MILK in unread  # named on the offers page only
    assert GOUDA not in unread
    assert PROTEIN not in unread  # reported as a dead URL instead
    assert len(unread) == len(HOFER) - 2


# --- local files (--from-files) -------------------------------------------------------------


def test_files_are_read_as_images_or_text(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "2.JPG").write_bytes(b"jpeg")
    (tmp_path / "pages" / "1.webp").write_bytes(b"webp")
    (tmp_path / "pages" / "notes.csv").write_text("ignored")
    (tmp_path / "shop.txt").write_text("  Vollmilch   3,5 %\n\n\t€ 1,32  \n", encoding="utf-8")

    captures = load_files([tmp_path / "shop.txt", tmp_path / "pages"])

    assert [(Path(c.source).name, c.text) for c in captures] == [
        ("shop.txt", "Vollmilch 3,5 %\n€ 1,32"),
        ("1.webp", None),
        ("2.JPG", None),
    ]
    assert [c.images for c in captures[1:]] == [
        (PageImage(b"webp", "image/webp"),),
        (PageImage(b"jpeg", "image/jpeg"),),
    ]


@pytest.mark.parametrize(
    ("name", "message"), [("missing.png", "no such file"), ("flyer.docx", "unsupported")]
)
def test_unreadable_files_are_refused(tmp_path: Path, name: str, message: str) -> None:
    if name.endswith(".docx"):
        (tmp_path / name).write_bytes(b"docx")

    with pytest.raises(ScannerError, match=message):
        load_files([tmp_path / name])


def test_pdfs_need_the_scanner_requirements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "pypdfium2", None)  # import fails, installed or not
    (tmp_path / "flyer.pdf").write_bytes(b"%PDF-1.7")

    with pytest.raises(ScannerError, match="pip install -r requirements-scraper.txt"):
        load_files([tmp_path / "flyer.pdf"])


def test_page_text_is_cleaned() -> None:
    assert clean_text("  a   b\n\n \n c\t\td ") == "a b\nc d"


def test_scanning_without_a_login_profile_asks_for_login(tmp_path: Path) -> None:
    session = BrowserSession(tmp_path / "shots", profile_dir=tmp_path / "no-profile")

    async def enter() -> None:
        async with session:
            pass

    with pytest.raises(ScannerError, match="run with --login first"):
        asyncio.run(enter())


# --- CLI ------------------------------------------------------------------------------------


@pytest.fixture
def paths(tmp_path: Path) -> dict[str, Path]:
    page = tmp_path / "hofer-page.txt"
    page.write_text("Milsani Vollmilch 1 l € 1,39", encoding="utf-8")
    return {
        "page": page,
        "source": Path(shutil.copy(FROZEN_CATALOG_AT, tmp_path / "catalog_at.csv")),
        "output": tmp_path / "catalog.json",
        "review": tmp_path / "scanner_review.json",
        "runs": tmp_path / "runs",
    }


def path_args(paths: dict[str, Path]) -> list[str]:
    return [
        "--source",
        str(paths["source"]),
        "--output",
        str(paths["output"]),
        "--review-file",
        str(paths["review"]),
        "--runs-dir",
        str(paths["runs"]),
    ]


def test_a_dry_run_prints_the_changes_and_writes_only_the_review(
    fake_llm: FakeOpenAI, paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    queue_offers(
        fake_llm,
        reply_offer(regular_price_eur=1.39),
        reply_offer(product_id=None, raw_name_de="Bergkäse", promo_price_eur=9.99),
    )
    argv = ["--store", "hofer", "--from-files", str(paths["page"]), *path_args(paths)]

    code = cli.main(argv, client=fake_llm.client, settings=scanner_settings(), today=TODAY)

    out = capsys.readouterr().out
    assert code == 0
    assert "1.32 -> 1.39" in out
    assert "For review: 1 offers" in out
    assert "Dry run: catalog unchanged" in out
    assert paths["source"].read_bytes() == FROZEN_CATALOG_AT.read_bytes()
    assert not paths["output"].exists()
    review = json.loads(paths["review"].read_text(encoding="utf-8"))
    assert [item["offer"]["raw_name_de"] for item in review["items"]] == ["Bergkäse"]
    assert (paths["runs"] / "last_offers.json").is_file()


def test_last_run_apply_writes_what_the_dry_run_showed_without_calling_openai(
    fake_llm: FakeOpenAI, paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    queue_offers(fake_llm, reply_offer(regular_price_eur=1.39))
    argv = ["--store", "hofer", "--from-files", str(paths["page"]), *path_args(paths)]
    cli.main(argv, client=fake_llm.client, settings=scanner_settings(), today=TODAY)

    code = cli.main(["--last-run", "--apply", *path_args(paths)], today=date(2026, 11, 20))

    assert code == 0
    assert fake_llm.calls == 1
    [milk] = [row for row in read_rows(paths["source"]) if row["id"] == MILK]
    assert (milk["price_eur"], milk["price_date"]) == ("1.39", "2026-11-10")  # the scan's day
    catalog = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert catalog["version"] == "at-2026-11-10"
    assert "Updated 1 row(s)" in capsys.readouterr().out


def test_dead_product_urls_are_printed_and_kept_in_the_review_after_last_run(
    paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    paths["runs"].mkdir()
    log = ScanLog(
        scanned_on=TODAY,
        offers=[seen(offer(regular="1.32"))],
        failures=[Failure(source=PROTEIN_PAGE, problem="HTTP 410", http_status=410)],
    )
    (paths["runs"] / "last_offers.json").write_text(log.model_dump_json(), encoding="utf-8")

    code = cli.main(["--last-run", *path_args(paths)])

    out = capsys.readouterr().out
    assert code == 0
    assert "Dead product URLs (HTTP 404/410): 1; update their source_url in catalog_at.csv:" in out
    assert f"  {PROTEIN}  HTTP 410  {PROTEIN_PAGE}" in out
    review = json.loads(paths["review"].read_text(encoding="utf-8"))
    assert [d["product_id"] for d in review["dead_product_url"]] == [PROTEIN]


def test_a_scan_keeps_its_failed_pages_for_last_run(
    fake_llm: FakeOpenAI, paths: dict[str, Path]
) -> None:
    fake_llm.queue_raw(None, refusal="No.")
    argv = ["--store", "hofer", "--from-files", str(paths["page"]), *path_args(paths)]

    cli.main(argv, client=fake_llm.client, settings=scanner_settings(), today=TODAY)

    log = ScanLog.model_validate_json((paths["runs"] / "last_offers.json").read_text())
    assert [(f.source, f.problem) for f in log.failures] == [
        (str(paths["page"]), "model refused: No.")
    ]


def test_last_run_without_a_previous_scan_fails(
    paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["--last-run", *path_args(paths)]) == 1
    assert "no previous scan" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["--from-files", "flyer.pdf"],  # whose flyer?
        ["--login", "--apply"],
        ["--dry-run", "--apply"],
        ["--min-confidence", "1.5"],
        ["--last-run", "--from-files", "flyer.pdf", "--store", "billa"],
    ],
)
def test_conflicting_flags_are_refused(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.parse_args(argv)
    assert exit_info.value.code == 2


# --- isolation from the app -----------------------------------------------------------------


def test_the_scanner_loads_without_its_browser_and_pdf_dependencies() -> None:
    assert cli.main  # imported at the top of this module
    assert "playwright" not in sys.modules
    assert "pypdfium2" not in sys.modules


def test_the_app_and_its_image_stay_free_of_the_scanner() -> None:
    app_code = "\n".join(p.read_text(encoding="utf-8") for p in (BACKEND / "app").rglob("*.py"))
    assert "price_scanner" not in app_code
    assert "playwright" not in app_code
    runtime = (BACKEND / "requirements.txt").read_text(encoding="utf-8").lower()
    assert not {"playwright", "pypdfium2", "pillow"} & set(runtime.replace("=", " ").split())
    ignored = (BACKEND / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert {".browser_profile/", "scripts/price_scanner/", "requirements-scraper.txt"} <= set(
        ignored
    )


def test_settings_default_to_a_deterministic_mini_model() -> None:
    settings = ScannerSettings(_env_file=None, openai_api_key="sk-test-not-a-real-key")
    assert (settings.scanner_model, settings.scanner_temperature) == ("gpt-4o-mini", 0.0)
