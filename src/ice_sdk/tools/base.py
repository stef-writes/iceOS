"""Base classes for iceOS skills and tools.

This module provides the foundational classes that all skills and tools inherit from.
It includes the base Skill class, metadata structures, and common utilities.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type

from pydantic import BaseModel, ConfigDict

from ice_sdk.providers.costs import CostTracker
from ice_sdk.utils.hashing import stable_hash

# ---------------------------------------------------------------------------
# Metadata structures --------------------------------------------------------
# ---------------------------------------------------------------------------

JsonSchemaValue = Dict[str, Any]


class SkillMeta:
    """Metadata for a skill instance."""

    def __init__(
        self,
        *,
        node_subtype: Optional[str] = None,
        commercializable: bool = False,
        license: str = "Proprietary",
        author: str | None = None,
        cost_weight: float = 1.0,
    ):
        self.node_subtype = node_subtype
        self.commercializable = commercializable
        self.license = license
        self.author = author or "Unknown"
        self.cost_weight = cost_weight


class _EmptyInputModel(BaseModel):
    """Empty input model for skills that don't require inputs."""

    model_config = ConfigDict(extra="forbid")


class SkillBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def json_schema(cls) -> dict[str, JsonSchemaValue]:
        return cls.model_json_schema()  # Class method access

    # Public identifying attributes populated by subclasses ------------------
    name: str = ""
    description: str = ""

    # Default JSON schema stub used by LLM function-calling
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, **data: Any) -> None:
        """
        Instantiate the skill and ensure Pydantic field initialisation.
        """
        super().__init__(**data)

    # ------------------------------------------------------------------
    # Structured representation for LLM function-calling ----------------
    # ------------------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:  # – helper name
        """Return an OpenAI-style function description.

        Many LLM providers expect a list of *function* objects each having a
        ``name``, ``description`` and JSONSchema ``parameters``.  Providing a
        minimal stub here unblocks agent-centric tests without forcing every
        skill author to implement the boilerplate.
        """

        return {
            "name": getattr(self, "name", ""),
            "description": getattr(self, "description", ""),
            "parameters": getattr(self, "parameters_schema", self.parameters_schema),
        }

    # ------------------------------------------------------------------
    # Metadata helper – surfaces nested ``Meta`` class as :class:`SkillMeta`
    # ------------------------------------------------------------------

    @property
    def meta(self) -> "SkillMeta":  # type: ignore[name-defined]
        """Return normalised :class:`SkillMeta` for this Skill instance."""

        meta_cls = getattr(self.__class__, "Meta", None)
        if meta_cls is None:
            return SkillMeta()

        return SkillMeta(
            node_subtype=getattr(meta_cls, "node_subtype", None),
            commercializable=getattr(meta_cls, "commercializable", False),
            license=getattr(meta_cls, "license", "Proprietary"),
            author=getattr(meta_cls, "author", None),
            cost_weight=getattr(meta_cls, "cost_weight", 1.0),
        )

    # ------------------------------------------------------------------
    # Default *run* shim (legacy compatibility) -------------------------
    # ------------------------------------------------------------------

    async def run(
        self, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:  # – unified entrypoint
        """Execute the skill as a *tool*.

        The orchestrator calls ``tool.run(ctx=ToolContext(), **tool_args)``.
        For skills implemented via :class:`SkillBase` the logic already lives
        inside :meth:`execute`, therefore we strip the positional/keyword
        *ctx* argument and forward the rest to :meth:`execute`.
        """

        # Drop *ctx* placeholder when present – context isn't required by most
        # skills and would otherwise break signature matching.
        kwargs.pop("ctx", None)

        # Positional args are not expected for Skill-based tools; raise early
        # to avoid silent misalignment.
        if args:
            raise TypeError(
                "Skill.run accepts only keyword arguments; positional values found"
            )

        # Forward gathered *kwargs* as *input_data* preserving legacy calling
        # contract.  Use an explicitly typed local v
        # generic-aware *dict[str, Any]* instance.
        kwdict: Dict[str, Any] = dict(kwargs)
        return await self.execute(input_data=kwdict)

    # Concrete Skills may override this with their own pydantic schema.
    # Keeping it a *class* attribute (not property) simplifies subclassing.
    InputModel: Type[BaseModel] = _EmptyInputModel

    async def execute(
        self,
        input_data: Optional[Dict[str, Any]] | None = None,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Public entry-point used by orchestrator and tests.

        Parameters
        ----------
        input_data: dict | None, optional
            Legacy payload mapping.  When provided, it is merged into
            ``kwargs`` so that both calling styles work:

            ``await skill.execute({"numbers": [1, 2]})`` **and**
            ``await skill.execute(numbers=[1, 2])``
        idempotency_key: str | None, optional
            Hint for external caching layers.  When *None* we hash the
            invocation arguments.
        **kwargs: Any
            Direct keyword parameters forwarded to the concrete skill.
        """

        # Merge *input_data* into kwargs for backward compatibility.
        merged_kwargs: Dict[str, Any] = {**(input_data or {}), **kwargs}

        # Build key lazily so hashing doesn't cost when unused.
        idempotency_key = idempotency_key or stable_hash(
            (self.__class__.__name__, merged_kwargs)
        )

        # Run with cost-tracking and circuit-breaking wrappers.
        CostTracker.start_span(self.__class__.__name__)
        try:
            result: Dict[str, Any] = await self._execute_impl(**merged_kwargs)  # type: ignore[assignment]
            CostTracker.end_span(success=True)
            return result
        except Exception as exc:  # – propagate specific errors
            CostTracker.end_span(success=False, error=str(exc))
            raise

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Default passthrough implementation.

        Concrete subclasses should override this.  For simple *function_tool*
        shims used in tests, we delegate to :meth:`run` so the class is no
        longer abstract and can be instantiated without redefining the
        method.
        """

        return await self.run(**kwargs)

    @classmethod
    def get_input_schema(cls) -> dict:
        """Get JSON schema for skill inputs.

        Example:
            WebSearchSkill.get_input_schema() => {'type': 'object', ...}
        """
        return cls.InputModel.model_json_schema()  # Fixed method call

    @classmethod
    def get_output_schema(cls) -> dict:
        """Get JSON schema for skill outputs.

        Example:
            WebSearchSkill.get_output_schema() => {'type': 'object', ...}
        """
        return cls.OutputModel.model_json_schema()  # Fixed method call


# Legacy compatibility -------------------------------------------------------
# Some test files still import ToolContext / function_tool from the deleted
# ice_sdk.tools.base module.  Provide minimal shims here so the import heals.

# ---------------------------------------------------------------------------
# Legacy compatibility: ToolContext & @function_tool decorator
# ---------------------------------------------------------------------------


# Provide a minimal *ToolContext* stub for tests that still expect it.
class ToolContext:
    """Lightweight context passed to stateful tools.

    The orchestrator builds a payload with keys ``agent_id``, ``session_id`` and
    ``metadata``.  Older skills never inspected the attributes, so we accept
    arbitrary keyword arguments to remain forward-compatible.
    """

    agent_id: str | None
    session_id: str | None
    metadata: Dict[str, Any]

    # Accept **kwargs so callers can evolve payload without breaking tools.
    def __init__(
        self,
        agent_id: str | None = None,
        session_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
        **_: Any,
    ) -> None:  # noqa: D401 – simple container
        self.agent_id = agent_id
        self.session_id = session_id
        self.metadata = metadata or {}


def _build_function_tool(
    func: Callable[..., Any],
    *,
    name: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Type[SkillBase]:
    """Build a *SkillBase* subclass that delegates to *func*.

    This helper creates a minimal class that satisfies the *SkillBase* interface
    while delegating actual execution to the provided callable.  It's used by
    the *@function_tool* decorator to create test-friendly tool implementations.
    """

    _name = name or func.__name__
    _description = description or (func.__doc__ or "")
    _tags = tags or []

    # Dynamically build a trivial class with ``run`` delegating to *func*.
    class _FunctionTool(SkillBase):  # pylint: disable=too-few-public-methods
        name: str = _name
        description: str = _description
        tags: tuple[str, ...] = tuple(_tags)  # type: ignore[assignment]

        # NB: We purposefully **do not** call ``SkillBase.execute`` here – the
        # GraphContextManager invokes ``run`` directly.  We support both sync
        # and async callables for convenience.

        async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override,no-untyped-def]
            import asyncio  # local import to keep global footprint low
            import inspect

            if inspect.iscoroutinefunction(func):
                res = await func(*args, **kwargs)
            else:
                # Execute sync function in thread-friendly executor to avoid
                # blocking the event loop when called from async orchestrator.
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(None, lambda: func(*args, **kwargs))

            from typing import cast

            return cast(Dict[str, Any], res or {})

        # Provide minimal _execute_impl so mypy recognises concrete subclass
        async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
            return await self.run(**kwargs)

    # Expose original callable as *func* attribute for debugging
    _FunctionTool.func = func  # type: ignore[attr-defined]

    return _FunctionTool


def function_tool(
    *,
    name_override: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Type[SkillBase]]:
    """Decorator that converts a function into a *SkillBase* subclass.

    This decorator is used primarily for testing and prototyping.  It creates
    a minimal *SkillBase* implementation that delegates execution to the
    decorated function.

    Examples
    --------
    >>> @function_tool(description="Adds two numbers")
    ... def add(a: int, b: int) -> int:
    ...     return a + b
    >>> tool = add()
    >>> await tool.execute(a=1, b=2)
    {'result': 3}
    """

    def decorator(func: Callable[..., Any]) -> Type[SkillBase]:
        return _build_function_tool(
            func, name=name_override, description=description, tags=tags
        )

    return decorator
