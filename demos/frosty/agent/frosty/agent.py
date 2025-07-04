"""Frosty Design Assistant

A dedicated agent for interactively guiding users through the design of new
iceOS flows. This version is housed under the `frosty` contrib namespace so we
can grow its feature-set independently of the neutral Flow-Design logic.

Mermaid diagram (for docs only):

```mermaid
graph TD
    A[User Query] --> B(Frosty Design Assistant)
    B --> C{Requirement Analysis}
    C -->|Needs API| D[APISuggestTool]
    C -->|Needs Data| E[DataSourceWizard]
    C -->|New Tool| F[ToolScaffoldGenerator]
    B --> G[Chain Builder]
    G --> H[YAML Config Generator]
    G --> I[Python Chain Stub]
    B --> J[Validation Subsystem]
    J --> K[Schema Checker]
    J --> L[Cost Estimator]
```"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ice_sdk.agents.agent_node import AgentNode


class FrostyAssistantConfig(BaseModel):
    """Configuration options for FrostyDesignAssistant."""

    persona: str = Field(
        default="frosty",
        description="Persona style; defaults to Frosty's playful tone.",
    )


class FrostyDesignAssistant(AgentNode):
    """An assistant that helps users architect iceOS flows with a frosty flair."""

    config: FrostyAssistantConfig

    async def _run(self, user_message: str) -> str:  # type: ignore[override]
        """Stubbed run-loop—will be expanded as features are added."""

        return (
            "❄️ Hey there! I'm Frosty, your flow-design sidekick. "
            "Tell me what you'd like to build and we'll chill-ify it together!"
        )
