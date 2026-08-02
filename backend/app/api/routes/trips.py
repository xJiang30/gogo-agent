from fastapi import APIRouter

from app.schemas.trip import StartPlanRequest, TripBoard
from app.services.trip_service import start_plan

router = APIRouter()


@router.post("/start-plan", response_model=TripBoard)
def create_trip_board(request: StartPlanRequest) -> TripBoard:
    return start_plan(request)
