# Changelog

## [0.5.0-beta] – 2025-07-07

### Added
- **Canonical CLI** ‑ new commands: `init`, `create`, `run`, `ls`, `edit`, `delete`, `doctor`, `update`, `copilot`.
- End-to-end quick-start workflow in README.

### Changed
- Docs and examples now use the simplified CLI exclusively.
- Refactored `ice_cli.cli` for uniform option style and error handling.

### Removed
- Legacy command groups (`sdk`, `tool`, `chain`, `make`, `node`, `space`, `connect`, `flow`, `prompt`).
- Obsolete scaffold files used during refactor.

### Fixed
- Typer metavar bug patch; `ice --help` works on all platforms.
- Fresh install path validated (`pip install iceos && ice init demo`).

---
Older versions are pre-release research iterations and are not listed here. 