from __future__ import annotations

from abc import ABC
from typing import Any, Callable, Dict, Optional, Protocol, Type

from pydantic import BaseModel

from ice_sdk.providers.costs import CostTracker
from ice_sdk.utils.circuit_breaker import CircuitBreaker
from ice_sdk.utils.errors import SkillExecutionError
from ice_sdk.utils.hashing import stable_hash

# ---------------------------------------------------------------------------
# Public protocol representing the minimal *skill* surface required by
# orchestrator/executor layers.  Defining it here avoids repeated ``# type:
# ignore[attr-defined]`` errors throughout the codebase.
# ---------------------------------------------------------------------------


class SupportsSkill(Protocol):  # noqa: D401 – structural typing
    name: str
    description: str


# ---------------------------------------------------------------------------
# Fallback *InputModel* allows concrete Skills to omit a custom schema until
# they mature.  Tests relying on direct instantiation therefore succeed even
# when the author hasn’t provided one.
# ---------------------------------------------------------------------------


class _EmptyInputModel(BaseModel):
    """Placeholder model used when a Skill does not declare an InputModel."""

    class Config:  # noqa: D401 – pydantic v1 stub
        arbitrary_types_allowed = True


class SkillBase(ABC):
    # Public identifying attributes populated by subclasses ------------------
    name: str = ""
    description: str = ""

    # Default JSON schema stub used by LLM function-calling
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self) -> None:
        # CircuitBreaker is a **no-op** stub for now, but keeping the interface
        # in place allows later drop-in of a real implementation without
        # touching call-sites.
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

    # ------------------------------------------------------------------
    # Structured representation for LLM function-calling ----------------
    # ------------------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:  # noqa: D401 – helper name
        """Return an OpenAI-style function description.

        Many LLM providers expect a list of *function* objects each having a
        ``name``, ``description`` and JSONSchema ``parameters``.  Providing a
        minimal stub here unblocks agent-centric tests without forcing every
        skill author to implement the boilerplate.
        """

        return {
            "name": getattr(self, "name", self.__class__.__name__.lower()),
            "description": getattr(self, "description", ""),
            "parameters": getattr(self, "parameters_schema", self.parameters_schema),
        }

    # ------------------------------------------------------------------
    # Default *run* shim (legacy compatibility) -------------------------
    # ------------------------------------------------------------------

    async def run(
        self, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:  # noqa: D401 – unified entrypoint
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

        return await self.execute(kwargs)

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

        # Build key lazily so hashing doesn’t cost when unused.
        idempotency_key = idempotency_key or stable_hash(
            (self.__class__.__name__, merged_kwargs)
        )

        # Run with cost-tracking and circuit-breaking wrappers.
        CostTracker.start_span(self.__class__.__name__)
        try:
            async with self._circuit_breaker:  # type: ignore[attr-defined]
                result = await self._execute_impl(**merged_kwargs)
            CostTracker.end_span(success=True)
            return result
        except Exception as exc:  # noqa: BLE001 – propagate specific errors
            CostTracker.end_span(success=False, error=str(exc))
            raise

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # noqa: D401
        """Default passthrough implementation.

        Concrete subclasses should override this.  For simple *function_tool*
        shims used in tests, we delegate to :meth:`run` so the class is no
        longer abstract and can be instantiated without redefining the
        method.
        """

        return await self.run(**kwargs)


# Legacy compatibility -------------------------------------------------------
# Some test files still import ToolContext / function_tool from the deleted
# ice_sdk.tools.base module.  Provide minimal shims here so the import heals.

# ---------------------------------------------------------------------------
# Legacy compatibility: ToolContext & @function_tool decorator
# ---------------------------------------------------------------------------

# Provide a minimal *ToolContext* stub for tests that still expect it.


class ToolContext(dict):  # type: ignore[D101]
    """Context object passed into legacy *function_tool* wrappers."""


def _build_function_tool(
    func,
    *,
    name: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
):
    """Return a lightweight SkillBase instance that wraps *func*.

    The orchestrator only requires the wrapper to expose the following API:

    1.  ``name`` attribute → for lookup/registration.
    2.  ``run`` coroutine/function → actual execution path consumed by
        :pymeth:`ice_sdk.context.manager.GraphContextManager.execute_tool`.

    Any other SkillBase helpers (``execute`` with retries, etc.) are not
    strictly needed for these test utilities, therefore we keep the wrapper
    minimal and steer clear of additional runtime overhead.
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

        async def run(self, *args, **kwargs):  # type: ignore[override]
            import asyncio  # local import to keep global footprint low
            import inspect

            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            # Execute sync function in thread-friendly executor to avoid
            # blocking the event loop when called from async orchestrator.
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        # Provide minimal _execute_impl so mypy recognises concrete subclass
        async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
            return await self.run(**kwargs)

    # Expose original callable for introspection and doctest friendliness
    _FunctionTool.__wrapped__ = func  # type: ignore[attr-defined]

    return _FunctionTool()


# ---------------------------------------------------------------------------
# Public decorator – legacy signature compatible
# ---------------------------------------------------------------------------


def function_tool(*_decorator_args, **_decorator_kwargs):  # type: ignore[D401]
    """Decorator that converts a plain async/sync function into a *Skill*.

    Legacy tests use two equivalent forms::

        @function_tool
        async def my_tool(ctx: ToolContext, ...):
            ...

        @function_tool(name_override="foo")
        async def my_tool(ctx: ToolContext, ...):
            ...
    """

    # Case 1: Bare decorator usage → first arg is the target function.
    if _decorator_args and callable(_decorator_args[0]) and not _decorator_kwargs:
        return _build_function_tool(_decorator_args[0])

    # Case 2: Decorator with keyword args (e.g. name_override="x") → return
    #         a decorator expecting the target function.
    def _decorator(func: Callable[..., Any]) -> Any:  # noqa: D401 – simple wrapper
        name = _decorator_kwargs.get("name_override") or _decorator_kwargs.get("name")
        description = _decorator_kwargs.get("description")
        tags = _decorator_kwargs.get("tags")
        return _build_function_tool(func, name=name, description=description, tags=tags)

    return _decorator


# ---------------------------------------------------------------------------
# Backwards-compatibility aliases (Phase 0 migration strategy)
# ---------------------------------------------------------------------------

# Older code imported *BaseTool* and *ToolError* from the now-removed
# ``ice_sdk.tools.base`` module.  Provide thin aliases here so that those
# imports resolve until the full vocabulary transition completes (v0.6.0).

SkillBase = SkillBase  # noqa: D401 – temporary alias
SkillExecutionError = SkillExecutionError  # noqa: D401 – temporary alias
BaseTool = SkillBase  # noqa: D401 – compatibility alias
