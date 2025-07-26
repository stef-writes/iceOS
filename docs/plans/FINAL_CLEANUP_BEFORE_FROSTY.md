# Final Cleanup Before Frosty Implementation

## Goal
Get the codebase into "picture perfect" form - a clean, well-documented, fully-tested foundation for implementing Frosty.

## Outstanding Issues to Fix

### 1. Remove ALL Legacy/Compatibility Code ❗
Found 40+ instances of backward compatibility code that should be removed:

#### Files with backward compat to clean:
- [ ] `src/ice_sdk/tools/base.py` - Remove legacy ToolContext & function_tool
- [ ] `src/ice_sdk/tools/service.py` - Remove legacy discovery stub
- [ ] `src/ice_sdk/unified_registry.py` - Remove backward compat helpers
- [ ] `src/ice_sdk/utils/errors.py` - Remove deprecated SkillExecutionError
- [ ] `src/ice_sdk/plugin_discovery.py` - Remove legacy function
- [ ] `src/ice_sdk/utils/hashing.py` - Remove "thin shim"
- [ ] `src/ice_core/utils/deprecation.py` - Keep (needed for future deprecations)
- [ ] Remove all "Accept legacy input_data" patterns in tools

### 2. Implement NotImplementedError Stubs 🔧
- [ ] `src/ice_sdk/context/formatter.py` - Implement format_context()
- [ ] `src/ice_orchestrator/nodes/code.py` - Implement CodeNode execution
- [ ] Base classes with NotImplementedError are OK (abstract methods)

### 3. Complete TODOs 📝
- [ ] `src/ice_core/models/node_models.py:373` - Migrate to unified registry
- [ ] `src/ice_sdk/tools/service.py:144` - Re-implement plugin discovery
- [ ] `src/ice_orchestrator/validation/chain_validator.py:93,97` - SBOM & privacy (defer to Phase 2)

### 4. Fix Test Failures 🧪
- [ ] Fix Pydantic validation errors in LLM operators
- [ ] Ensure all tests pass with `make test`
- [ ] Run mypy --strict and fix any issues

### 5. Documentation Polish 📚
- [ ] Update all docstrings to Google style
- [ ] Add code examples to key modules
- [ ] Create API reference with mkdocs
- [ ] Update README with current architecture

### 6. Remove Unused Plans 🗑️
- [ ] Delete `docs/plans/docker_poetry_strategy.md` (empty)
- [ ] Delete `docs/api/frosty.md` (will recreate when implementing)
- [ ] Keep `plugin_governance_spec.md` (future roadmap)
- [ ] Keep `mcp.yaml` (active API spec)

### 7. Code Organization 🏗️
- [ ] Ensure all files follow naming conventions
- [ ] Remove any empty __init__.py files
- [ ] Consolidate related utilities
- [ ] Check for duplicate functionality

### 8. Type Safety 🔒
- [ ] Add missing type hints
- [ ] Use TypeAlias for complex types
- [ ] Ensure all public APIs are fully typed
- [ ] Enable strict mypy checking

### 9. Performance & Security 🚀
- [ ] Remove any debug print statements
- [ ] Ensure no hardcoded secrets/URLs
- [ ] Add proper logging levels
- [ ] Review error handling patterns

### 10. Final Verification ✅
- [ ] Run full test suite: `make test`
- [ ] Type check: `mypy --strict src/`
- [ ] Linting: `ruff check src/`
- [ ] Coverage: `make coverage` (aim for >80%)
- [ ] Fresh install test in new venv

## Success Criteria

The codebase is "picture perfect" when:

1. **Zero legacy code** - No backward compatibility shims
2. **Zero TODOs** - All marked work completed or moved to issues
3. **Zero NotImplementedError** - All stubs implemented
4. **100% tests pass** - Including mypy strict mode
5. **Clean architecture** - Clear layer boundaries maintained
6. **Comprehensive docs** - Every public API documented
7. **Consistent style** - All code follows project conventions

## Estimated Timeline

- Phase 1: Remove legacy code (2-3 hours)
- Phase 2: Implement stubs (1-2 hours) 
- Phase 3: Fix tests (2-3 hours)
- Phase 4: Documentation (2-3 hours)
- Phase 5: Final verification (1 hour)

**Total: 8-12 hours of focused work**

## After This Is Done

With a pristine codebase, we can focus 100% on designing and implementing Frosty:
- Clean foundation to build on
- No technical debt to work around
- Clear patterns to follow
- Comprehensive tests to prevent regressions

The interpreter → compiler → runtime architecture is ready for its crown jewel! 