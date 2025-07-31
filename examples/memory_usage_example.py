"""Example demonstrating the improved memory architecture.

This shows:
1. Simplified memory configuration
2. Dependency injection pattern
3. Analytics capabilities
4. Clear separation between context and memory
"""

import asyncio
from typing import Dict, Any

from ice_core.memory import UnifiedMemory, UnifiedMemoryConfig
from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig


async def demonstrate_simplified_configuration():
    """Show how to use the simplified memory configuration."""
    print("🔧 Simplified Memory Configuration")
    print("=" * 50)
    
    # Simple configuration with smart defaults
    memory_config = UnifiedMemoryConfig(
        backend="redis",
        enable_vector_search=True,
        domains=["marketplace", "pricing", "inventory"]
    )
    
    # Create unified memory
    memory = UnifiedMemory(memory_config)
    await memory.initialize()
    
    print("✅ Memory initialized with simplified config")
    print(f"   Backend: {memory_config.backend}")
    print(f"   Vector search: {memory_config.enable_vector_search}")
    print(f"   Domains: {memory_config.domains}")
    print()


async def demonstrate_dependency_injection():
    """Show dependency injection pattern for agents."""
    print("💉 Dependency Injection Pattern")
    print("=" * 50)
    
    # Create memory instance
    memory = UnifiedMemory(UnifiedMemoryConfig())
    await memory.initialize()
    
    # Create agent with injected memory
    agent_config = MemoryAgentConfig(
        enable_memory=True,
        memory_config=None  # Will use injected memory
    )
    
    agent = MemoryAgent(agent_config, memory=memory)
    
    print("✅ Agent created with injected memory")
    print(f"   Memory instance: {type(agent.memory).__name__}")
    print(f"   Memory enabled: {agent.config.enable_memory}")
    print()


async def demonstrate_analytics():
    """Show the new analytics capabilities."""
    print("📊 Memory Analytics")
    print("=" * 50)
    
    memory = UnifiedMemory(UnifiedMemoryConfig())
    await memory.initialize()
    
    # Store some test data
    await memory.remember_fact("User prefers dark mode", {"user_id": "123"})
    await memory.remember_episode({
        "user_id": "123",
        "action": "purchase",
        "timestamp": "2024-01-01T10:00:00Z"
    })
    await memory.remember_procedure("checkout", ["add_to_cart", "payment", "confirmation"])
    
    # Get analytics
    usage_stats = await memory.get_usage_stats()
    domain_analytics = await memory.get_domain_analytics()
    performance_metrics = await memory.get_performance_metrics()
    
    print("📈 Usage Statistics:")
    for mem_type, stats in usage_stats.items():
        print(f"   {mem_type}: {stats.get('entry_count', 0)} entries")
    
    print("\n🎯 Domain Analytics:")
    for domain, usage in domain_analytics["domain_usage"].items():
        print(f"   {domain}: {sum(usage.values())} total entries")
    
    print("\n⚡ Performance Metrics:")
    for mem_type, metrics in performance_metrics.items():
        if "error" not in metrics:
            print(f"   {mem_type}: {metrics['write_time_ms']}ms write, {metrics['read_time_ms']}ms read")
    print()


async def demonstrate_memory_vs_context():
    """Show the clear separation between memory and context."""
    print("🧠 Memory vs Context Separation")
    print("=" * 50)
    
    # Long-term memory (persistent)
    memory = UnifiedMemory(UnifiedMemoryConfig())
    await memory.initialize()
    
    # Store long-term facts
    await memory.remember_fact("User prefers dark mode")
    await memory.remember_fact("User is a premium subscriber")
    
    # Context is short-term (execution state)
    # This would typically be managed by the context manager
    execution_context = {
        "current_node": "checkout_flow",
        "session_id": "abc123",
        "temp_data": "shopping_cart_items"
    }
    
    print("💾 Long-term Memory (persistent):")
    facts = await memory.search("User prefers", memory_types=["semantic"])
    for fact in facts:
        print(f"   - {fact.content}")
    
    print("\n⚡ Execution Context (short-term):")
    for key, value in execution_context.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Clear separation maintained:")
    print("   - Memory: Long-term, persistent, searchable")
    print("   - Context: Short-term, execution state, temporary")
    print()


async def main():
    """Run all demonstrations."""
    print("🚀 Memory Architecture Improvements Demo")
    print("=" * 60)
    print()
    
    await demonstrate_simplified_configuration()
    await demonstrate_dependency_injection()
    await demonstrate_analytics()
    await demonstrate_memory_vs_context()
    
    print("✅ All demonstrations completed successfully!")


if __name__ == "__main__":
    asyncio.run(main()) 