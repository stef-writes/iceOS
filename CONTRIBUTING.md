# Contribution Guidelines

Welcome to iceOS - the spatial computing powerhouse! 🚀

## Spatial Computing Vision
iceOS is designed for both traditional workflow execution and future canvas-based experiences. When contributing:
- Consider how features will work in visual programming interfaces
- Design with real-time collaboration in mind
- Think about Frosty AI integration opportunities
- Ensure compatibility with NetworkX graph intelligence

## Development Setup
```bash
# Clone and install
git clone https://github.com/your-org/iceos.git
cd iceos
poetry install --with dev
# Optional: install pre-commit hooks
# poetry run pre-commit install
```

## Code Quality Gates
All new code must pass:
```bash
make lint    # Ruff linting (config: config/linting/ruff.toml)
make type    # MyPy strict typing (config: config/typing/mypy.ini)
make test    # Pytest (unit) (config: config/testing/pytest.ini)
```

### Quality Requirements
- Pydantic models for all public APIs
- Type hints on all public functions
- Google-style docstrings with examples

## Architecture Rules
1. **Layer Dependencies**: ice_core → ice_builder → ice_orchestrator → ice_api
2. **No Cross-Layer Imports**: All cross-layer calls go through stable service interfaces under `services/*`. Do not use service locators.
3. **External I/O**: Only in Tool implementations
4. **Dynamic Imports**: Only in the plugin registry/manifest loader modules

## Workflow Development Guidelines

### Spatial Computing Features
When working with the Workflow engine:
- **Spatial Metadata**: Always include layout hints and positioning data in new features
- **Real-time Events**: Emit spatial events for canvas updates using `_emit_spatial_event()`
- **Graph Intelligence**: Leverage NetworkX analysis in `GraphAnalyzer` for optimization suggestions
- **Collaboration Support**: Consider multi-user scenarios and state synchronization

### Workflow Parameters
- Enable spatial features with `enable_spatial_features=True`
- Include Frosty integration with `enable_frosty_integration=True`
- Support collaboration with `enable_collaboration=True`

## Deprecation Process
1. Add `@deprecated(version, replacement)` decorator
2. Log structured warning with replacement path
3. Update CHANGELOG.md with deprecation notice
4. Maintain for 2 minor versions before removal

## Testing Guidelines
- Unit tests for business logic
- Integration tests for layer interactions
- Use `pytest -c config/testing/pytest.ini`
- Prefer validating against real Pydantic models and schemas; keep external network calls behind tool boundaries
- Test both success and error paths

## Documentation
- Update relevant docs in `docs/`
- Add/update docstrings
- Include code examples
- Build docs locally with `poetry run mkdocs build`

## Pull Request Process
1. Fork and create feature branch
2. Make changes following guidelines above
3. Ensure all tests pass: `make ci`
4. Update CHANGELOG.md
5. Submit PR with clear description
6. Address review feedback

## Configuration Files
Configuration is organized in `config/`:
- `config/linting/ruff.toml` - Linting rules
- `config/typing/mypy.ini` - Type checking settings
- `config/testing/pytest.ini` - Test configuration

## Questions?
- Check existing issues/discussions
- Review architecture docs: `docs/ARCHITECTURE.md`
- Ask in discussions for clarification
