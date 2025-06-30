"""Minimal engine for interactive *Chain Builder* M0.

The engine is UI-agnostic: it exposes :func:`ask_next` which returns a
question dict and :func:`submit_answer` which records the response.
A CLI wrapper (in ``ice_cli.cli``) feeds user answers via *questionary*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Note: Imports below are only needed for type hints in the generated template
# string – they are not used at runtime within this module.  Suppress the
# unused-import warnings accordingly.  # noqa: F401
from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig  # noqa: F401

# ---------------------------------------------------------------------------
# Standard library imports ---------------------------------------------------
# ---------------------------------------------------------------------------



__all__ = ["ChainDraft", "BuilderEngine", "Question"]


@dataclass
class Question:  # noqa: D401 – simple container
    key: str
    prompt: str
    choices: Optional[List[str]] = None  # None → free text


@dataclass
class ChainDraft:  # noqa: D401 – mutable builder state
    name: str = "my_chain"
    nodes: List[dict] = field(default_factory=list)  # hold raw answers per node
    current_step: int = 0
    total_nodes: int = 0

    # Helpers -----------------------------------------------------------
    def save(self) -> None:  # noqa: D401 – persist to disk
        """Serialize *self* to .ice/builder.draft.json under CWD (best-effort)."""

        import json
        from dataclasses import asdict
        from pathlib import Path

        ice_dir = Path.cwd() / ".ice"
        ice_dir.mkdir(exist_ok=True)
        (ice_dir / "builder.draft.json").write_text(json.dumps(asdict(self), indent=2))
        # Intentionally swallow exceptions – persistence is best-effort


class BuilderEngine:  # noqa: D401 – stateless helper
    """Simple state machine for M0 (linear ai/tool nodes)."""

    @staticmethod
    def start(total_nodes: int, chain_name: str | None = None) -> ChainDraft:
        cd = ChainDraft(name=chain_name or "my_chain", total_nodes=total_nodes)
        return cd

    # ------------------------------------------------------------------
    # Question flow -----------------------------------------------------
    # ------------------------------------------------------------------
    @staticmethod
    def next_question(draft: ChainDraft) -> Optional[Question]:  # noqa: D401
        # Determine current node index ---------------------------------
        node_idx = len(draft.nodes) - (1 if draft.current_step < 1 else 0)

        if draft.current_step == 0:
            return Question(key="type", prompt="Node type", choices=["ai", "tool"])
        elif draft.current_step == 1:
            return Question(key="name", prompt="Node name")
        elif draft.current_step == 2:
            if draft.nodes and draft.nodes[-1]["type"] == "ai":
                return Question(key="model", prompt="Model (ai only)")
            else:
                # Skip model step for tool nodes -----------------------
                draft.current_step += 1
                return BuilderEngine.next_question(draft)
        elif draft.current_step == 3 and node_idx > 0:
            # Ask dependencies unless this is the first node ----------
            available_ids = [f"n{i}" for i in range(node_idx)]
            return Question(
                key="deps",
                prompt=f"Depends on (comma-separated IDs, blank=auto-prev) [available: {', '.join(available_ids)}]",
            )
        else:
            return None

    @staticmethod
    def submit_answer(draft: ChainDraft, key: str, answer: str) -> None:  # noqa: D401
        # Map step index -> expected key (dynamic based on node type) ---
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
        elif draft.current_step in (2, 3) and key == "deps":
            deps = [d.strip() for d in answer.split(",") if d.strip()]
            if not deps and len(draft.nodes) > 1:
                # Default dependency → previous node id --------------
                deps = [f"n{len(draft.nodes)-2}"]
            draft.nodes[-1]["dependencies"] = deps
            # Node finished – reset pointer for next node -------------
            draft.current_step = 0

        # Persist after every answer ----------------------------------
        draft.save()

    # ------------------------------------------------------------------
    # Render -------------------------------------------------------------
    # ------------------------------------------------------------------
    @staticmethod
    def render_chain(draft: ChainDraft) -> str:  # noqa: D401
        """Return Python source code for the ScriptChain."""
        import textwrap

        node_lines: List[str] = []
        for idx, node in enumerate(draft.nodes):
            node_id = f"n{idx}"
            if node["type"] == "ai":
                deps_str = node.get('dependencies', [])
                node_lines.append(
                    f"    AiNodeConfig(id=\"{node_id}\", type=\"ai\", name=\"{node['name']}\", model=\"{node.get('model','gpt-3.5-turbo')}\", prompt=\"# TODO\", llm_config={{'provider': 'openai'}}, dependencies={deps_str}),"
                )
            else:
                deps_str = node.get('dependencies', [])
                node_lines.append(
                    f"    ToolNodeConfig(id=\"{node_id}\", type=\"tool\", name=\"{node['name']}\", tool_name=\"echo\", tool_args={{}}, dependencies={deps_str}),"
                )

        nodes_block = "\n".join(node_lines)
        template = f'"""{draft.name} – generated by Chain Builder"""\n\nfrom __future__ import annotations\n\nfrom typing import List\n\nfrom ice_orchestrator.script_chain import ScriptChain\nfrom ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig\nfrom ice_sdk.tools.builtins.deterministic import SumTool\n\nnodes: List[AiNodeConfig | ToolNodeConfig] = [\n{nodes_block}\n]\n\nif __name__ == "__main__":\n    chain = ScriptChain(nodes=nodes, tools=[SumTool()], name="{draft.name}")\n    import asyncio, rich; rich.print(asyncio.run(chain.execute()).model_dump())\n'
        return textwrap.dedent(template)

    @staticmethod
    def render_mermaid(draft: ChainDraft) -> str:  # noqa: D401
        """Return Mermaid \`graph LR\` diagram representing the draft.

        Notes
        -----
        * M0 supports only **linear** chains, therefore each node depends on the
          previous one.  The diagram is rendered left-to-right (LR).
        * Node IDs follow the same temporary convention used by
          :py:meth:`render_chain` – ``n0``, ``n1`` … – so both previews align.
        """
        lines: list[str] = ["graph LR"]

        for idx, node in enumerate(draft.nodes):
            node_id = f"n{idx}"
            label = f"{node['type'].upper()}: {node.get('name', '')}".strip()
            lines.append(f"    {node_id}[{label}]")
            deps = node.get('dependencies')
            if deps:
                for dep in deps:
                    lines.append(f"    {dep} --> {node_id}")
            elif idx > 0:
                prev_id = f"n{idx - 1}"
                lines.append(f"    {prev_id} --> {node_id}")

        return "\n".join(lines) 