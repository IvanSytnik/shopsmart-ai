"""Product price catalog (app/data/catalog.json): the only source of prices and nutrition."""

from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, model_validator

Country = Literal["AT", "DE"]
DietTag = Literal["vegetarian", "vegan", "gluten_free", "lactose_free"]
Unit = Literal["kg", "l", "pcs", "pack"]
# What a menu portion (amount_per_person) is counted in. "pack" = a fraction of one pack.
PortionUnit = Literal["g", "ml", "pcs", "pack"]
DEFAULT_PORTION_UNIT: dict[Unit, PortionUnit] = {"kg": "g", "l": "ml", "pcs": "pcs", "pack": "pack"}
ALLOWED_PORTION_UNITS: dict[Unit, frozenset[PortionUnit]] = {
    "kg": frozenset({"g", "pack"}),
    "l": frozenset({"ml", "pack"}),
    "pcs": frozenset({"pcs", "pack"}),
    "pack": frozenset({"pack"}),
}
# Mirrors frontend/src/types.ts (ProductCategory).
Category = Literal[
    "vegetables",
    "fruits",
    "meat",
    "fish",
    "dairy",
    "bread",
    "beverages",
    "snacks",
    "frozen",
    "pantry",
    "cleaning",
    "hygiene",
    "other",
]
# Not food: diet filters don't apply and nutrition is null.
NON_FOOD_CATEGORIES: frozenset[Category] = frozenset({"cleaning", "hygiene"})

Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)]
# Kind of product and its nominal size, shared by equivalent products in every store:
# `milk_whole_1l`, `eggs_10pk`, `butter_250g`.
ConceptId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$", max_length=80)]
NonEmptyStr = Annotated[str, Field(min_length=1, max_length=120)]
Grams = Annotated[float, Field(ge=0)]
Money = Annotated[Decimal, Field(gt=0, decimal_places=2)]


def _unique_tags(tags: list[DietTag]) -> list[DietTag]:
    if len(set(tags)) != len(tags):
        raise ValueError("diet_tags must not contain duplicates")
    return tags


