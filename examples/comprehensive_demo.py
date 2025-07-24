#!/usr/bin/env python3
"""
🧊 iceOS Comprehensive Demo
==========================

This demo showcases the complete iceOS platform capabilities:

1. Incremental Blueprint Construction (Frosty-style)
2. Cost Estimation before execution
3. Real-time event streaming during execution
4. Data processing pipeline (CSV → Analysis → Report)
5. Nested workflows and composition
6. Debug information and monitoring

Each section can be used as a standalone example for that feature.

Prerequisites:
    - iceOS API server running: make dev
    - Sample data file: examples/data/sales_data.csv
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize Rich console for beautiful output
console = Console()

# API Configuration
API_BASE = "http://localhost:8000/api/v1/mcp"


async def section_1_incremental_construction():
    """Section 1: Build a workflow incrementally (like Frosty would)."""
    console.print("\n[bold blue]📝 Section 1: Incremental Blueprint Construction[/bold blue]")
    console.print("Building a simple data analysis workflow step by step...\n")
    
    async with httpx.AsyncClient() as client:
        # 1.1 Start with empty blueprint
        console.print("1.1 Creating empty blueprint...")
        resp = await client.post(f"{API_BASE}/blueprints/partial")
        partial = resp.json()
        bp_id = partial["blueprint_id"]
        console.print(f"   ✅ Created: [green]{bp_id}[/green]")
        
        # 1.2 Add CSV reader
        console.print("\n1.2 Adding CSV reader node...")
        resp = await client.put(
            f"{API_BASE}/blueprints/partial/{bp_id}",
            json={
                "action": "add_node",
                "node": {
                    "id": "load_data",
                    "type": "tool",
                    "tool_name": "csv_reader",
                    "name": "Load Sales Data",
                    "tool_args": {
                        "file_path": "examples/data/sales_data.csv"
                    },
                    "input_schema": {
                        "file_path": "str"
                    },
                    "output_schema": {
                        "rows": "list[dict]",
                        "headers": "list[str]"
                    }
                }
            }
        )
        partial = resp.json()
        
        # Show AI suggestions
        if partial.get("next_suggestions"):
            console.print("   🤖 AI Suggestions:")
            for suggestion in partial["next_suggestions"]:
                console.print(f"      - {suggestion['type']}: {suggestion['reason']}")
        
        # 1.3 Add simple LLM analyzer
        console.print("\n1.3 Adding AI analyzer...")
        resp = await client.put(
            f"{API_BASE}/blueprints/partial/{bp_id}",
            json={
                "action": "add_node",
                "node": {
                    "id": "analyze_trends",
                    "type": "llm",
                    "name": "Analyze Sales Trends",
                    "model": "gpt-4",
                    "prompt": "Analyze this sales data and provide insights: {load_data.rows}",
                    "dependencies": ["load_data"],
                    "input_schema": {
                        "rows": "list[dict]"
                    },
                    "output_schema": {
                        "analysis": "dict"
                    },
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "llm_config": {
                        "provider": "openai"
                    }
                }
            }
        )
        
        # 1.4 Check if complete
        partial = resp.json()
        console.print(f"\n1.4 Blueprint complete: [green]{partial['is_complete']}[/green]")
        
        # 1.5 Finalize
        console.print("\n1.5 Finalizing blueprint...")
        resp = await client.post(f"{API_BASE}/blueprints/partial/{bp_id}/finalize")
        final = resp.json()
        
        console.print(f"   ✅ Final blueprint: [green]{final['blueprint_id']}[/green]")
        return final["blueprint_id"]


async def section_2_cost_estimation(blueprint_id: str):
    """Section 2: Estimate costs before execution."""
    console.print("\n[bold blue]💰 Section 2: Cost Estimation[/bold blue]")
    
    # In real implementation, this would call workflow.estimate_cost()
    # For demo, we'll simulate the response
    cost_estimate = {
        "estimated_cost": "$0.08 ($0.06 - $0.10)",
        "estimated_tokens": "2,000",
        "estimated_duration": "5.2s",
        "api_calls": 2,
        "confidence": "high",
        "breakdown": {
            "load_data": {"type": "tool", "cost": "$0.00", "tokens": 0},
            "analyze_trends": {"type": "llm", "cost": "$0.08", "tokens": 2000}
        }
    }
    
    # Display cost breakdown
    table = Table(title="Cost Estimation")
    table.add_column("Node", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Cost", style="green")
    table.add_column("Tokens", style="yellow")
    
    for node_id, details in cost_estimate["breakdown"].items():
        table.add_row(
            node_id,
            details["type"],
            details["cost"],
            str(details["tokens"])
        )
    
    console.print(table)
    console.print(f"\n[bold]Total Estimated Cost: {cost_estimate['estimated_cost']}[/bold]")
    console.print(f"Estimated Duration: {cost_estimate['estimated_duration']}")
    
    return cost_estimate


async def section_3_event_streaming(blueprint_id: str):
    """Section 3: Execute with real-time event streaming."""
    console.print("\n[bold blue]🚀 Section 3: Execution with Event Streaming[/bold blue]")
    
    events_received = []
    
    async def event_handler(event: Dict[str, Any]):
        """Handle workflow events for display."""
        events_received.append(event)
        
        event_type = event.get("event_type", "unknown")
        
        if event_type == "workflow.started":
            console.print("▶️  Workflow started")
        elif event_type == "node.started":
            console.print(f"   🔄 {event.get('node_id')} started...")
        elif event_type == "node.completed":
            console.print(f"   ✅ {event.get('node_id')} completed ({event.get('duration_seconds', 0):.2f}s)")
        elif event_type == "node.failed":
            console.print(f"   ❌ {event.get('node_id')} failed: {event.get('error_message')}")
        elif event_type == "workflow.completed":
            console.print("✅ Workflow completed!")
    
    async with httpx.AsyncClient() as client:
        # Start execution
        resp = await client.post(
            f"{API_BASE}/runs",
            json={
                "blueprint_id": blueprint_id,
                "options": {"max_parallel": 5}
            }
        )
        
        if resp.status_code != 202:
            console.print(f"[red]Error: Expected 202, got {resp.status_code}[/red]")
            console.print(f"Response: {resp.text}")
            return None, []
        
        run = resp.json()
        run_id = run["run_id"]
        
        console.print(f"Started run: [green]{run_id}[/green]")
        
        # Poll for completion (in real implementation, would use SSE)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Executing workflow...", total=None)
            
            while True:
                resp = await client.get(f"{API_BASE}/runs/{run_id}")
                
                if resp.status_code == 200:
                    result = resp.json()
                    break
                    
                await asyncio.sleep(1)
        
        # Simulate events (in real implementation, these would stream)
        await event_handler({"event_type": "workflow.started"})
        await event_handler({"event_type": "node.started", "node_id": "load_data"})
        await event_handler({"event_type": "node.completed", "node_id": "load_data", "duration_seconds": 0.5})
        await event_handler({"event_type": "node.started", "node_id": "analyze_trends"})
        await event_handler({"event_type": "node.completed", "node_id": "analyze_trends", "duration_seconds": 2.1})
        await event_handler({"event_type": "workflow.completed"})
        
        return run_id, events_received


async def section_4_debug_monitoring(run_id: str):
    """Section 4: Debug information and monitoring."""
    console.print("\n[bold blue]🔍 Section 4: Debug & Monitoring[/bold blue]")
    
    # Simulate debug info (in real implementation, would call workflow.get_debug_info())
    debug_info = {
        "workflow_summary": {
            "total_nodes": 2,
            "completed": 2,
            "failed": 0,
            "total_duration": "2.6s",
            "total_tokens": 2000,
            "total_cost": "$0.08"
        },
        "node_diagnostics": {
            "analyze_trends": {
                "duration": "2.1s",
                "tokens_used": 2000,
                "cache_hit": False,
                "retry_count": 0
            }
        },
        "suggestions": [
            "Consider caching analyze_trends results for repeated queries",
            "load_data processed 100 rows in 0.5s - well optimized"
        ]
    }
    
    console.print("\n[bold]Workflow Summary:[/bold]")
    for key, value in debug_info["workflow_summary"].items():
        console.print(f"  {key}: {value}")
    
    console.print("\n[bold]Performance Insights:[/bold]")
    for suggestion in debug_info["suggestions"]:
        console.print(f"  💡 {suggestion}")


async def section_5_nested_workflows():
    """Section 5: Demonstrate nested workflow composition."""
    console.print("\n[bold blue]🔗 Section 5: Nested Workflow Composition[/bold blue]")
    
    console.print("""
