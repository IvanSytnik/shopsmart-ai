"""What the scanner reads off a page, and the shape the model must return it in.

The model returns `ExtractedOffer`s through Structured Outputs (strict mode, so every field
is required and optional values are `null`). `build_extraction_model` narrows
`product_id` to an enum of one store's product ids, so the model can only name products
the catalog has. Prices are only read, never computed, by the model; the updater checks
them before they reach the CSV.
"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, create_model

# The schema says "number" only: Pydantic's default schema for Decimal also allows a
# string, and a model writing "1,99" would fail validation of the whole reply.
Price = Annotated[Decimal, WithJsonSchema({"type": "number"})]

# OpenAI strict mode limits enum values per schema; above this, ids are plain strings and
# the updater rejects unknown ones (as app.schemas.llm does for plans).
MAX_ENUM_IDS = 500


class ExtractedOffer(BaseModel):
    """One product with a price, as read off a shop page or flyer."""

    model_config = ConfigDict(frozen=True)

    product_id: str | None = Field(
        description="Our id for the same product in the same pack size; null if none."
    )
    raw_name_de: str = Field(description="Product name as printed.")
    pack_size_desc: str = Field(description="Pack size as printed: '1 l', '6 x 0,5 l'.")
    regular_price_eur: Price | None = Field(
        description="Normal price of one pack (the struck-through one during a promotion)."
    )
    promo_price_eur: Price | None = Field(
        description="Promotional price of one pack that every shopper pays; null if none."
    )
    # Not stored in the CSV: a promotion that hasn't started yet goes to review.
    promo_valid_from: date | None = Field(description="First day of the promotion.")
    promo_valid_until: date | None = Field(description="Last day of the promotion.")
    confidence: float = Field(ge=0, le=1, description="How sure the match and prices are.")
    notes: str | None = Field(description="Conditions, doubts, or a similar product of ours.")


class StoreProduct(BaseModel):
    """A catalog_at.csv row as the scanner needs it: shown to the model, and the page to
    visit."""

    model_config = ConfigDict(frozen=True)

    id: str
    name_de: str
    concept_id: str
    pack_size: str
    unit: str
    price_eur: Decimal  # regular price
    source_url: str

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "StoreProduct":
        return cls.model_validate({field: row[field] for field in cls.model_fields})


class ScannedOffer(BaseModel):
    """An offer and where it was seen: the store scanned and the page (URL or file)."""

    model_config = ConfigDict(frozen=True)

    store: str
    source: str
    screenshot: str | None = None
    offer: ExtractedOffer


class ScanLog(BaseModel):
    """All offers of one run (.scanner/last_offers.json), for `--last-run`."""

    scanned_on: date
    offers: list[ScannedOffer]


class Failure(BaseModel):
    """A page that couldn't be loaded or read; the run goes on without it."""

    model_config = ConfigDict(frozen=True)

    source: str
    problem: str


def build_extraction_model(product_ids: Sequence[str]) -> type[BaseModel]:
    """The reply model for one store: `{"offers": [ExtractedOffer, ...]}` with
    `product_id` limited to `product_ids` (or null)."""
    id_type: Any
    if not product_ids:
        id_type = None
    elif len(product_ids) <= MAX_ENUM_IDS:
        id_type = Literal[tuple(product_ids)] | None
    else:
        id_type = str | None
    offer = create_model(
        "ExtractedOffer",
        __base__=ExtractedOffer,
        product_id=(
            id_type,
            Field(description=ExtractedOffer.model_fields["product_id"].description),
        ),
    )
    return create_model("Extraction", offers=(list[offer], ...))
