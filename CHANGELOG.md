# Changelog

All notable changes to iceOS will be documented in this file.

## [Unreleased]

### Major Architectural Refactoring - Clean Architecture Achieved

#### Changed
- **Moved ALL execution logic to orchestrator layer**
  - `WorkflowExecutionService` moved from SDK to orchestrator
  - Created new `ToolExecutionService` in orchestrator 
  - SDK `ToolService` now purely registry/discovery (no execution)
  - All runtime concerns now properly isolated in orchestrator

- **Consolidated context management in orchestrator**
  - Moved `formatter.py`, `types.py`, `type_manager.py` from SDK to orchestrator
  - All context components now in single layer
  - No more split context functionality

- **Moved shared components to core**
  - `exceptions.py` moved from SDK to core
  - `token_counter.py` moved from SDK to core utils
  - `config.py` (runtime config) moved from SDK to orchestrator
  - Cost tracking moved from SDK to orchestrator

- **Simplified SDK to pure development kit**
  - Removed `WorkflowExecutionService` 
  - Removed `BuilderService` (builders used directly)
  - Removed empty `providers` directory
  - SDK now only contains: tools, builders, ServiceLocator, dev utilities

- **Updated service initialization**
  - Split `initialize_services()` into `initialize_sdk()` and `initialize_orchestrator()`
  - Each layer initializes its own services
  - Clean dependency flow via ServiceLocator
