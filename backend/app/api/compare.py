import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_catalog
from app.errors import AppError
from app.schemas.compare import CompareRequest, CompareResponse
from app.services.catalog import ProductCatalog
from app.services.comparison import compare

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/compare", response_model=CompareResponse)
def compare_stores(
    compare_request: CompareRequest,
    catalog: Annotated[ProductCatalog, Depends(get_catalog)],
) -> CompareResponse:
    """A shopping list priced at each store, and the cheapest split across them.

    Computed from the catalog only: no LLM call, so no rate limit or daily cap like /generate.
    """
    known_stores = catalog.stores_by_country()[compare_request.country]
    if unknown := [s for s in compare_request.stores if s not in known_stores]:
        logger.info("Unknown stores for %s: %s", compare_request.country, unknown)
        raise AppError(422, "unknown_store", "Unknown store for the selected country")
    return compare(catalog, compare_request)
