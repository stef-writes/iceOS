# FB Marketplace Seller - Architecture Decisions

## Nodes vs Agents Breakdown

### Should be AGENTS (need reasoning/iteration):
1. **ConversationManagerAgent** ✅
   - Handles multi-turn conversations with buyers
   - Needs to understand context and intent
   - Makes decisions about responses

2. **ListingCreatorAgent** ✅ 
   - Already an agent in our design
   - Creates compelling listings using AI

3. **PricingOptimizerAgent** ✅
   - Analyzes market data and makes pricing decisions
   - May need multiple iterations to find optimal price
   - Uses LLM for strategic pricing

### Should be NODES (deterministic/single-step):
1. **InventoryAnalyzerNode** ✅
   - Simple filtering based on rules
   - No AI reasoning needed

2. **ImageProcessorNode** ✅
   - Deterministic image enhancement
   - No decision-making required

3. **OrderHandlerNode** ✅
   - Follows structured workflow
   - No complex reasoning

4. **MetricsTrackerNode** ✅
   - Collects and calculates metrics
   - Pure data processing

## Memory Requirements

### For MVP:
- **Short-term**: Use Redis for active conversations
- **Product Knowledge**: Simple key-value store for listings
- **Customer History**: Basic SQLite or Redis

### Future Enhancements:
- **Vector Memory**: For semantic search of past conversations
- **Knowledge Graph**: For understanding product relationships
- **Long-term Memory**: For learning from sales patterns

## Implementation Strategy

1. **Phase 1 (Now)**: Build with simple memory (Redis/dict)
2. **Phase 2**: Add vector search for conversations
3. **Phase 3**: Implement full knowledge graph

The current iceOS architecture supports this evolution! 