"""Executor for *llm* (LLM node). Canonical implementation."""

from datetime import datetime
from typing import Any, Dict

import ice_core.llm.service as _llm_service_mod
from ice_core.models import LLMNodeConfig, NodeExecutionResult
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry

__all__ = ["llm_node_executor"]


@register_node("llm")
async def llm_node_executor(
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: LLMNodeConfig,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:  # noqa: D401, ANN401
    start_time = datetime.utcnow()

    try:
        try:
            prompt_template = cfg.prompt or ""
            prompt = prompt_template.format(**ctx)
        except KeyError as exc:
            raise ValueError(f"Missing template variable in prompt: {exc}") from exc

        provider: ModelProvider | str = (
            cfg.llm_config.provider
            if cfg.llm_config and cfg.llm_config.provider
            else ModelProvider.OPENAI
        )
        if isinstance(provider, str):
            try:
                provider = ModelProvider(provider)
            except ValueError:
                provider = ModelProvider.OPENAI

        llm_cfg = LLMConfig(
            provider=provider,
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
        )

        # Prefer factory-based LLM instance when registered; fall back to LLMService
        text: str
        usage: dict[str, int] | None
        error: str | None

        # If a custom LLM factory is registered under cfg.model (or cfg.llm_name), use it
        chosen_llm_name = getattr(cfg, "llm_name", None) or cfg.model
        try:
            llm_helper = registry.get_llm_instance(chosen_llm_name)
            text, usage, error = await llm_helper.generate(
                llm_config=llm_cfg,
                prompt=prompt,
                context=ctx,
            )
        except KeyError:
            llm_service = _llm_service_mod.LLMService()
            text, usage, error = await llm_service.generate(
                llm_config=llm_cfg,
                prompt=prompt,
                context=ctx,
            )
        end_time = datetime.utcnow()

        if error:
            return NodeExecutionResult(
                success=False,
                error=error,
                output={},
                metadata=NodeMetadata(
                    node_id=cfg.id,
                    node_type=cfg.type,
                    name=f"llm_{cfg.model}",
                    version="1.0.0",
                    owner="system",
                    error_type="LLMError",
                    provider=cfg.provider,
                    start_time=start_time,
                    end_time=end_time,
                    duration=(end_time - start_time).total_seconds(),
                    description=f"LLM execution failed: {cfg.model}",
                ),
            )

        return NodeExecutionResult(
            success=True,
            output={
                "response": text,
                "prompt": prompt,
                "model": cfg.model,
                "usage": usage or {},
            },
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=f"llm_{cfg.model}",
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"LLM execution: {cfg.model}",
            ),
        )

    except Exception as exc:  # pragma: no cover
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=str(exc),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=f"llm_{getattr(cfg, 'model', 'unknown')}",
                version="1.0.0",
                owner="system",
                error_type=type(exc).__name__,
                provider=cfg.provider,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"LLM execution failed: {getattr(cfg, 'model', 'unknown')}",
            ),
        )
