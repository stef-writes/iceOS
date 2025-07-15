# Orchestrator Execution Flow

*Work‐in‐progress – high-level sequence diagram coming soon.*
 
1. **ScriptChain** received → validate config
2. Build dependency graph → topological sort
3. Schedule node execution (async)
4. Collect NodeExecutionResult → aggregate
5. Emit metrics / telemetry 