from app.schemas.trip import StartPlanRequest, TripBoard, TripDay, TripNode


def start_plan(request: StartPlanRequest) -> TripBoard:
    destination = request.intake.destination or "未命名目的地"
    return TripBoard(
        id="trip-demo-kyushu",
        title=f"{destination} 轻量行程",
        destination=destination,
        days=[
            TripDay(
                id="day-1",
                title="Day 1",
                nodes=[
                    TripNode(
                        id="arrival",
                        title="抵达并入住",
                        kind="arrival",
                        starts_at="15:00",
                        notes="先保持落地日轻松，后续由 Trip Board 细化。",
                    )
                ],
            )
        ],
    )
