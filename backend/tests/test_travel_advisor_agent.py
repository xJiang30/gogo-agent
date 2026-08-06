from app.agents.travel_advisor import create_travel_advisor


def test_travel_advisor_has_intake_inspection_tool():
    agent = create_travel_advisor()

    assert [tool.name for tool in agent.tools] == ["inspect_intake_fields"]
