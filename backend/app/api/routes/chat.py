from fastapi import APIRouter

from app.schemas.intake import IntakeRequest, IntakeResponse
from app.services.intake_service import collect_trip_intake

router = APIRouter()


@router.post("/intake", response_model=IntakeResponse)
async def intake(request: IntakeRequest) -> IntakeResponse:
    return await collect_trip_intake(request)
