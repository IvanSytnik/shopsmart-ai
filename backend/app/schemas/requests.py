from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    supermarkets: list[str]
    budget: float = Field(gt=0, le=10000)
    preferences: str = ""
    family_size: int = Field(ge=1, le=20, default=2)
    language: str = "en"
    mode: str = "shopping"
    days: int | None = 7
