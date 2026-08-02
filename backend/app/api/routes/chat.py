from fastapi import APIRouter

from app.schemas.intake import IntakeRequest, IntakeResponse
from app.services.intake_service import collect_trip_intake

router = APIRouter()


@router.post("/intake", response_model=IntakeResponse)
def intake(request: IntakeRequest) -> IntakeResponse:
    return collect_trip_intake(request)
