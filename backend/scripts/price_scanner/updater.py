"""catalog_at.csv changes from scanned offers, and the review queue for the rest.

An offer changes a row only if it names one of the store's products, the model is at least
`min_confidence` sure and its prices pass `problems`. Every other offer goes to
data_src/scanner_review.json with the reason: low confidence, products not in the catalog
(new promotions worth adding), implausible prices, or a second offer for a product that
disagrees with the one applied.

A changed row describes the shelf on the scan day: the regular price seen (or the old one
if only a promo price was shown), the promotion seen, or none (an older promotion is
cleared), and `price_date` set to that day. An offer confirming the current prices only
moves `price_date`. Money is written with exactly 2 decimals, as in the rest of the CSV.
"""

import csv
import json
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Literal

from scripts.build_catalog import COLUMNS, DEFAULT_CONCEPTS, build, render, report
from scripts.price_scanner.schemas import ExtractedOffer, ScannedOffer, StoreProduct

CENT = Decimal("0.01")
# A regular price moving more than this is more likely another pack size or product.
MAX_REGULAR_CHANGE = Decimal("0.5")

ReviewKind = Literal["not_in_catalog", "unknown_product", "low_confidence", "rejected", "conflict"]
REVIEW_LABELS: dict[ReviewKind, str] = {
    "not_in_catalog": "not in the catalog",
    "unknown_product": "unknown product id",
    "low_confidence": "low confidence",
    "rejected": "failed checks",
    "conflict": "conflicting offer",
}


def money(value: Decimal) -> str:
    """ "1.50": rounded to the cent, always 2 decimals."""
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def store_products(rows: Iterable[dict[str, str]], store: str) -> list[StoreProduct]:
    return [StoreProduct.from_row(row) for row in rows if row["store"] == store]


@dataclass(frozen=True)
class PriceState:
    """The price columns of a catalog_at.csv row, as written there."""

    price_eur: str
    promo_price_eur: str
    promo_valid_until: str
    price_date: str

    @classmethod
    def of(cls, row: dict[str, str]) -> "PriceState":
        return cls(
            price_eur=row["price_eur"],
            promo_price_eur=row["promo_price_eur"],
            promo_valid_until=row["promo_valid_until"],
            price_date=row["price_date"],
        )

    def promo(self) -> str:
        if not self.promo_price_eur:
            return "-"
        return f"{self.promo_price_eur} until {self.promo_valid_until}"


@dataclass(frozen=True)
class RowUpdate:
    product_id: str
    store: str
    confidence: float
    source: str
    old: PriceState
    new: PriceState

    @property
    def change(self) -> str:
        """What changed besides price_date: "price", "promo", "promo ended" or "confirmed"."""
        parts = []
        if self.new.price_eur != self.old.price_eur:
            parts.append("price")
        if self.new.promo_price_eur:
            if self.new.promo() != self.old.promo():
                parts.append("promo")
        elif self.old.promo_price_eur:
            parts.append("promo ended")
        return ", ".join(parts) or "confirmed"


@dataclass(frozen=True)
class ReviewItem:
    kind: ReviewKind
    reason: str
    scanned: ScannedOffer
    catalog: PriceState | None  # the row's current prices, for a known product

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "reason": self.reason,
            "store": self.scanned.store,
            "source": self.scanned.source,
            "screenshot": self.scanned.screenshot,
            "offer": self.scanned.offer.model_dump(mode="json"),
            "catalog": asdict(self.catalog) if self.catalog else None,
        }


@dataclass(frozen=True)
class UpdatePlan:
    updates: list[RowUpdate]  # in CSV order
    review: list[ReviewItem]


def problems(offer: ExtractedOffer, row: dict[str, str], today: date) -> list[str]:
    """Why a confident offer can't be applied to `row` as seen on `today`; empty if it can."""
    regular, promo = offer.regular_price_eur, offer.promo_price_eur
    if regular is None and promo is None:
        return ["no price"]
    found = []
    old = Decimal(row["price_eur"])
    new_regular = old if regular is None else regular.quantize(CENT, rounding=ROUND_HALF_UP)
    for name, price in (("regular", regular), ("promo", promo)):
        if price is not None and price.quantize(CENT, rounding=ROUND_HALF_UP) <= 0:
            found.append(f"{name} price {price} is not above 0")
    if regular is not None and abs(new_regular - old) > old * MAX_REGULAR_CHANGE:
        found.append(
            f"regular price {money(old)} -> {money(new_regular)} moved more than "
            f"{MAX_REGULAR_CHANGE:.0%}: same product and pack size?"
        )
    if promo is not None:
        until, start = offer.promo_valid_until, offer.promo_valid_from
        if until is None:
            found.append("promotion without a last day")
        elif until < today:
            found.append(f"promotion ended on {until}")
        if start is not None and start > today:
            found.append(f"promotion starts on {start}")
        if promo.quantize(CENT, rounding=ROUND_HALF_UP) >= new_regular:
            found.append(
                f"promo price {money(promo)} is not below the regular price {money(new_regular)}"
            )
    if row["price_date"] > today.isoformat():
        found.append(f"the row's price_date {row['price_date']} is after the scan")
    return found