This section shows how to compose workflows:

1. Create reusable workflow components
2. Nest workflows within other workflows
3. Share data between workflow levels
4. Maintain clean abstractions

Example structure:
    
    Main Analysis Workflow
    ├── Data Loading Component
    ├── Quality Check Workflow
    │   ├── Schema Validator
    │   └── Data Profiler
    └── Reporting Workflow
        ├── Chart Generator
        └── PDF Builder
    """)


async def main():
    """Run the comprehensive demo."""
    console.print("""
[bold cyan]🧊 iceOS Comprehensive Demo[/bold cyan]
================================

This demo showcases all major iceOS capabilities in a single workflow.
Each section can be studied independently as an example.
    """)
    
    # Ensure server is running
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/health")
            resp.raise_for_status()
    except Exception:
        console.print("[red]❌ Error: iceOS API server not running![/red]")
        console.print("Please run: [bold]make dev[/bold]")
        return
    
    # Create sample data if missing
    data_path = Path("data/sales_data.csv")
    if not data_path.exists():
        console.print("Creating sample data file...")
        data_path.parent.mkdir(exist_ok=True)
        data_path.write_text("""Date,Product,Category,Quantity,Price,Revenue
2024-01-01,Widget A,Electronics,10,29.99,299.90
2024-01-02,Gadget B,Electronics,5,49.99,249.95
2024-01-03,Tool C,Hardware,15,19.99,299.85
2024-01-04,Widget A,Electronics,8,29.99,239.92
2024-01-05,Service D,Software,1,99.99,99.99
""")
    
    try:
        # Section 1: Build blueprint incrementally
        blueprint_id = await section_1_incremental_construction()
        
        # Section 2: Estimate costs
        cost_estimate = await section_2_cost_estimation(blueprint_id)
        
        # Section 3: Execute with events
        run_id, events = await section_3_event_streaming(blueprint_id)
        
        # Section 4: Debug and monitor
        await section_4_debug_monitoring(run_id)
        
        # Section 5: Show nested workflows
        await section_5_nested_workflows()
        
        console.print("\n[bold green]✨ Demo completed successfully![/bold green]")
        console.print("\nKey takeaways:")
        console.print("• Incremental blueprint construction enables Frosty-style interaction")
        console.print("• Cost estimation helps users make informed decisions")
        console.print("• Event streaming enables real-time canvas updates")
        console.print("• Debug tools provide transparency for troubleshooting")
        console.print("• Nested workflows enable clean composition")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise


if __name__ == "__main__":
    # Check for rich library
    try:
        import rich
    except ImportError:
        print("Please install rich: pip install rich")
        exit(1)
    
    asyncio.run(main()) 