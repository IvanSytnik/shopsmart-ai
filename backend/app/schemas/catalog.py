"""Product price catalog (app/data/catalog.json): the only source of prices and nutrition."""

from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, model_validator

Country = Literal["AT", "DE"]
DietTag = Literal["vegetarian", "vegan", "gluten_free", "lactose_free"]
Unit = Literal["kg", "l", "pcs", "pack"]
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
    price_eur: Decimal = Field(gt=0, decimal_places=2, description="Price of one pack.")
    # Per pack; all four null for non-food.
    kcal: Grams | None
    protein_g: Grams | None
    fat_g: Grams | None
    carbs_g: Grams | None
    diet_tags: Annotated[list[DietTag], AfterValidator(_unique_tags)]
    source_url: HttpUrl
    price_date: date

    @model_validator(mode="after")
    def check_consistency(self) -> "Product":
        nutrition = (self.kcal, self.protein_g, self.fat_g, self.carbs_g)
        if any(v is None for v in nutrition) and any(v is not None for v in nutrition):
            raise ValueError("nutrition must be all set or all null")
        if "vegan" in self.diet_tags and "vegetarian" not in self.diet_tags:
            raise ValueError("a vegan product must also be tagged vegetarian")
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
