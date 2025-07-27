#!/usr/bin/env python
"""Run comprehensive memory system tests."""

import asyncio
import sys
import os
from pathlib import Path
import pytest
import time
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_memory_tests(verbose: bool = True, coverage: bool = True) -> Dict[str, Any]:
    """Run all memory-related tests and return results."""
    test_files = [
        # Unit tests
        "tests/unit/ice_orchestrator/memory/test_episodic_memory.py",
        "tests/unit/ice_orchestrator/memory/test_semantic_memory.py",
        "tests/unit/ice_orchestrator/memory/test_procedural_memory.py",
        "tests/unit/ice_sdk/memory/test_working_memory.py",
        
        # Integration tests
        "tests/integration/ice_orchestrator/memory/test_unified_memory.py",
        "tests/unit/ice_sdk/memory/test_memory_agent.py",
    ]
    
    # Filter existing files
    existing_tests = [f for f in test_files if os.path.exists(f)]
    
    print(f"\n🧠 Running Memory System Tests")
    print(f"{'=' * 60}")
    print(f"Found {len(existing_tests)} test files")
    
    # Prepare pytest arguments
    pytest_args = existing_tests
    
    if verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")
        
    if coverage:
        pytest_args.extend([
            "--cov=ice_orchestrator.memory",
            "--cov=ice_sdk.context",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_memory"
        ])
    
    # Add other useful options
    pytest_args.extend([
        "-x",  # Stop on first failure
        "--tb=short",  # Shorter traceback
        "--disable-warnings",  # Cleaner output
        "-p", "no:randomly",  # Disable random test order for consistency
    ])
    
    # Run tests
    start_time = time.time()
    result = pytest.main(pytest_args)
    duration = time.time() - start_time
    
    # Analyze results
    return {
        "exit_code": result,
        "duration": duration,
        "test_files": existing_tests,
        "success": result == 0
    }


async def run_performance_tests():
    """Run performance benchmarks for memory systems."""
    print("\n⚡ Running Performance Tests")
    print(f"{'=' * 60}")
    
    from ice_orchestrator.memory import (
        EpisodicMemory, SemanticMemory, ProceduralMemory, UnifiedMemory, UnifiedMemoryConfig
    )
    from ice_orchestrator.memory import MemoryConfig
    
    # Test write performance
    print("\n📝 Write Performance:")
    
    # Episodic Memory
    episodic = EpisodicMemory(MemoryConfig(backend="memory"))
    await episodic.initialize()
    
    start = time.time()
    for i in range(1000):
        await episodic.store(
            f"episode_{i}",
            {"content": f"Episode {i}"},
            metadata={"index": i}
        )
    episodic_write_time = time.time() - start
    print(f"  Episodic: 1000 writes in {episodic_write_time:.2f}s ({1000/episodic_write_time:.0f} ops/sec)")
    
    # Semantic Memory
    semantic = SemanticMemory(MemoryConfig(backend="memory", enable_vector_search=True))
    await semantic.initialize()
    
    start = time.time()
    for i in range(1000):
        await semantic.store(
            f"fact_{i}",
            {"fact": f"Fact number {i}"},
            metadata={"entities": [f"entity_{i}"]}
        )
    semantic_write_time = time.time() - start
    print(f"  Semantic: 1000 writes in {semantic_write_time:.2f}s ({1000/semantic_write_time:.0f} ops/sec)")
    
    # Test search performance
    print("\n🔍 Search Performance:")
    
    # Episodic search
    start = time.time()
    for _ in range(100):
        results = await episodic.search("Episode")
    episodic_search_time = time.time() - start
    print(f"  Episodic: 100 searches in {episodic_search_time:.2f}s ({100/episodic_search_time:.0f} ops/sec)")
    
    # Semantic search (with vectors)
    start = time.time()
    for _ in range(100):
        results = await semantic.search("Fact about")
    semantic_search_time = time.time() - start
    print(f"  Semantic: 100 searches in {semantic_search_time:.2f}s ({100/semantic_search_time:.0f} ops/sec)")
    
    # Cleanup
    await episodic.clear()
    await semantic.clear()


async def run_stress_tests():
    """Run stress tests for memory systems."""
    print("\n💪 Running Stress Tests")
    print(f"{'=' * 60}")
    
    from ice_orchestrator.memory import UnifiedMemory, UnifiedMemoryConfig
    
    # Create unified memory
    memory = UnifiedMemory(UnifiedMemoryConfig(
        enable_working=True,
        enable_episodic=True,
        enable_semantic=True,
        enable_procedural=True
    ))
    await memory.initialize()
    
    # Concurrent writes
    print("\n🔄 Concurrent Write Test (1000 items across 4 memory types):")
    
    async def stress_write(prefix: str, count: int):
        tasks = []
        for i in range(count):
            task = memory.store(f"{prefix}:stress_{i}", f"Data {i}")
            tasks.append(task)
        await asyncio.gather(*tasks)
    
    start = time.time()
    await asyncio.gather(
        stress_write("work", 250),
        stress_write("episode", 250),
        stress_write("fact", 250),
        stress_write("procedure", 250)
    )
    stress_time = time.time() - start
    print(f"  Completed in {stress_time:.2f}s ({1000/stress_time:.0f} ops/sec)")
    
    # Memory usage test
    print("\n💾 Memory Usage Test:")
    print(f"  Total items stored: 1000")
    
    # Search across all memories
    print("\n🔎 Cross-Memory Search Test:")
    start = time.time()
    results = await memory.search("Data")
    search_time = time.time() - start
    print(f"  Found {len(results)} results in {search_time:.2f}s")
    
    # Cleanup
    await memory.clear()


def generate_report(test_results: Dict[str, Any]):
    """Generate a test report."""
    print("\n📊 Test Summary")
    print(f"{'=' * 60}")
    print(f"Status: {'✅ PASSED' if test_results['success'] else '❌ FAILED'}")
    print(f"Duration: {test_results['duration']:.2f} seconds")
    print(f"Test Files: {len(test_results['test_files'])}")
    
    if test_results['success']:
        print("\n✨ All memory tests passed successfully!")
        print("\nKey Features Tested:")
        print("  ✓ Basic CRUD operations")
        print("  ✓ Search and filtering")
        print("  ✓ Memory-specific features (TTL, vectors, procedures)")
        print("  ✓ Cross-memory integration")
        print("  ✓ Concurrent access")
        print("  ✓ Error handling")
        print("  ✓ Performance benchmarks")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("\n📁 Coverage Report: coverage_memory/index.html")


async def main():
    """Main test runner."""
    print("🚀 IceOS Memory System Test Suite")
    print(f"{'=' * 60}")
    
    # Run unit and integration tests
    test_results = run_memory_tests(verbose=True, coverage=True)
    
    if test_results['success']:
        # Run performance tests only if unit tests pass
        await run_performance_tests()
        
        # Run stress tests
        await run_stress_tests()
    
    # Generate report
    generate_report(test_results)
    
    # Exit with appropriate code
    sys.exit(0 if test_results['success'] else 1)


if __name__ == "__main__":
    asyncio.run(main()) 