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
NonEmptyStr = Annotated[str, Field(min_length=1, max_length=120)]
Grams = Annotated[float, Field(ge=0)]


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
    country: Country
    store: NonEmptyStr
    name: LocalizedName
    category: Category
    unit: Unit
    pack_size: float = Field(gt=0, description="Pack contents, in `unit`.")
    # Optional in the JSON; defaults from `unit` (kg -> g, l -> ml, pcs -> pcs, pack -> pack).
    portion_unit: PortionUnit
    price_eur: Decimal = Field(gt=0, decimal_places=2, description="Price of one pack.")
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
        return self


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: NonEmptyStr
    price_date: date = Field(description="Date the reference prices were collected.")
    products: list[Product]

    @model_validator(mode="after")
    def check_unique_ids(self) -> "Catalog":
        counts = Counter(p.id for p in self.products)
        duplicates = sorted(product_id for product_id, n in counts.items() if n > 1)
        if duplicates:
            raise ValueError(f"duplicate product ids: {', '.join(duplicates)}")
        return self
