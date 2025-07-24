# Changelog

## [Unreleased]

### Added
- **Direct Execution API**: New endpoints for executing individual tools, agents, units, and chains
  - `POST /api/v1/tools/{name}` - Execute tools with automatic blueprint creation
  - `POST /api/v1/agents/{name}` - Execute agents directly
  - `POST /api/v1/units/{name}` - Execute units directly  
  - `POST /api/v1/chains/{name}` - Execute chains directly
  - All endpoints support sync/async modes and return AI suggestions
  - Maintains full telemetry and analysis benefits while simplifying UX

### Changed
- Updated `UnitRegistry` to support iteration like other registries
- Enhanced API documentation with direct execution examples

## [0.7.0] – 2024-12-30 🚀 **Spatial Computing Release**

### 🎯 Major: Workflow Engine - The Spatial Computing Powerhouse

**Enhanced Workflow Engine**: The core Workflow engine now powers spatial computing experiences.

#### 🧠 **Graph Intelligence**
- **NetworkX Integration**: Advanced dependency analysis, bottleneck detection, and optimization suggestions
- **Pattern Recognition**: AI-powered workflow refactoring opportunities  
- **Critical Path Analysis**: Intelligent execution path optimization
- **Parallelization Intelligence**: Smart suggestions for performance improvements

#### 🎨 **Canvas-Ready Architecture**
- **Spatial Layout Hints**: Rich positioning data for visual programming interfaces
- **Scope Organization**: Contextual grouping with semantic meaning for canvas regions
- **Real-time Collaboration**: Cursor tracking, shared state, and collaborative editing support
- **Interactive Modes**: Freeform, execution flow, scope selection, and temporal debugging modes

#### 🤖 **Frosty AI Integration**  
- **Contextual Suggestions**: Graph-position-aware recommendations for next nodes
- **Intelligent Optimization**: AI-powered workflow improvements based on execution patterns
- **Interactive Canvas Companion**: Seamless integration points for AI assistance
- **Pattern-Based Learning**: Suggestions improve based on workflow usage patterns

#### ⚡ **Enhanced Execution**
- **Spatial Execution Tracking**: Real-time canvas updates during execution
- **Event Streaming**: Live execution events for canvas visualization
- **Incremental Execution**: Debug-friendly step-by-step execution with checkpoints
- **Enhanced Metrics**: Spatial utilization, collaboration activity, and optimization opportunities

### 🌐 **API Enhancements**
- **Graph Intelligence Endpoints**: `/workflows/{id}/graph/metrics`, `/graph/layout`, `/graph/analysis`
- **Node Impact Analysis**: `/workflows/{id}/nodes/{node_id}/impact` for dependency impact assessment
- **AI Suggestions**: `/workflows/{id}/nodes/{node_id}/suggestions` for Frosty integration
- **Pattern Matching**: `/workflows/{id}/graph/patterns` for workflow refactoring opportunities

### 🔧 **Developer Experience**
- **Enhanced SDK**: All components updated for spatial computing readiness
- **Comprehensive Demo**: Updated `comprehensive_demo.py` showcases all new capabilities
- **Documentation Overhaul**: All READMEs updated with spatial computing focus

### 🏗️ **Architecture Evolution**

- **Spatial Features Toggle**: Optional spatial computing features for gradual adoption
- **Collaboration Support**: Built-in real-time collaboration infrastructure
- **Canvas State Management**: Comprehensive state tracking for visual interfaces

### 🧪 **Testing & Quality**
- **Rigorous Test Suite**: Integration tests for service initialization, registry integrity, schema validation, and architectural boundaries
- **Demo Validation**: Comprehensive demo runs successfully with all new features
- **Import Structure**: Clean import paths and resolved circular dependencies

---

## [0.6.0] – 2024-12-30

### Added
- **Unified Registry** - Single registry for all node types, tools, chains, and executors
- **Service Initialization** - Clean initialization without layer violations via `initialize_services()`
- **Comprehensive Platform Vision** - Updated vision document with three-tier architecture
- **Config Organization** - Configuration files organized into `config/` directory structure

### Changed
- **SDK Structure** - Reduced from ~20 directories to 8 essential ones
- **Layer Boundaries** - Enforced strict architectural boundaries, no upward dependencies
- **Import Paths** - All imports now use `ice_core.models` directly
- **Test Organization** - Tests properly configured with new config locations

### Removed
- **Legacy Code** - All backward compatibility shims and deprecated aliases
- **Redundant Directories** - Removed nodes/, events/, dsl/, interfaces/, protocols/, core/, models/ from SDK
- **Compatibility Layers** - Removed ToolContext, function_tool, skill aliases
- **Dead Code** - Removed unused registry modules and empty directories

### Fixed
- **Import Errors** - Fixed all circular dependencies and layer violations
- **Test Failures** - Fixed Pydantic validation errors in LLM operators
- **Configuration** - All tools now properly reference organized config files

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