from backend.app.core.logging import get_logger
from fastapi import APIRouter


logger = get_logger()
router = APIRouter(prefix="/home")


@router.get("/")
def home():
    return {"message": "Welcome to the NextGen Bank API!"}
