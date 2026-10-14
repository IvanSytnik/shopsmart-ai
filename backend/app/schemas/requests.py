from typing import Annotated, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from app.schemas.catalog import Country, DietTag

# Checked against the catalog's stores for `country` in the /generate route.
StoreName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Mode = Literal["shopping", "menu"]
Language = Literal["en", "uk", "de"]


T = TypeVar("T")


def _unique(values: list[T]) -> list[T]:
    if len(set(values)) != len(values):
        raise ValueError("must not contain duplicates")
    return values


class GenerateRequest(BaseModel):
    supermarkets: Annotated[
        list[StoreName],
        Field(min_length=1, max_length=5, json_schema_extra={"uniqueItems": True}),
        AfterValidator(_unique),
    ]
    budget: float = Field(ge=10, le=1000)
    preferences: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""
    family_size: int = Field(default=2, ge=1, le=10)
    language: Language = "en"
    mode: Mode = "shopping"
    days: int = Field(default=7, ge=1, le=7, description="Only used when mode is 'menu'.")
    # TODO(2B): not used by /generate yet; they will select catalog candidates
    # (ProductCatalog.candidates) once the LLM picks products by id.
    diets: Annotated[
        list[DietTag],
        Field(max_length=4, json_schema_extra={"uniqueItems": True}),
        AfterValidator(_unique),
    ] = []
    country: Country = "AT"
