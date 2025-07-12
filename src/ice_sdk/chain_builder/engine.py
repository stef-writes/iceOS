"""Chain Builder engine – relocated from ice_cli.chain_builder.engine.

Stateless helper to drive the interactive *Chain Builder* flow.  The public
API is stable: start(), next_question(), submit_answer(), render_chain(),
render_mermaid(), validate().
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from ice_sdk.models.node_models import (  # noqa: F401 – typings only
    AiNodeConfig,
    ToolNodeConfig,
)

__all__ = [
    "ChainDraft",
    "BuilderEngine",
    "Question",
]


@dataclass
class Question:  # noqa: D401 – simple container
    key: str
    prompt: str
    choices: Optional[List[str]] = None  # None → free text


@dataclass
class ChainDraft:  # noqa: D401 – mutable builder state
    name: str = "my_chain"
    nodes: List[dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    total_nodes: int = 0
    persist_interm_outputs: Optional[bool] = None

    def save(self) -> None:
        """Persist *self* under .ice/builder.draft.json (best-effort)."""
        ice_dir = Path.cwd() / ".ice"
        ice_dir.mkdir(exist_ok=True)
        (ice_dir / "builder.draft.json").write_text(json.dumps(asdict(self), indent=2))


class BuilderEngine:  # noqa: D401 – stateless helper
    """State-machine implementing the linear M0 Q&A flow."""

    # ------------------------------------------------------------------ engine lifecycle
    @staticmethod
    def start(total_nodes: int, chain_name: str | None = None) -> ChainDraft:
        return ChainDraft(name=chain_name or "my_chain", total_nodes=total_nodes)

    # ------------------------------------------------------------------ question flow
    @staticmethod
    def next_question(draft: ChainDraft) -> Optional[Question]:
        if draft.persist_interm_outputs is None:
            return Question(
                key="persist",
                prompt="Persist intermediate outputs?",
                choices=["y", "n"],
            )

        node_idx = len(draft.nodes) - (1 if draft.current_step < 1 else 0)

        if draft.current_step == 0:
            return Question(key="type", prompt="Node type", choices=["ai", "tool"])
        elif draft.current_step == 1:
            return Question(key="name", prompt="Node name")
        elif draft.current_step == 2:
            if draft.nodes and draft.nodes[-1]["type"] == "ai":
                return Question(key="model", prompt="Model (ai only)")
            draft.current_step += 1
            return BuilderEngine.next_question(draft)
        elif draft.current_step == 3:
            if draft.nodes and draft.nodes[-1]["type"] == "ai":
                return Question(
                    key="tools", prompt="Allowed tools (comma-separated, blank=all)"
                )
            draft.current_step += 1
            return BuilderEngine.next_question(draft)
        elif draft.current_step == 4:
            available_ids = [f"n{i}" for i in range(node_idx)]
            return Question(
                key="deps",
                prompt=(
                    "Depends on (comma-separated IDs, blank=auto-prev) "
                    f"[available: {', '.join(available_ids)}]"
                ),
            )
        elif draft.current_step == 5:
            return Question(key="adv", prompt="Advanced settings?", choices=["y", "n"])
        elif draft.current_step == 6:
            if draft.nodes[-1].get("adv") == "y":
                return Question(key="retries", prompt="Retries (int)")
            draft.current_step = 0
            return None
        elif draft.current_step == 7:
            return Question(key="timeout", prompt="Timeout seconds (int)")
        elif draft.current_step == 8:
            return Question(key="cache", prompt="Enable cache?", choices=["y", "n"])
        return None

    # ------------------------------------------------------------------ answer submission
    @staticmethod
    def submit_answer(draft: ChainDraft, key: str, answer: str) -> None:
        if key == "persist" and draft.persist_interm_outputs is None:
            draft.persist_interm_outputs = answer.lower().startswith("y")
            draft.save()
            return

        if draft.current_step == 0 and key == "type":
            draft.nodes.append({"type": answer})
            draft.current_step += 1
        elif draft.current_step == 1 and key == "name":
            draft.nodes[-1]["name"] = answer
            draft.current_step += 1
        elif draft.current_step == 2 and key == "model":
            if draft.nodes[-1]["type"] == "ai":
                draft.nodes[-1]["model"] = answer
                draft.current_step += 1
                draft.save()
                return
            draft.current_step += 1
        elif draft.current_step == 3 and key == "tools":
            tools = [t.strip() for t in answer.split(",") if t.strip()]
            draft.nodes[-1]["tools"] = tools
            draft.current_step += 1
            draft.save()
            return
        elif draft.current_step in (2, 3, 4) and key == "deps":
            deps = [d.strip() for d in answer.split(",") if d.strip()]
            if not deps and len(draft.nodes) > 1:
                deps = [f"n{len(draft.nodes)-2}"]
            draft.nodes[-1]["dependencies"] = deps
            draft.current_step = 5
        elif draft.current_step == 5 and key == "adv":
            draft.nodes[-1]["adv"] = answer.lower()
            if answer.lower().startswith("y"):
                draft.current_step += 1
            else:
                draft.current_step = 0
        elif draft.current_step == 6 and key == "retries":
            try:
                draft.nodes[-1]["retries"] = int(answer)
            except ValueError:
                draft.nodes[-1]["retries"] = 0
            draft.current_step += 1
        elif draft.current_step == 7 and key == "timeout":
            try:
                draft.nodes[-1]["timeout"] = int(answer)
            except ValueError:
                draft.nodes[-1]["timeout"] = 0
            draft.current_step += 1
        elif draft.current_step == 8 and key == "cache":
            draft.nodes[-1]["cache"] = answer.lower().startswith("y")
            draft.current_step = 0

        draft.save()

    # ------------------------------------------------------------------ rendering
    @staticmethod
    def _common_node_extras(node: dict[str, Any]) -> list[str]:
        extras = []
        for key in ("retries", "timeout", "cache"):
            if key in node:
                if key == "cache":
                    extras.append(f"use_cache={node[key]}")
                else:
                    extras.append(f"{key}={node[key]}")
        return extras

    @staticmethod
    def render_chain(draft: ChainDraft) -> str:
        node_lines: List[str] = []
        for idx, node in enumerate(draft.nodes):
            node_id = f"n{idx}"
            deps_str = node.get("dependencies", [])
            extra_str = (
                (", " + ", ".join(BuilderEngine._common_node_extras(node)))
                if BuilderEngine._common_node_extras(node)
                else ""
            )
            if node["type"] == "ai":
                tools_str = ""
                if node.get("tools"):
                    tools_list = (
                        "[" + ", ".join([f'"{t}"' for t in node["tools"]]) + "]"
                    )
                    tools_str = f", tools={tools_list}"
                node_lines.append(
                    f"    AiNodeConfig(id=\"{node_id}\", type=\"ai\", name=\"{node['name']}\", model=\"{node.get('model','gpt-3.5-turbo')}\", prompt=\"# TODO\", llm_config={{'provider': 'openai'}}, dependencies={deps_str}{tools_str}{extra_str}),"
                )
            else:
                node_lines.append(
                    f"    ToolNodeConfig(id=\"{node_id}\", type=\"tool\", name=\"{node['name']}\", tool_name=\"echo\", tool_args={{}}, dependencies={deps_str}{extra_str}),"
                )

        nodes_block = "\n".join(node_lines)
        template = (
            f'"""{draft.name} – generated by Chain Builder"""\n\n'
            "from __future__ import annotations\n\n"
            "from typing import List\n\n"
            "from ice_orchestrator.script_chain import ScriptChain\n"
            "from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig\n"
            "from ice_sdk.tools.system.sum_tool import SumTool\n\n"
            "nodes: List[AiNodeConfig | ToolNodeConfig] = [\n"
            f"{nodes_block}\n"  # noqa: E501
            "]\n\n"
            f'chain = ScriptChain(nodes=nodes, tools=[SumTool()], name="{draft.name}", persist_intermediate_outputs={draft.persist_interm_outputs if draft.persist_interm_outputs is not None else True})\n\n'
            'if __name__ == "__main__":\n    import asyncio, rich; rich.print(asyncio.run(chain.execute()).model_dump())\n'
        )
        return textwrap.dedent(template)

    @staticmethod
    def render_mermaid(draft: ChainDraft) -> str:
        lines: list[str] = ["graph LR"]
        for idx, node in enumerate(draft.nodes):
            node_id = f"n{idx}"
            label = f"{node['type'].upper()}: {node.get('name', '')}".strip()
            lines.append(f"    {node_id}[{label}]")
            deps = node.get("dependencies")
            if deps:
                for dep in deps:
                    lines.append(f"    {dep} --> {node_id}")
            elif idx > 0:
                prev_id = f"n{idx - 1}"
                lines.append(f"    {prev_id} --> {node_id}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ validation
    @staticmethod
    def validate(draft: ChainDraft) -> list[str]:
        errors: list[str] = []
        names_seen: set[str] = set()
        for n in draft.nodes:
            if "name" in n:
                if n["name"] in names_seen:
                    errors.append(f"Duplicate node name '{n['name']}'.")
                names_seen.add(n["name"])
        for idx, n in enumerate(draft.nodes):
            for dep in n.get("dependencies", []):
                try:
                    dep_idx = int(dep.lstrip("n"))
                except ValueError:
                    errors.append(f"Invalid dependency id '{dep}'.")
                    continue
                if dep_idx >= idx:
                    errors.append(
                        f"Node n{idx} depends on n{dep_idx} which is not an earlier node (cycle)."
                    )
        return errors
