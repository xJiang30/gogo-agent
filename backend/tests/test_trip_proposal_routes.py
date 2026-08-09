from fastapi.testclient import TestClient

from app.main import app
from app.services import trip_service

client = TestClient(app)


def setup_function():
    trip_service.clear_trip_state()


def test_create_and_apply_trip_board_proposal_over_api():
    board_response = client.post(
        "/trips/start-plan",
        json={"intake": {"destination": "九州"}},
    )
    board = board_response.json()

    proposal_response = client.post(
        f"/trips/{board['id']}/proposals",
        json={
            "summary": "加一个晚餐节点。",
            "mutations": [
                {
                    "action": "add_node",
                    "day_id": "day-1",
                    "node": {
                        "id": "dinner",
                        "title": "天神拉面晚餐",
                        "kind": "meal",
                        "starts_at": "18:30",
                    },
                }
            ],
        },
    )

    assert proposal_response.status_code == 200
    proposal = proposal_response.json()
    assert proposal["requires_approval"] is True
    assert proposal["status"] == "pending"

    apply_response = client.post(
        f"/trips/{board['id']}/proposals/{proposal['id']}/apply",
        json={"approved": True},
    )

    assert apply_response.status_code == 200
    body = apply_response.json()
    assert body["proposal"]["status"] == "applied"
    assert body["assistant_message"] == "已应用。"
    assert body["trip_board"]["days"][0]["nodes"][-1]["id"] == "dinner"


def test_apply_trip_board_proposal_rejects_missing_approval_over_api():
    board_response = client.post(
        "/trips/start-plan",
        json={"intake": {"destination": "九州"}},
    )
    board = board_response.json()
    proposal_response = client.post(
        f"/trips/{board['id']}/proposals",
        json={
            "summary": "加一个晚餐节点。",
            "mutations": [
                {
                    "action": "add_node",
                    "day_id": "day-1",
                    "node": {
                        "id": "dinner",
                        "title": "天神拉面晚餐",
                        "kind": "meal",
                        "starts_at": "18:30",
                    },
                }
            ],
        },
    )
    proposal = proposal_response.json()

    apply_response = client.post(
        f"/trips/{board['id']}/proposals/{proposal['id']}/apply",
        json={"approved": False},
    )

    assert apply_response.status_code == 400