def new_state(offer: ExtractedOffer, row: dict[str, str], today: date) -> PriceState:
    """The row's price columns after applying `offer` (which passed `problems`)."""
    regular = offer.regular_price_eur if offer.regular_price_eur is not None else row["price_eur"]
    promo, until = "", ""
    if offer.promo_price_eur is not None and offer.promo_valid_until is not None:
        promo, until = money(offer.promo_price_eur), offer.promo_valid_until.isoformat()
    return PriceState(
        price_eur=money(Decimal(regular)),
        promo_price_eur=promo,
        promo_valid_until=until,
        price_date=today.isoformat(),
    )


def plan_updates(
    rows: Sequence[dict[str, str]],
    offers: Iterable[ScannedOffer],
    *,
    min_confidence: float,
    today: date,
) -> UpdatePlan:
    by_id = {row["id"]: row for row in rows}
    review: list[ReviewItem] = []
    accepted: dict[str, list[ScannedOffer]] = {}
    for scanned in offers:
        offer = scanned.offer
        row = by_id.get(offer.product_id) if offer.product_id else None
        kind: ReviewKind
        if offer.product_id is None:
            kind, reason = "not_in_catalog", "no matching product in the catalog"
        elif row is None or row["store"] != scanned.store:
            kind, reason, row = "unknown_product", f"no {scanned.store} product with this id", None
        elif offer.confidence < min_confidence:
            kind, reason = "low_confidence", f"confidence {offer.confidence:.2f} < {min_confidence}"
        elif found := problems(offer, row, today):
            kind, reason = "rejected", "; ".join(found)
        else:
            accepted.setdefault(offer.product_id, []).append(scanned)
            continue
        review.append(ReviewItem(kind, reason, scanned, PriceState.of(row) if row else None))

    updates = []
    for row in rows:
        group = accepted.get(row["id"])
        if not group:
            continue
        best = max(group, key=lambda s: s.offer.confidence)  # the first one on a tie
        new = new_state(best.offer, row, today)
        old = PriceState.of(row)
        updates.append(
            RowUpdate(row["id"], row["store"], best.offer.confidence, best.source, old, new)
        )
        for other in group:
            if other is not best and new_state(other.offer, row, today) != new:
                reason = f"another offer was applied: {best.source} ({best.offer.confidence:.2f})"
                review.append(ReviewItem("conflict", reason, other, old))
    return UpdatePlan(updates, review)


def apply_updates(
    rows: Sequence[dict[str, str]], updates: Iterable[RowUpdate]
) -> list[dict[str, str]]:
    new = {u.product_id: asdict(u.new) for u in updates}
    return [{**row, **new[row["id"]]} if row["id"] in new else row for row in rows]


def write_rows(path: Path, rows: Iterable[dict[str, str]]) -> None:
    """catalog_at.csv as the build reads it: its columns, CRLF line ends, minimal quoting."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def save_catalog(
    rows: Sequence[dict[str, str]],
    source: Path,
    output: Path,
    concepts: Path = DEFAULT_CONCEPTS,
) -> str:
    """Write `rows` to `source` and rebuild `output` (catalog.json); return the build report.

    The rows are built from a temporary copy first: if the build fails (BuildError), neither
    file is touched.
    """
    with tempfile.TemporaryDirectory() as folder:
        candidate = Path(folder) / source.name  # build errors name catalog_at.csv:<line>
        write_rows(candidate, rows)
        catalog, built_rows = build(candidate, concepts)
    write_rows(source, rows)
    output.write_text(render(catalog), encoding="utf-8")
    return report(catalog, built_rows)


def write_review(
    path: Path, review: Sequence[ReviewItem], *, scanned_on: date, min_confidence: float
) -> None:
    data = {
        "scanned_on": scanned_on.isoformat(),
        "min_confidence": min_confidence,
        "items": [item.as_json() for item in review],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def format_updates(updates: Sequence[RowUpdate]) -> str:
    """The changed rows as a table: old -> new regular price and promotion."""

    def arrow(old: str, new: str) -> str:
        return new if old == new else f"{old} -> {new}"

    table = [("Store", "Product", "Price EUR", "Promo EUR", "Conf.", "Change")]
    table += [
        (
            u.store,
            u.product_id,
            arrow(u.old.price_eur, u.new.price_eur),
            arrow(u.old.promo(), u.new.promo()),
            f"{u.confidence:.2f}",
            u.change,
        )
        for u in updates
    ]
    widths = [max(len(line[column]) for line in table) for column in range(len(table[0]))]
    lines = [
        "  ".join(cell.ljust(w) for cell, w in zip(line, widths, strict=True)).rstrip()
        for line in table
    ]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)
