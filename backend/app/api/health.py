from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_catalog
from app.services.catalog import ProductCatalog

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "ShopSmart AI API", "version": "1.0.0"}


@router.get("/health")
def health(catalog: Annotated[ProductCatalog, Depends(get_catalog)]) -> dict[str, str]:
    return {"status": "healthy", "catalog_version": catalog.catalog.version}
