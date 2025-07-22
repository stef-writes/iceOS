"""PromptTemplateRegistry – central registry for named LLM prompt templates.

Lives in *ice_core* so all layers (SDK, orchestrator, API) can import it
without creating cyclic dependencies.

Design goals
------------
* **Pure in-memory** – no external IO, satisfying core layer constraints.
* **Typed** – stores :class:`ice_core.models.llm.MessageTemplate` instances.
* **Idempotent validate()** – every template is validated on registration
  (Rule 13) so bad templates never reach runtime execution.
* **Async-safe** – registry operations are lightweight and thread-safe for
  typical asyncio workloads (no locking yet, fine for CPython GIL).
"""

from __future__ import annotations

from typing import Dict, Iterator, Callable, Any

from ice_core.models.llm import MessageTemplate

__all__: list[str] = [
    "PromptTemplateRegistry",
    "global_prompt_template_registry",
    "register_prompt_template",
]


class PromptTemplateRegistry:
    """Runtime registry mapping *name* → :class:`MessageTemplate`."""

    _templates: Dict[str, MessageTemplate]

    def __init__(self) -> None:  # noqa: D401 – simple init
        self._templates = {}

    # ------------------------------------------------------------------
    # Registration ------------------------------------------------------
    # ------------------------------------------------------------------
    def register(self, name: str, template: MessageTemplate) -> None:  # noqa: D401
        if name in self._templates:
            raise ValueError(f"Prompt template '{name}' already registered")

        # Rule 13 – idempotent validate
        template.is_compatible_with_model(template.min_model_version)
        self._templates[name] = template

    # ------------------------------------------------------------------
    # Resolution --------------------------------------------------------
    # ------------------------------------------------------------------
    def get(self, name: str) -> MessageTemplate:
        try:
            return self._templates[name]
        except KeyError as exc:
            raise KeyError(f"Prompt template '{name}' not found") from exc

    # Convenience iter/len ---------------------------------------------
    def __iter__(self) -> Iterator[tuple[str, MessageTemplate]]:
        yield from self._templates.items()

    def __len__(self) -> int:  # noqa: D401
        return len(self._templates)


# Global singleton ----------------------------------------------------------

global_prompt_template_registry: PromptTemplateRegistry = PromptTemplateRegistry()


# Decorator helper -----------------------------------------------------------

def register_prompt_template(name: str) -> Callable[[Callable[[], MessageTemplate] | MessageTemplate], Callable[..., Any]]:
    """Decorator to register a function that returns MessageTemplate."""

    def decorator(fn: Callable[[], MessageTemplate] | MessageTemplate) -> Callable[..., Any]:  # noqa: D401
        tmpl: MessageTemplate = fn() if callable(fn) else fn  # type: ignore[arg-type]
        if not isinstance(tmpl, MessageTemplate):
            raise TypeError("register_prompt_template expects a MessageTemplate instance")
        global_prompt_template_registry.register(name, tmpl)
        return fn  # type: ignore[return-value]

    return decorator


# PromptTemplateStore removed in v1.1 – use *global_prompt_template_registry* instead. 