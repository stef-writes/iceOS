from tenacity import retry, stop_after_attempt, wait_exponential
from ice_sdk.utils.circuit_breaker import CircuitBreaker
from ice_sdk.utils.errors import SkillExecutionError
from typing import Any

class SkillBase:
    circuit_breaker = CircuitBreaker(failure_threshold=3)

    # Default JSON schema stub used by LLM function-calling
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

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

    async def run(self, *args, **kwargs):  # noqa: D401 – unified entrypoint
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
    
    def validate(self, config: dict) -> bool:
        """Pre-execution validation (Rule 13)"""
        required = self.get_required_config()
        return all(k in config for k in required)
    
    def get_required_config(self):  # noqa: D401
        """Return list of required config keys. Subclasses should override."""
        return []
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
    @circuit_breaker.protect
    async def execute(self, input_data: dict) -> dict:
        """Execute with retries and circuit breaking"""
        return await self._execute_impl(input_data)
    
    async def _execute_impl(self, input_data: dict) -> dict:
        raise NotImplementedError 

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
        tags: list[str] = _tags  # type: ignore[assignment]

        # NB: We purposefully **do not** call ``SkillBase.execute`` here – the
        # GraphContextManager invokes ``run`` directly.  We support both sync
        # and async callables for convenience.

        async def run(self, *args, **kwargs):  # type: ignore[override]
            import inspect, asyncio  # local import to keep global footprint low

            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            # Execute sync function in thread-friendly executor to avoid
            # blocking the event loop when called from async orchestrator.
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

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
    def _decorator(func):  # noqa: D401 – simple wrapper
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