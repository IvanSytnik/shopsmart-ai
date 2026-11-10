from typing import Annotated, get_args

from fastapi import APIRouter, Depends

from app.api.deps import get_catalog
from app.schemas.catalog import Category, Country, DietTag
from app.schemas.compare import ConceptsResponse
from app.schemas.responses import CatalogMeta
from app.services.catalog import ProductCatalog

router = APIRouter(prefix="/api/catalog")


@router.get("/meta", response_model=CatalogMeta)
def catalog_meta(catalog: Annotated[ProductCatalog, Depends(get_catalog)]) -> CatalogMeta:
    """What the form can offer: stores per country, diets, categories, price date."""
    return CatalogMeta(
        catalog_version=catalog.catalog.version,
        price_date=catalog.catalog.price_date,
        countries=catalog.stores_by_country(),
        diet_tags=list(get_args(DietTag)),
        categories=list(get_args(Category)),
    )


@router.get("/concepts", response_model=ConceptsResponse)
def catalog_concepts(
    catalog: Annotated[ProductCatalog, Depends(get_catalog)], country: Country = "AT"
) -> ConceptsResponse:
    """Every concept sold in `country`, for the compare form's autocomplete."""
    return ConceptsResponse(country=country, concepts=catalog.concepts(country))
