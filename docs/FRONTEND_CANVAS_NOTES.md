# Frontend Canvas & Frosty: Key Considerations

## Executive Summary
The canvas vision extends far beyond "text to workflow" - it's a **spatial computing platform** where Frosty acts as an embedded co-creator understanding context at multiple granularities.

## Multi-Level Translation Architecture

### Granularity Levels
1. **Text → Tool**: Atomic utilities ("parse CSV" → CSVReaderTool)
2. **Text → Node**: Configured components ("wait 5 min" → DelayNode)
3. **Text → Chain**: Connected sequences ("if error retry" → TryCatch chain)
4. **Text → Workflow**: Complete systems ("daily reports" → Full pipeline)

### Why This Matters
- Users think at different abstraction levels
- Progressive complexity disclosure
- Enables both quick tasks and complex systems
- Natural learning curve from simple to advanced

## Technical Challenges

### 1. Visual Interpretation (HIGH RISK)
**Challenge**: Converting sketches/drawings to executable logic
**Why Hard**: 
- Ambiguous visual representations
- Cultural differences in diagramming
- Imprecise user drawings
- Intent vs literal interpretation

**Mitigation**:
- Start with structured inputs (not freeform sketches)
- Use standardized visual language
- Confidence scoring with clarification UI
- Learn from corrections

### 2. Canvas Performance (MEDIUM RISK)
**Challenge**: Smooth interaction with 10K+ nodes
**Why Hard**:
- Browser memory limits
- Rendering performance
- Network sync overhead
- Mobile device constraints

**Mitigation**:
- WebGL acceleration
- Viewport virtualization
- Level-of-detail rendering
- Progressive loading

### 3. Real-time Collaboration (HIGH COMPLEXITY)
**Challenge**: Multiple users editing simultaneously
**Why Hard**:
- Conflict resolution
- Network latency
- State consistency
- Permission boundaries

**Mitigation**:
- CRDT or OT algorithms
- Optimistic updates
- Conflict visualization
- Region locking

### 4. Context Boundaries (MEDIUM RISK)
**Challenge**: Spatial permissions and governance
**Why Hard**:
- Visual representation of permissions
- Inheritance rules
- Dynamic boundaries
- Audit requirements

**Mitigation**:
- Visual permission indicators
- Explicit boundary zones
- Inheritance visualization
- Activity logging

## Backend Architecture Requirements

### Incremental Blueprint Construction ✅ IMPLEMENTED!
Current: All-or-nothing blueprints
~~Needed~~ **Done**: Progressive assembly with partial validation

```python
# Already implemented in MCP API!
# POST /api/v1/mcp/blueprints/partial - Create partial blueprint
# PUT /api/v1/mcp/blueprints/partial/{id} - Add/remove/update nodes
# POST /api/v1/mcp/blueprints/partial/{id}/finalize - Convert to executable

# Example usage:
partial = PartialBlueprint()
partial.add_node(PartialNodeSpec(
    id="csv_reader",
    type="tool", 
    pending_outputs=["data"]
))
partial._validate_incremental()  # Updates suggestions
# Returns: {"next_suggestions": [{"type": "llm", "reason": "Process tool output"}]}
```

This means the canvas frontend can:
1. Start with empty blueprint
2. Add nodes incrementally as user describes/draws
3. Get AI suggestions after each addition
4. Show validation errors in real-time
5. Finalize when ready to execute

### Spatial Context Engine
- Map canvas regions to execution contexts
- Maintain spatial relationships in backend
- Support zoom-level aware queries
- Enable spatial permissions

## AI/ML Considerations

### Frosty's Enhanced Requirements
1. **Multi-modal understanding**: Text + visual + spatial
2. **Context window management**: Large canvas awareness
3. **Progressive refinement**: Learn from corrections
4. **Confidence scoring**: Know when to ask for clarification

### Training Data Needs
- 10K+ sketch → blueprint examples
- Spatial layout patterns
- Common user correction sequences
- Multi-level intent classifications

## Implementation Phases

### Phase 1: Text-Only Canvas (Lower Risk)
- Canvas as spatial text organizer
- Frosty understands text in regions
- No visual interpretation yet
- Focus on multi-level translation

### Phase 2: Structured Visual Elements
- Predefined visual components
- Drag-drop from palette
- Connected by lines
- Frosty assists connections

### Phase 3: Freeform Sketching
- Sketch recognition
- Intent interpretation
- Visual to logical mapping
- Full "Make Real" experience

## Open Questions

1. **Version Control**: How to diff/merge visual layouts?
2. **Testing**: How to test visual workflows?
3. **Accessibility**: How to make spatial UI accessible?
4. **Migration**: How to import existing code-based workflows?
5. **Export**: How to share workflows outside the platform?

## Success Metrics

### Technical
- Canvas load time < 2s for 1K nodes
- Real-time sync latency < 100ms
- Visual interpretation accuracy > 80%
- Collaboration conflicts < 1%

### User Experience
- Time to first working node < 30s
- Natural language success rate > 90%
- User correction rate < 10%
- Daily active canvas users > 1K

## Conclusion

This vision is ambitious but achievable with phased implementation. Key risks are visual interpretation accuracy and real-time collaboration at scale. Starting with text-based canvas and structured components reduces initial complexity while delivering value.

The multi-level translation (Tool → Node → Chain → Workflow) is a powerful concept that should guide the architecture from day one. 