class LocalizedName(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    en: NonEmptyStr
    uk: NonEmptyStr
    de: NonEmptyStr


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Slug
    concept_id: ConceptId = Field(
        description="Same for equivalent products in other stores, e.g. `milk_whole_1l`."
    )
    country: Country
    store: NonEmptyStr
    name: LocalizedName
    category: Category
    unit: Unit
    pack_size: float = Field(gt=0, description="Pack contents, in `unit`.")
    # Optional in the JSON; defaults from `unit` (kg -> g, l -> ml, pcs -> pcs, pack -> pack).
    portion_unit: PortionUnit
    price_eur: Money = Field(
        description=(
            "Price of one pack, the one every plan is priced with: the promo price while a "
            "promotion runs, the regular price otherwise."
        )
    )
    # Null in catalogs from before promotions: price_eur is then the regular price.
    regular_price_eur: Money | None = None
    promo_price_eur: Money | None = None
    promo_valid_until: date | None = Field(default=None, description="Last day of the promotion.")
    # Per pack; all four null for non-food.
    kcal: Grams | None
    protein_g: Grams | None
    fat_g: Grams | None
    carbs_g: Grams | None
    diet_tags: Annotated[list[DietTag], AfterValidator(_unique_tags)]
    source_url: HttpUrl
    price_date: date

    @model_validator(mode="before")
    @classmethod
    def default_portion_unit(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("portion_unit") is None:
            unit = data.get("unit")
            if unit in DEFAULT_PORTION_UNIT:
                return {**data, "portion_unit": DEFAULT_PORTION_UNIT[unit]}
        return data

    @model_validator(mode="after")
    def check_consistency(self) -> "Product":
        nutrition = (self.kcal, self.protein_g, self.fat_g, self.carbs_g)
        if any(v is None for v in nutrition) and any(v is not None for v in nutrition):
            raise ValueError("nutrition must be all set or all null")
        if "vegan" in self.diet_tags and "vegetarian" not in self.diet_tags:
            raise ValueError("a vegan product must also be tagged vegetarian")
        # pcs/pack count whole things; a fractional weight belongs in kg or l.
        if self.unit in ("pcs", "pack") and not self.pack_size.is_integer():
            raise ValueError(f"pack_size must be a whole number for unit {self.unit!r}")
        if self.portion_unit not in ALLOWED_PORTION_UNITS[self.unit]:
            raise ValueError(f"portion_unit {self.portion_unit!r} doesn't fit unit {self.unit!r}")
        self._check_promotion()
        return self

    def _check_promotion(self) -> None:
        if (self.promo_price_eur is None) != (self.promo_valid_until is None):
            raise ValueError("promo_price_eur and promo_valid_until must be set together")
        if self.promo_price_eur is not None and self.promo_valid_until is not None:
            if self.regular_price_eur is None:
                raise ValueError("a promotion needs regular_price_eur")
            if self.promo_price_eur >= self.regular_price_eur:
                raise ValueError("promo_price_eur must be below regular_price_eur")
            if self.promo_valid_until < self.price_date:
                raise ValueError("promo_valid_until must not be before price_date")
        if self.regular_price_eur is not None and self.price_eur not in (
            self.regular_price_eur,
            self.promo_price_eur,
        ):
            raise ValueError("price_eur must be regular_price_eur or promo_price_eur")

    def promo_runs_on(self, day: date) -> bool:
        """Whether the promotion still runs on `day` (it runs from `price_date`, when seen)."""
        return self.promo_valid_until is not None and day <= self.promo_valid_until

    def price_on(self, day: date) -> Decimal:
        """Price of one pack on `day`: the promo price until the promotion ends, then the
        regular price."""
        if self.promo_price_eur is not None and self.promo_runs_on(day):
            return self.promo_price_eur
        if self.regular_price_eur is not None:
            return self.regular_price_eur
        return self.price_eur

    def priced_on(self, day: date) -> "Product":
        """This product with `price_eur` set to its price on `day`."""
        price = self.price_on(day)
        return self if price == self.price_eur else self.model_copy(update={"price_eur": price})


class Concept(BaseModel):
    """A kind of product (`Product.concept_id`), named for shoppers picking from a list."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    concept_id: ConceptId
    name: LocalizedName = Field(
        description="Neutral, without store brands or variants: 'Butter', not 'Clever Teebutter'."
    )


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: NonEmptyStr
    price_date: date = Field(description="Date the reference prices were collected.")
    products: list[Product]
    # A name for every concept_id of the products, sorted by id. The build writes no others;
    # extra ones are ignored, so a cut-down catalog needn't prune them.
    concepts: list[Concept] = []

    @model_validator(mode="after")
    def check_unique_ids(self) -> "Catalog":
        counts = Counter(p.id for p in self.products)
        duplicates = sorted(product_id for product_id, n in counts.items() if n > 1)
        if duplicates:
            raise ValueError(f"duplicate product ids: {', '.join(duplicates)}")
        return self

    @model_validator(mode="after")
    def check_prices_as_of_price_date(self) -> "Catalog":
        stale = [p.id for p in self.products if p.price_eur != p.price_on(self.price_date)]
        if stale:
            raise ValueError(
                f"price_eur must be the price on the catalog's price_date {self.price_date} "
                f"(regular price once a promotion has ended): {', '.join(stale)}"
            )
        return self

    @model_validator(mode="after")
    def check_concepts(self) -> "Catalog":
        counts = Counter(c.concept_id for c in self.concepts)
        problems = [
            f"{what}: {', '.join(sorted(ids))}"
            for what, ids in (
                ("concepts named twice", {i for i, n in counts.items() if n > 1}),
                ("concepts without a name", {p.concept_id for p in self.products} - counts.keys()),
            )
            if ids
        ]
        if problems:
            raise ValueError("; ".join(problems))
        return self
