"""Utility to execute an iceOS Workflow fully *in-process*.

The tester patches the network-heavy LLM layer so that blueprints can be
executed deterministically inside unit-tests without API keys or network
access.

Typical usage
-------------
>>> from ice_orchestrator.testing.workflow_tester import WorkflowTester
>>> tester = WorkflowTester()
>>> result = await tester.run(workflow_dict)
>>> assert result.success
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import MethodType
from typing import Any, Dict, Optional

import yaml  # PyYAML is already a transitive dependency

from ice_orchestrator.workflow import iceEngine, Workflow
from ice_core.models import ChainExecutionResult  # public return type
from ice_sdk.providers.llm_service import LLMService

class WorkflowTester:  # pylint: disable=too-few-public-methods
    """Execute a Workflow with stubbed LLM responses.

    Parameters
    ----------
    default_text : str, default "stubbed response"
        Text returned for every LLM node.
    default_usage : dict | None, optional
        Usage dictionary attached to the stubbed response.  Defaults to an
        empty token/cost payload so downstream cost tracking passes.
    """

    def __init__(
        self,
        *,
        default_text: str = "stubbed response",
        default_usage: Optional[Dict[str, int]] = None,
    ) -> None:
        self._default_text = default_text
        self._default_usage = default_usage or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        self._orig_generate = None  # will be populated on patch

    # ------------------------------------------------------------------ public API
    async def run(self, workflow: dict[str, Any] | iceEngine) -> ChainExecutionResult:  # type: ignore[type-var]
        """Execute *workflow* and return a :class:`ChainExecutionResult`.

        The *workflow* argument can be:
        • A dict adhering to the chain JSON schema.
        • A pre-instantiated :class:`ice_orchestrator.workflow.Workflow`.
        """

        self._patch_llm()
        try:
            wf: iceEngine
            if isinstance(workflow, Workflow):
                wf = workflow
            else:
                wf = await Workflow.from_dict(workflow)  # type: ignore[arg-type]

            result = await wf.execute()
            return result  # type: ignore[return-value]
        finally:
            self._restore_llm()

    async def run_and_write_fixture(
        self,
        workflow: dict[str, Any] | Workflow,
        *,
        output_path: str | Path,
        overwrite: bool = False,
    ) -> ChainExecutionResult:  # noqa: D401 – convenience wrapper
        """Execute *workflow* and serialize the result to YAML *output_path*."""

        result = await self.run(workflow)

        path = Path(output_path)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Fixture already exists: {path}")

        # PyYAML dumps complex dataclasses poorly – convert via dict first.
        data_dict = result.model_dump(mode="json") if hasattr(result, "model_dump") else result  # type: ignore[attr-defined]
        yaml.safe_dump(data_dict, path.open("w"), sort_keys=False)
        return result

    # ------------------------------------------------------------------ internals
    def _patch_llm(self) -> None:
        """Monkey-patch :pymeth:`LLMService.generate` with a stub coroutine."""

        if self._orig_generate is not None:  # already patched – nested use
            return

        self._orig_generate = LLMService.generate

        async def _stub_generate(  # type: ignore[return-type]
            _self: LLMService, *args: Any, **kwargs: Any
        ) -> tuple[str, dict[str, int] | None, None]:
            # Mimic signature: returns (text, usage, error)
            return self._default_text, dict(self._default_usage), None  # type: ignore[arg-type]

        # Bind as *instance* method so *self* is passed correctly
        LLMService.generate = MethodType(_stub_generate, LLMService)  # type: ignore[assignment]

    def _restore_llm(self) -> None:
        """Restore the original *generate* implementation."""

        if self._orig_generate is not None:
            LLMService.generate = self._orig_generate  # type: ignore[assignment]
            self._orig_generate = None

__all__ = ["WorkflowTester"] 