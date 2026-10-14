from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

Store = Literal["Lidl", "Aldi", "Edeka", "Rewe", "Kaufland"]
Mode = Literal["shopping", "menu"]
Language = Literal["en", "uk", "de"]


def _unique(stores: list[Store]) -> list[Store]:
    if len(set(stores)) != len(stores):
        raise ValueError("supermarkets must not contain duplicates")
    return stores


class GenerateRequest(BaseModel):
    supermarkets: Annotated[
        list[Store],
        Field(min_length=1, max_length=5, json_schema_extra={"uniqueItems": True}),
        AfterValidator(_unique),
    ]
    budget: float = Field(ge=10, le=1000)
    preferences: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""
    family_size: int = Field(default=2, ge=1, le=10)
    language: Language = "en"
    mode: Mode = "shopping"
    days: int = Field(default=7, ge=1, le=7, description="Only used when mode is 'menu'.")
