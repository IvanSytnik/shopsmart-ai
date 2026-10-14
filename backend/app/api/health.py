from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "ShopSmart AI API", "version": "1.0.0"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
