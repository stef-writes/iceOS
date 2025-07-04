import click

from ice_sdk.agents.flow_design_agent import FlowDesignAgent
from ice_sdk.context import get_async_context


@click.command()
@click.option("--goal", help="Initial design goal to seed conversation")
def design(goal):
    """Interactive flow design assistant"""
    context = get_async_context()
    agent = FlowDesignAgent(context)

    with context.new_session() as session:
        if goal:
            session.add_message("user", f"Goal: {goal}")

        while True:
            response = agent.generate_response(session)
            click.echo(f"\nAssistant: {response.text}")

            if response.requires_input:
                user_input = click.prompt("Your response")
                session.add_message("user", user_input)
            else:
                break
