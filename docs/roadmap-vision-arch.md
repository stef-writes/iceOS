Below is a single, self-contained document you can drop into `docs/` as
`architecture_three_tier_overview.md` (or any name you prefer).

────────────────────────────────────────
iceOS Architecture & End-to-End Authoring Flow
────────────────────────────────────────

1  Three-Tier Execution Model
────────────────────────────

Tier | Purpose | iceOS Packages & Key Objects
---- | ------- | ---------------------------
**Design-time**  (“Sketch / Canvas”) | Human-readable plan; nodes may be incomplete or placeholders | `ice_builder` (Draft DSL, WorkflowBuilder) → emits `Blueprint` *(Pydantic)* models
**Compile-time** (“Studio / Build”) | Full structural & behavioural validation; generates immutable import paths | `ice_api.api.mcp` validation routes<br>  • `ComponentDefinition`  *(tool_factory_code, etc.)*<br>  • `validate_component()` & supporting validators in `ice_core.validation`<br>  Registers factories via `ice_core.unified_registry`
**Run-time**  (“Execute / Orchestrator”) | Deterministic execution of validated nodes | `ice_orchestrator` DAG engine + node executors; factories invoked through `registry.get_*_instance`

Guarantees
•  Schema correctness (Design) → enforced by Pydantic models.
•  Behavioural correctness (Compile) → factory executed once, sample object validated, signature- vs-arg match checked.
•  Safe execution (Run) → fresh instance from factory, quick `isinstance` assert, sandbox/time-out limits.

2  iceStudio & iceCanvas Roles
──────────────────────────────

Component | Role | Mapping to 3-tier model
--------- | ---- | ----------------------
**iceCanvas** (whiteboard UI) | Brain-storming & layout. Users drag “sticky-note” placeholders or drop pre-built components. <br>Outputs draft `Blueprint`. | Operates entirely in **Design-time** tier.
**iceStudio** (component workbench) | Focused environment to turn a placeholder into a real Tool, Agent, or Workflow. <br>Provides templates, NL chat-based code generation, and live unit-style previews. | Primary interface to the **Compile-time** tier. On “Validate”, Studio calls MCP `/components/validate`.
**MCP** (Model-Compile Pipeline) | Headless compile service; executes factory once, validates, and records import paths in the registry. | Implements the **Compile-time** tier API.
**Orchestrator** | Executes a blueprint; pulls fresh instances via factory paths stored in the registry. | Implements the **Run-time** tier.

3  End-to-End User Story
────────────────────────

1. **Idea & White-boarding**
   • Emma opens **iceCanvas** and describes to ChatGPT-powered assistant:
     *“I want a workflow that parses a CSV of ads, enriches each row with an LLM, then posts to Facebook Marketplace.”*
   • The assistant sketches three sticky notes: `csv_loader`, “enrich row (sketch)”, `marketplace_poster`.
   • Canvas persists this draft as a `Blueprint` with two **real** tools (`csv_loader`, `marketplace_poster`) and one **placeholder** node.

2. **Opening the Placeholder in Studio**
   • Emma clicks the “enrich row” placeholder → **iceStudio** launches a Tool wizard.
   • Through NL chat she tells the Studio assistant: *“Create a tool that calls OpenAI with prompt X; needs params sentiment, category.”*
   • Studio scaffolds a factory function:

   ```python
   from ice_builder.utils.tool_factory import tool_factory
from ice_tools.toolkits.common.csv_loader import CSVLoaderTool

@tool_factory("csv_loader")
def create_csv_loader(path: str = "/tmp/data.csv", *, delimiter: str = ",") -> CSVLoaderTool:
    """Factory that returns a **typed** CSVLoaderTool instance."""
    return CSVLoaderTool(path=path, delimiter=delimiter)
   ```

   • Emma runs quick inline tests; everything passes.

3. **Compile / Validation (MCP)**
   • She clicks **Validate**.  Studio posts a `ComponentDefinition` with `tool_factory_code`.
   • MCP executes the factory once, creates a `RowEnricher` instance, validates `_execute_impl` signature against declared `tool_args`, and registers:

   ```
   from ice_core.unified_registry import register_tool_factory

register_tool_factory(
    "csv_loader",
    "ice_tools.toolkits.common.factory:create_csv_loader",
)
   ```

4. **Back to Canvas**
   • Canvas now manually or auto-replaces the placeholder with a real node:

     ```yaml
     - id: enrich
       type: tool
       tool_name: row_enricher
       tool_args:
         model: gpt-4o
     ```

   • Dependencies auto-wire.  The entire draft is now executable.

5. **End-to-End Run**
   • Emma presses **Run**.
   • Orchestrator executes:
     1. `csv_loader` → returns rows
     2. `row_enricher` → `registry.get_tool_instance("row_enricher", model="gpt-4o")` → fresh object, call `_execute_impl`
     3. `marketplace_poster` → posts

6. **Confidence loop**
   • Any structural error would have surfaced in Studio validation.
   • Any type mismatch in `tool_args` would raise during compile.
   • At runtime, only genuine network/API issues remain.

4  Impact on Developers & Tests
──────────────────────────────

•  **Developers** author only factories; they never worry about singletons.
•  **Tests** live in the Compile tier:
   – Unit: each factory’s `validate()` method.
   – Integration: executor resolves factory path & passes `tool_args`.
•  **CI** runs mypy-strict first (fast) → runs tests (slower) → publishes artefacts.

5  Traceability Cheat-Sheet
──────────────────────────

Step | Code call-path
---- | --------------
Register factory | `@tool_factory` → `register_tool_factory`
Validate factory | MCP `validate_component()`
Runtime create | `tool_executor` → `registry.get_tool_instance`
Error surfaces | • Compile error in Studio <br>• Quick `TypeError` in executor if factory hijacked

────────────────────────────────────────
This document can serve as the canonical explanation of how factories, MCP validation, and Canvas/Studio interactions guarantee “no-surprise” runtime execution.
