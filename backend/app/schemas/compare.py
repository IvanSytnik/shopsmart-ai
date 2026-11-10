"""POST /compare and GET /api/catalog/concepts: a shopping list of concepts priced at each
chosen store, computed from the catalog without the LLM (see app.services.comparison).

Money is a `Decimal` in Python and a number rounded to cents in JSON, like the other responses.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, PlainSerializer

from app.schemas.catalog import Category, ConceptId, Country, DietTag, LocalizedName, Unit
from app.schemas.requests import StoreName, _unique

Eur = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class ConceptSummary(BaseModel):
    concept_id: str
    # Every product's names, in catalog order without repeats: the first is a display name,
    # all of them are worth searching.
    names: list[LocalizedName]
    category: Category
    unit: Unit
    stores: list[str]  # sorted
    reference_pack_size: float = Field(
        description=(
            "What quantity 1 means in POST /compare: the smallest pack of this concept in the "
            "country, in `unit`."
        )
    )


class ConceptsResponse(BaseModel):
    country: Country
    concepts: list[ConceptSummary]  # sorted by concept_id


class CompareItemRequest(BaseModel):
    concept_id: ConceptId
    quantity: int = Field(
        ge=1,
        le=50,
        description=(
            "How many reference packs (`reference_pack_size`) of the concept. A store with "
            "bigger packs buys fewer that hold at least as much."
        ),
    )


def _unique_concepts(items: list[CompareItemRequest]) -> list[CompareItemRequest]:
    _unique([item.concept_id for item in items])
    return items


class CompareRequest(BaseModel):
    items: Annotated[
        list[CompareItemRequest],
        Field(min_length=1, max_length=50),
        AfterValidator(_unique_concepts),
    ]
    stores: Annotated[
        list[StoreName],
        Field(min_length=1, max_length=5, json_schema_extra={"uniqueItems": True}),
        AfterValidator(_unique),
    ]
    diet_tags: Annotated[
        list[DietTag],
        Field(max_length=4, json_schema_extra={"uniqueItems": True}),
        AfterValidator(_unique),
    ] = []
    # The split basket is recommended once it saves at least this much over the best store.
    min_split_savings_eur: Decimal = Field(default=Decimal("3.00"), ge=0, le=1000, decimal_places=2)
    country: Country = "AT"


class MatchedStoreItem(BaseModel):
    concept_id: str
    product_id: str
    names: LocalizedName
    store: str
    packs_needed: int
    pack_size: float
    unit: Unit
    price_eur: Eur  # per pack, today: the promo price while a promotion runs
    regular_price_eur: Eur
    promo_price_eur: Eur | None  # only while the promotion runs
    promo_valid_until: date | None  # only while the promotion runs
    line_total_eur: Eur
    price_per_base_unit_eur: Eur = Field(description="Per 1 kg, 1 l, 1 piece or 1 pack (`unit`).")


class StoreComparison(BaseModel):
    store: str
    items: list[MatchedStoreItem]  # in request order
    total_eur: Eur
    promo_savings_eur: Eur  # regular minus promo price, over all packs
    missing_concepts: list[str]  # requested concepts this store doesn't sell (for the diets)


class SplitStoreGroup(BaseModel):
    store: str
    items: list[MatchedStoreItem]
    total_eur: Eur


class SplitBasket(BaseModel):
    """Each concept from the store where it costs least."""

    stores: list[SplitStoreGroup]  # only stores with items, sorted by name
    total_eur: Eur
    missing_concepts: list[str]  # sold by none of the stores (for the diets)
    total_savings_vs_worst_eur: Eur = Field(
        description=(
            "The most any single store charges above the split basket for the same items "
            "(the items that store has)."
        )
    )


Strategy = Literal["single_store", "split_basket"]


class CompareResponse(BaseModel):
    # Fewest missing concepts first, then the lowest total, then the store name.
    single_store_rankings: list[StoreComparison]
    split_basket: SplitBasket
    recommended_strategy: Strategy
    recommended_store: str | None  # the best single store; null for split_basket
    split_extra_savings_eur: Eur = Field(
        description="What the split basket saves over the best single store, on its items."
    )
    catalog_version: str
    price_date: date
