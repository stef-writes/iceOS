from __future__ import annotations

from pydantic import BaseModel


class PlannerPromptPack(BaseModel):
    system: str
    user_template: str


def default_planner_pack() -> PlannerPromptPack:
    return PlannerPromptPack(
        system=(
            "You are an expert workflow architect. Produce STRICT JSON only.\n"
            'Return either an object {\\"patches\\": [...] } or a top-level array [...].\n'
            'Each patch: {\\"action\\": \\"add_node|remove_node|update_node\\", \\"node\\": PartialNodeSpec?, \\"node_id\\": str?, \\"updates\\": object?}.\n'
            'When adding a node, minimally include: {id: string, type: \\"llm\\"|\\"tool\\", name: string, dependencies: []}.\n'
            "Never include commentary or markdown.\n"
        ),
        user_template=("Request: {request}\n" "Context: {canvas_state}\n"),
    )


__all__ = ["PlannerPromptPack", "default_planner_pack"]
