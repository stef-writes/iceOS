# pragma: no cover
from __future__ import annotations

# ruff: noqa: E402

"""Python-first DSL helpers to create NodeConfig objects via decorators.

This helper module is declarative only – unit tests cover behaviour via
integration, so exclude from coverage.

Example
-------

```python
from ice_sdk.dsl import ai, tool

@tool(id="fetch", name="Fetch Article", tool_name="HttpRequestTool")
async def fetch_article():
    ...

@ai(id="summariser_ai", prompt="Summarise: {{ article_text }}", model="gpt-4o", max_tokens=256)
async def summariser(ctx):
    return ctx.output
```

Each decorator returns a fully-populated :class:`~ice_sdk.models.node_models.*` instance.  The
wrapped function is not executed; it exists purely so users get IDE help
and type checking.
"""  # pragma: no cover

from typing import Any, Callable, Dict, List, Optional

from ice_core.models.model_registry import get_default_model_id
from ice_sdk.models.node_models import LLMOperatorConfig, SkillNodeConfig

# ---------------------------------------------------------------------------
# Helper ---------------------------------------------------------------
# ---------------------------------------------------------------------------


def _coerce_llm_kwargs(
    model: str | None = None, **kwargs: Any
) -> Dict[str, Any]:  # noqa: D401
    """Build llm_config dict from helper kwargs."""

    llm_conf: Dict[str, Any] = (
        kwargs.pop("llm_config", {}) if "llm_config" in kwargs else {}
    )
    if model:
        llm_conf.setdefault("model", model)
    # promote common kwargs
    for key in ("provider", "temperature", "top_p", "max_tokens"):
        if key in kwargs:
            llm_conf[key] = kwargs.pop(key)
    return llm_conf


# ---------------------------------------------------------------------------
# Public decorators ----------------------------------------------------
# ---------------------------------------------------------------------------


def ai(
    *,
    id: str,
    prompt: str,
    model: str | None = None,
    dependencies: Optional[List[str]] = None,
    name: str | None = None,
    **llm_kwargs: Any,
) -> Callable[[Callable[..., Any]], LLMOperatorConfig]:  # noqa: D401
    """Decorator that converts a Python function into an *LLMOperatorConfig*.

    Parameters correspond 1-to-1 with the YAML schema.  Additional keyword
    arguments map into *llm_config* automatically (temperature, top_p, …).
    """

    def _wrapper(
        func: Callable[..., Any]
    ) -> LLMOperatorConfig:  # noqa: D401 – inner factory
        llm_conf = _coerce_llm_kwargs(model, **llm_kwargs)

        cfg = LLMOperatorConfig(
            id=id,
            type="llm",
            name=name or func.__name__,
            prompt=prompt,
            model=model or llm_conf.get("model", get_default_model_id()),
            llm_config=llm_conf,  # type: ignore[arg-type]
            dependencies=dependencies or [],
        )
        # Store reference so tooling can introspect --------------------
        setattr(cfg, "_python_callable", func)
        return cfg

    return _wrapper


def tool(
    *,
    id: str,
    tool_name: str,
    name: str | None = None,
    tool_args: Optional[Dict[str, Any]] = None,
    dependencies: Optional[List[str]] = None,
) -> Callable[[Callable[..., Any]], SkillNodeConfig]:  # noqa: D401
    """Decorator that returns a *SkillNodeConfig* bound to an existing Skill class."""

    def _wrapper(func: Callable[..., Any]) -> SkillNodeConfig:
        cfg = SkillNodeConfig(
            id=id,
            type="skill",
            name=name or func.__name__,
            tool_name=tool_name,
            tool_args=tool_args or {},
            dependencies=dependencies or [],
        )
        setattr(cfg, "_python_callable", func)
        return cfg

    return _wrapper
