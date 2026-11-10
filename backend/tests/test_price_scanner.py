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
from scripts.price_scanner.browser import BrowserSession
from scripts.price_scanner.capture import Capture, PageImage, clean_text, load_files
from scripts.price_scanner.config import ScannerError, ScannerSettings
from scripts.price_scanner.extractors.llm_extractor import LLMExtractor
from scripts.price_scanner.schemas import ExtractedOffer, ScannedOffer
from scripts.price_scanner.updater import (
    PriceState,
    UpdatePlan,
    apply_updates,
    format_updates,
    money,
    plan_updates,
    save_catalog,
    store_products,
    write_review,
    write_rows,
)
from tests.conftest import FakeOpenAI

TODAY = date(2026, 11, 10)
ROWS = read_rows(DEFAULT_SOURCE)  # every row has price_date 2026-10-15, no promotion
MILK = "at-hofer-whole-milk-1l"  # Hofer, €1.32
GOUDA = "at-hofer-gouda-450g"  # Hofer, €3.99
BANANAS = "at-billa-bananas-1kg"  # Billa
MILK_PAGE = "https://www.hofer.at/produkt/milsani-vollmilch-laenger-frisch-000000000000106876"
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


def seen(o: ExtractedOffer, store: str = "Hofer", source: str = MILK_PAGE) -> ScannedOffer:
    return ScannedOffer(store=store, source=source, offer=o)


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

    [item] = plan(new).review

    assert (item.kind, item.catalog, item.scanned.offer) == ("not_in_catalog", None, new)


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


def test_updates_follow_the_csv_order() -> None:
    result = plan(offer(GOUDA, regular="4.19"), offer(MILK, regular="1.39"))

    assert [u.product_id for u in result.updates] == [MILK, GOUDA]


def test_the_review_file_lists_each_offer_with_its_reason_and_the_catalog_row(
    tmp_path: Path,
) -> None:
    result = plan(
        offer(regular="1.39", confidence=0.6),
        offer(None, regular="2.99", promo="1.99", until=date(2026, 11, 14), confidence=0.9),
    )
    path = tmp_path / "scanner_review.json"

    write_review(path, result.review, scanned_on=TODAY, min_confidence=0.85)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert (data["scanned_on"], data["min_confidence"]) == ("2026-11-10", 0.85)
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


def test_unchanged_rows_are_written_back_byte_for_byte(tmp_path: Path) -> None:
    path = tmp_path / "catalog_at.csv"

    write_rows(path, ROWS)

    assert path.read_bytes() == DEFAULT_SOURCE.read_bytes()


def test_applying_rewrites_only_the_changed_rows_and_rebuilds_the_catalog(
    tmp_path: Path,
) -> None:
    source = shutil.copy(DEFAULT_SOURCE, tmp_path / "catalog_at.csv")
    output = tmp_path / "catalog.json"
    result = plan(
        offer(regular="1.32", promo="0.99", until=date(2026, 11, 14)),
        offer(GOUDA, regular="4.19"),
    )

    build_report = save_catalog(apply_updates(ROWS, result.updates), source, output)

    before = DEFAULT_SOURCE.read_bytes().split(b"\r\n")
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
    source = shutil.copy(DEFAULT_SOURCE, tmp_path / "catalog_at.csv")
    output = tmp_path / "catalog.json"
    broken = with_row(MILK, promo_price_eur="0.99")  # no promo_valid_until

    with pytest.raises(BuildError, match=r"catalog_at\.csv:2 \(at-hofer-whole-milk-1l\)"):
        save_catalog(broken, source, output)

    assert source.read_bytes() == DEFAULT_SOURCE.read_bytes()
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

    offers, failures = extract(fake_llm, [Capture(source=MILK_PAGE, text="Vollmilch € 1,32")])

    assert failures == []
    assert [(o.store, o.source) for o in offers] == [("Hofer", MILK_PAGE)] * 2
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

    extract(fake_llm, [Capture(source=MILK_PAGE, text="Vollmilch € 1,32")])

    request = fake_llm.requests[0]
    assert (request["model"], request["temperature"]) == ("test-model", 0.0)
    schema = request["response_format"]["json_schema"]
    assert schema["strict"] is True
    product_id = schema["schema"]["$defs"]["ExtractedOffer"]["properties"]["product_id"]
    assert product_id["anyOf"][0]["enum"] == [p.id for p in HOFER]
    assert product_id["anyOf"][1] == {"type": "null"}
    system, user = request["messages"]
    assert "Austrian supermarket Hofer" in system["content"]
    assert "Today is 2026-11-10" in system["content"]
    assert system["content"].endswith("Hofer hint.")
    products, page = (part["text"] for part in user["content"])
    assert f"{MILK} | Vollmilch 3,5% länger frisch | milk_whole | 1 l | 1.32" in products
    assert BANANAS not in products
    assert page.startswith(f"Page: {MILK_PAGE}\nThe product page of our {MILK}")
    assert page.endswith("Vollmilch € 1,32")


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
        "source": Path(shutil.copy(DEFAULT_SOURCE, tmp_path / "catalog_at.csv")),
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
    assert paths["source"].read_bytes() == DEFAULT_SOURCE.read_bytes()
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
