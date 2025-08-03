# Refactoring Plan: Merging Frosty into ice_builder

## Current State Issues:
1. **Duplication**: Both `frosty` and `ice_builder.nl` claim to handle natural language → blueprint conversion
2. **Empty Stubs**: `ice_builder.nl.cognitive.*` is an elaborate structure with zero implementation
3. **Confusion**: Unclear separation of concerns between the two packages
4. **Wasted Effort**: The cognitive architecture in ice_builder was never implemented

## Proposed New Structure:

### Option 1: Merge Frosty into ice_builder (RECOMMENDED)
```
src/ice_builder/
├── dsl/                    # Keep as-is: Programmatic builders
│   ├── workflow.py
│   ├── agent.py
│   └── ...
├── nl/                     # Natural Language processing (from Frosty)
│   ├── __init__.py         # Export generate_blueprint, etc.
│   ├── orchestrator.py     # MultiLLMOrchestrator (from frosty)
│   ├── pipeline.py         # InteractivePipeline (from frosty)
│   ├── providers/          # LLM providers (from frosty.core.providers)
│   │   ├── base.py
│   │   ├── openai_gpt4o.py
│   │   ├── deepseek_r1.py
│   │   └── anthropic_claude3.py
│   ├── generation/         # Blueprint generation logic
│   │   ├── atomic_principles.py
│   │   ├── heuristics.py
│   │   ├── prompts.py
│   │   └── registry_integration.py
│   └── cognitive/          # DELETE - it's all empty stubs!
├── utils/                  # Keep existing utils
└── public.py              # Update to export NL functions too
```

### Benefits:
1. **Single source of truth** for blueprint authoring (both DSL and NL)
2. **No more confusion** about where NL processing lives
3. **Delete empty stubs** that add no value
4. **Cleaner imports**: `from ice_builder.nl import generate_blueprint`
5. **Maintains backward compatibility** through public.py

### Option 2: Keep Frosty separate but clarify roles
- ice_builder: Low-level DSL only
- frosty: High-level NL interface that uses ice_builder.dsl
- Problem: Still confusing, ice_builder.nl would need to be deleted

## Migration Steps:
1. Move `src/frosty/blueprint_generation/*` → `src/ice_builder/nl/generation/`
2. Move `src/frosty/core/providers/*` → `src/ice_builder/nl/providers/`
3. Delete `src/ice_builder/nl/cognitive/*` (all empty stubs)
4. Update imports in moved files
5. Create new `src/ice_builder/nl/__init__.py` with public exports
6. Update `ice_builder.public` to export NL functions
7. Keep `frosty` package as a thin CLI wrapper that imports from ice_builder
8. Update tests and documentation

## CLI Changes:
- Keep `frosty` CLI command but have it import from `ice_builder.nl`
- OR: Add `ice generate` subcommand and deprecate separate `frosty` command

## Backward Compatibility:
- All existing `ice_builder.dsl` imports remain unchanged
- `ice_builder.public` will export both DSL and NL functions
- Frosty CLI can remain as a compatibility wrapper