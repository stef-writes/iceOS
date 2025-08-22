# Plugins Manifest Contract (plugins.v0)

This document defines the stable authoring contract for first‑party and third‑party Plugins. It covers the manifest format, supported component types, versioning, and loading semantics used by the unified registry.

## Goals
- Deterministic, versioned component discovery
- No runtime imports outside declared manifests
- Clear, minimal shape to register Tools, Workflows, Agents

## Location and loading
- Manifests live under `Plugins/kits/**/plugins.v0.yaml` and are loaded via the environment variable:
  - `ICEOS_PLUGIN_MANIFESTS=/app/plugins/kits/tools/memory/plugins.v0.yaml,/app/plugins/kits/tools/search/plugins.v0.yaml`
- The API and tests rely on this env var; no bootstrap scripts.

## Schema (v0)
```yaml
schema: plugins.v0
components:
  - node_type: tool        # one of: tool | workflow | agent
    name: memory_search_tool
    import_path: plugins.kits.tools.memory.memory_search_tool:create_memory_search_tool
    version: 1.0.0
    description: Semantic memory search
```
Optional fields:
- `signature`: reserved for future signing/verification

## Semantics
- `node_type` selects registry bucket (tool/workflow/agent)
- `import_path` is `module:callable_or_class`
  - Tools: callable returning `ToolBase` OR a subclass of `ToolBase`
  - Workflows: callable returning a Workflow‑like object
  - Agents: callable returning an `IAgent` OR an import path for an agent factory
- The loader supports `allow_dynamic` flag. When false, metadata stubs are registered without importing symbols.

## Versioning
- Manifest `schema: plugins.v0` is frozen
- Component `version` follows semver; use it for packaging/marketplace, not for Python import resolution

## Idempotency and conflicts
- Re‑registering the same name/path is idempotent
- Re‑registering a name with a different path raises a registry error

## Examples
- Tools (memory/search) – see `Plugins/kits/tools/memory/plugins.v0.yaml`, `Plugins/kits/tools/search/plugins.v0.yaml`
- Bundle workflows reference these tools; bundles are packaged under `Plugins/bundles/*` with `bundle.yaml`

## Testing conventions
- Integration tests set `ICEOS_PLUGIN_MANIFESTS` to the two toolkit manifests
- The Docker test image pre‑registers `writer_tool` for smoke runs

## Non‑goals
- Signing/verification, dependency resolution, and remote registry are out of scope for v0
