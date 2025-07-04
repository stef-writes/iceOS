from ice_sdk.agents import FlowDesignAgent, TestContextStore


def test_design_session():
    context = TestContextStore()
    agent = FlowDesignAgent(context)

    session = context.new_session()
    session.add_message("user", "I need to process support tickets")

    response = agent.generate_response(session)
    assert "ticketing systems" in response.text
    assert response.tool_calls == ["tool_discovery"]

    session.add_message("user", "We use Zendesk")
    final_response = agent.generate_response(session)
    assert "ZendeskWebhookTool" in final_response.text
