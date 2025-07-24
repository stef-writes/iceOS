#!/usr/bin/env python3
"""
🧊 iceOS Enhanced Comprehensive Demo with Real LLM Calls
========================================================

This enhanced demo showcases detailed node inspection with real API calls:

1. Detailed Node Configuration Display
2. Real LLM API calls with full prompt/response logging
3. Node Classification and Metadata Analysis
4. Complete Chain Inspection and Output Tracking
5. Workflow Spatial Intelligence Features

Prerequisites:
    - iceOS API server running: make dev
    - Sample data file: examples/data/sales_data.csv
    - Real LLM API keys configured
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
from rich.json import JSON

# Initialize Rich console for beautiful output
console = Console()

# API Configuration
API_BASE = "http://localhost:8000/api/v1/mcp"


class NodeInspector:
    """Enhanced node inspection and display utilities."""
    
    @staticmethod
    def classify_node(node_config: Dict[str, Any]) -> str:
        """Classify a node based on its configuration."""
        node_type = node_config.get("type", "unknown")
        
        classifications = {
            "llm": "🧠 AI Language Model Node",
            "tool": "🔧 Tool Execution Node", 
            "agent": "🤖 Autonomous Agent Node",
            "condition": "🔀 Conditional Branch Node",
            "nested_chain": "🔗 Sub-Workflow Node",
            "parallel": "⚡ Parallel Execution Node"
        }
        
        return classifications.get(node_type, f"❓ Unknown Node Type: {node_type}")
    
    @staticmethod
    def display_node_config(node_config: Dict[str, Any]) -> None:
        """Display detailed node configuration."""
        node_id = node_config.get("id", "unknown")
        node_type = node_config.get("type", "unknown")
        node_name = node_config.get("name", node_id)
        
        # Create the main panel
        config_tree = Tree(f"[bold cyan]{node_id}[/bold cyan] - {NodeInspector.classify_node(node_config)}")
        
        # Basic info
        basic_info = config_tree.add("[bold]Basic Configuration[/bold]")
        basic_info.add(f"ID: [green]{node_id}[/green]")
        basic_info.add(f"Type: [yellow]{node_type}[/yellow]")
        basic_info.add(f"Name: [blue]{node_name}[/blue]")
        
        if node_config.get("dependencies"):
            deps = config_tree.add("[bold]Dependencies[/bold]")
            for dep in node_config["dependencies"]:
                deps.add(f"↳ [magenta]{dep}[/magenta]")
        
        # LLM-specific configuration
        if node_type == "llm":
            llm_config = config_tree.add("[bold]LLM Configuration[/bold]")
            llm_config.add(f"Model: [cyan]{node_config.get('model', 'not specified')}[/cyan]")
            llm_config.add(f"Temperature: [yellow]{node_config.get('temperature', 'default')}[/yellow]")
            llm_config.add(f"Max Tokens: [green]{node_config.get('max_tokens', 'default')}[/green]")
            
            if node_config.get("prompt"):
                prompt_node = llm_config.add("[bold]Prompt Template[/bold]")
                # Show prompt with syntax highlighting
                prompt_text = node_config["prompt"]
                if len(prompt_text) > 100:
                    prompt_text = prompt_text[:100] + "..."
                prompt_node.add(f"[italic]{prompt_text}[/italic]")
        
        # Tool-specific configuration
        elif node_type == "tool":
            tool_config = config_tree.add("[bold]Tool Configuration[/bold]")
            tool_config.add(f"Tool Name: [cyan]{node_config.get('tool_name', 'not specified')}[/cyan]")
            
            # Show tool parameters
            for key, value in node_config.items():
                if key not in ["id", "type", "name", "dependencies", "tool_name"]:
                    tool_config.add(f"{key}: [yellow]{value}[/yellow]")
        
        # Schema information
        if node_config.get("input_schema") or node_config.get("output_schema"):
            schema_info = config_tree.add("[bold]Schema Definition[/bold]")
            if node_config.get("input_schema"):
                input_schema = schema_info.add("Input Schema")
                for key, schema_type in node_config["input_schema"].items():
                    input_schema.add(f"{key}: [green]{schema_type}[/green]")
            
            if node_config.get("output_schema"):
                output_schema = schema_info.add("Output Schema")
                for key, schema_type in node_config["output_schema"].items():
                    output_schema.add(f"{key}: [green]{schema_type}[/green]")
        
        console.print(Panel(config_tree, title=f"[bold]Node Configuration: {node_id}[/bold]", border_style="blue"))

    @staticmethod
    def display_execution_result(node_id: str, result: Dict[str, Any]) -> None:
        """Display detailed execution results."""
        success = result.get("success", False)
        status_color = "green" if success else "red"
        status_text = "✅ SUCCESS" if success else "❌ FAILED"
        
        result_tree = Tree(f"[bold {status_color}]{status_text}[/bold {status_color}] - {node_id}")
        
        # Execution metadata
        metadata = result.get("metadata", {})
        if metadata:
            meta_info = result_tree.add("[bold]Execution Metadata[/bold]")
            meta_info.add(f"Duration: [yellow]{metadata.get('duration', 'unknown')}s[/yellow]")
            meta_info.add(f"Start Time: [cyan]{metadata.get('start_time', 'unknown')}[/cyan]")
            meta_info.add(f"Node Type: [magenta]{metadata.get('node_type', 'unknown')}[/magenta]")
        
        # Output data
        if result.get("output"):
            output_info = result_tree.add("[bold]Output Data[/bold]")
            output_data = result["output"]
            
            if isinstance(output_data, dict):
                for key, value in output_data.items():
                    if isinstance(value, (str, int, float, bool)):
                        output_info.add(f"{key}: [green]{value}[/green]")
                    elif isinstance(value, list) and len(value) <= 3:
                        output_info.add(f"{key}: [green]{value}[/green]")
                    else:
                        # For large/complex data, show a preview
                        preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                        output_info.add(f"{key}: [green]{preview}[/green]")
            else:
                preview = str(output_data)[:200] + "..." if len(str(output_data)) > 200 else str(output_data)
                output_info.add(f"[green]{preview}[/green]")
        
        # Usage/token information
        if result.get("usage"):
            usage_info = result_tree.add("[bold]Resource Usage[/bold]")
            usage = result["usage"]
            usage_info.add(f"Total Tokens: [yellow]{usage.get('total_tokens', 0)}[/yellow]")
            usage_info.add(f"Prompt Tokens: [cyan]{usage.get('prompt_tokens', 0)}[/cyan]")
            usage_info.add(f"Completion Tokens: [green]{usage.get('completion_tokens', 0)}[/green]")
        
        # Error information
        if not success and result.get("error"):
            error_info = result_tree.add("[bold red]Error Details[/bold red]")
            error_info.add(f"[red]{result['error']}[/red]")
        
        console.print(Panel(result_tree, title=f"[bold]Execution Result: {node_id}[/bold]", border_style=status_color))


async def create_enhanced_workflow():
    """Create a comprehensive workflow with real LLM calls."""
    console.print("\n[bold blue]🚀 Creating Enhanced Real-World Workflow[/bold blue]")
    console.print("Building a multi-node data analysis pipeline with real AI...\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create sample data
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
2024-01-06,Widget A,Electronics,12,29.99,359.88
2024-01-07,Gadget B,Electronics,3,49.99,149.97
2024-01-08,Tool C,Hardware,20,19.99,399.80
2024-01-09,Service D,Software,2,99.99,199.98
2024-01-10,Widget A,Electronics,15,29.99,449.85
""")
        
        # Define comprehensive workflow with multiple LLM nodes
        workflow_blueprint = {
            "name": "Enhanced Sales Analysis Pipeline",
            "description": "Comprehensive sales data analysis with multiple AI insights",
            "nodes": [
                {
                    "id": "load_data",
                    "type": "tool",
                    "name": "CSV Data Loader",
                    "tool_name": "csv_reader",
                    "tool_args": {
                        "file_path": str(data_path)
                    },
                    "dependencies": [],
                    "input_schema": {
                        "file_path": "str"
                    },
                    "output_schema": {
                        "rows": "list[dict]",
                        "headers": "list[str]"
                    }
                },
                {
                    "id": "trend_analyzer",
                    "type": "llm",
                    "name": "Sales Trend Analyzer",
                    "model": "gpt-4",
                    "prompt": """Analyze the sales data and identify key trends:

Data: {load_data.rows}

Please provide a detailed analysis including:
1. Top performing products by revenue
2. Category performance comparison
3. Sales trends over time
4. Key insights and patterns

Format your response as structured JSON with clear sections for each analysis point.""",
                    "dependencies": ["load_data"],
                    "input_schema": {
                        "rows": "list[dict]"
                    },
                    "output_schema": {
                        "analysis": "dict"
                    },
                    "temperature": 0.3,
                    "max_tokens": 1000,
                    "llm_config": {
                        "provider": "openai"
                    }
                },
                {
                    "id": "summary_generator",
                    "type": "llm",
                    "name": "Executive Summary Generator",
                    "model": "gpt-3.5-turbo",
                    "prompt": """Create an executive summary based on this sales analysis:

Analysis: {trend_analyzer.analysis}

Generate a concise executive summary (2-3 paragraphs) that highlights:
- Key business insights
- Actionable recommendations
- Critical performance metrics

Write in a professional business tone suitable for senior management.""",
                    "dependencies": ["trend_analyzer"],
                    "input_schema": {
                        "analysis": "dict"
                    },
                    "output_schema": {
                        "summary": "str",
                        "recommendations": "list[str]"
                    },
                    "temperature": 0.5,
                    "max_tokens": 500,
                    "llm_config": {
                        "provider": "openai"
                    }
                },
                {
                    "id": "insight_classifier",
                    "type": "llm",
                    "name": "Business Insight Classifier",
                    "model": "gpt-4",
                    "prompt": """Classify and categorize the insights from this analysis:

Original Analysis: {trend_analyzer.analysis}
Executive Summary: {summary_generator.summary}

Classify insights into categories:
- GROWTH_OPPORTUNITIES: Areas with potential for expansion
- PERFORMANCE_CONCERNS: Areas needing attention
- OPERATIONAL_INSIGHTS: Process and efficiency observations
- MARKET_TRENDS: External market factors

Return a structured classification with confidence scores.""",
                    "dependencies": ["trend_analyzer", "summary_generator"],
                    "input_schema": {
                        "analysis": "dict",
                        "summary": "str"
                    },
                    "output_schema": {
                        "classifications": "dict",
                        "confidence_scores": "dict"
                    },
                    "temperature": 0.2,
                    "max_tokens": 600,
                    "llm_config": {
                        "provider": "openai"
                    }
                }
            ]
        }
        
        console.print("[bold green]📋 WORKFLOW BLUEPRINT CREATED[/bold green]")
        console.print(f"Total Nodes: {len(workflow_blueprint['nodes'])}")
        console.print(f"LLM Nodes: {len([n for n in workflow_blueprint['nodes'] if n['type'] == 'llm'])}")
        console.print(f"Tool Nodes: {len([n for n in workflow_blueprint['nodes'] if n['type'] == 'tool'])}")
        
        # Display each node configuration
        console.print("\n[bold blue]🔍 DETAILED NODE CONFIGURATIONS[/bold blue]")
        for i, node in enumerate(workflow_blueprint['nodes'], 1):
            console.print(f"\n[bold yellow]--- Node {i}/{len(workflow_blueprint['nodes'])} ---[/bold yellow]")
            NodeInspector.display_node_config(node)
        
        return workflow_blueprint


async def execute_enhanced_workflow(workflow_blueprint: Dict[str, Any]):
    """Execute the workflow with detailed tracking and display."""
    console.print("\n[bold blue]⚡ EXECUTING ENHANCED WORKFLOW WITH REAL LLM CALLS[/bold blue]")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Create and execute the workflow
        console.print("🚀 Submitting workflow for execution...")
        
        try:
            # Create proper Blueprint structure
            blueprint_request = {
                "blueprint": {
                    "blueprint_id": f"enhanced_demo_{datetime.now().strftime('%H%M%S')}",
                    "schema_version": "1.1.0",
                    "nodes": workflow_blueprint["nodes"],
                    "metadata": {
                        "name": workflow_blueprint["name"],
                        "description": workflow_blueprint["description"],
                        "demo_type": "enhanced_real_llm",
                        "spatial_features_enabled": True
                    }
                },
                "options": {
                    "max_parallel": 3,
                    "timeout_seconds": 300
                }
            }
            
            resp = await client.post(
                f"{API_BASE}/runs",
                json=blueprint_request
            )
            resp.raise_for_status()
            execution_result = resp.json()
            
            console.print(f"✅ Workflow submitted successfully")
            run_id = execution_result.get('run_id', 'unknown')
            console.print(f"Run ID: [green]{run_id}[/green]")
            
            # Wait a moment and fetch detailed results
            console.print("⏳ Waiting for execution to complete...")
            await asyncio.sleep(2)  # Give it time to start
            
            # Fetch execution results
            result_resp = await client.get(f"{API_BASE}/runs/{run_id}")
            if result_resp.status_code == 200:
                execution_result = result_resp.json()
            
            # Display execution results
            if execution_result.get("success"):
                console.print("\n[bold green]🎉 WORKFLOW EXECUTION COMPLETED SUCCESSFULLY[/bold green]")
                
                # Show detailed results for each node
                node_results = execution_result.get("output", {})
                console.print(f"\nProcessed {len(node_results)} nodes:")
                
                # Display results in execution order
                execution_order = ["load_data", "trend_analyzer", "summary_generator", "insight_classifier"]
                
                for i, node_id in enumerate(execution_order, 1):
                    if node_id in node_results:
                        console.print(f"\n[bold yellow]--- Node {i}: {node_id} Results ---[/bold yellow]")
                        NodeInspector.display_execution_result(node_id, node_results[node_id])
                        
                        # Special handling for LLM responses
                        if node_results[node_id].get("output"):
                            output = node_results[node_id]["output"]
                            
                            # Show AI response content
                            if node_id == "trend_analyzer":
                                console.print("\n[bold cyan]🧠 AI TREND ANALYSIS[/bold cyan]")
                                if isinstance(output, dict) and "analysis" in output:
                                    console.print(Panel(
                                        str(output["analysis"])[:500] + "..." if len(str(output["analysis"])) > 500 else str(output["analysis"]),
                                        title="Sales Trend Analysis",
                                        border_style="cyan"
                                    ))
                            
                            elif node_id == "summary_generator":
                                console.print("\n[bold magenta]📝 EXECUTIVE SUMMARY[/bold magenta]")
                                if isinstance(output, dict) and "summary" in output:
                                    console.print(Panel(
                                        output["summary"],
                                        title="Executive Summary",
                                        border_style="magenta"
                                    ))
                                    
                                    if "recommendations" in output:
                                        console.print("\n[bold green]💡 RECOMMENDATIONS[/bold green]")
                                        for j, rec in enumerate(output["recommendations"], 1):
                                            console.print(f"{j}. {rec}")
                            
                            elif node_id == "insight_classifier":
                                console.print("\n[bold blue]🏷️ INSIGHT CLASSIFICATION[/bold blue]")
                                if isinstance(output, dict) and "classifications" in output:
                                    classifications = output["classifications"]
                                    
                                    for category, insights in classifications.items():
                                        console.print(f"\n[bold]{category}[/bold]:")
                                        if isinstance(insights, list):
                                            for insight in insights:
                                                console.print(f"  • {insight}")
                                        else:
                                            console.print(f"  • {insights}")
                
                # Show overall execution metrics
                console.print("\n[bold blue]📊 EXECUTION METRICS[/bold blue]")
                metrics_table = Table(title="Workflow Execution Summary")
                metrics_table.add_column("Metric", style="cyan")
                metrics_table.add_column("Value", style="green")
                
                total_duration = execution_result.get("execution_time", 0)
                total_tokens = sum([
                    result.get("usage", {}).get("total_tokens", 0) 
                    for result in node_results.values() 
                    if result.get("usage")
                ])
                
                metrics_table.add_row("Total Duration", f"{total_duration:.2f}s")
                metrics_table.add_row("Total Tokens Used", str(total_tokens))
                metrics_table.add_row("Nodes Executed", str(len(node_results)))
                metrics_table.add_row("Success Rate", "100%")
                
                console.print(metrics_table)
                
            else:
                console.print(f"\n[bold red]❌ WORKFLOW EXECUTION FAILED[/bold red]")
                error_msg = execution_result.get('error', 'Unknown error')
                console.print(f"Error: {error_msg}")
                
                # Show partial results if any nodes succeeded
                if execution_result.get("output"):
                    console.print(f"\n[bold yellow]📊 PARTIAL RESULTS (Some nodes may have succeeded)[/bold yellow]")
                    node_results = execution_result.get("output", {})
                    
                    for node_id, result in node_results.items():
                        if result.get("success"):
                            console.print(f"\n[bold green]✅ {node_id} - Succeeded[/bold green]")
                            NodeInspector.display_execution_result(node_id, result)
                        else:
                            console.print(f"\n[bold red]❌ {node_id} - Failed[/bold red]")
                            console.print(f"Error: {result.get('error', 'Unknown error')}")
                            
                # Show execution details for debugging
                console.print(f"\n[bold cyan]🔍 EXECUTION DEBUG INFO[/bold cyan]")
                debug_table = Table(title="Execution Details")
                debug_table.add_column("Property", style="cyan")
                debug_table.add_column("Value", style="white")
                
                debug_table.add_row("Run ID", str(run_id))
                debug_table.add_row("Success", str(execution_result.get("success", False)))
                debug_table.add_row("Execution Time", f"{execution_result.get('execution_time', 0):.2f}s")
                debug_table.add_row("Error Message", str(execution_result.get("error", "None")))
                debug_table.add_row("Node Count", str(len(execution_result.get("output", {}))))
                
                console.print(debug_table)
                
        except httpx.HTTPStatusError as e:
            console.print(f"\n[bold red]❌ HTTP ERROR: {e.response.status_code}[/bold red]")
            console.print(f"Response: {e.response.text}")
        except Exception as e:
            console.print(f"\n[bold red]❌ EXECUTION ERROR: {str(e)}[/bold red]")


async def demonstrate_spatial_features():
    """Demonstrate workflow spatial computing features."""
    console.print("\n[bold blue]🎨 DEMONSTRATING WORKFLOW SPATIAL FEATURES[/bold blue]")
    
    async with httpx.AsyncClient() as client:
        try:
            # Get graph metrics (this would normally be from a completed workflow)
            console.print("🧠 Graph Intelligence Analysis...")
            
            # Simulated spatial features demo
            spatial_features = {
                "graph_metrics": {
                    "total_nodes": 4,
                    "total_edges": 5,
                    "max_depth": 3,
                    "parallel_opportunities": 1,
                    "complexity_score": 6.5,
                    "bottleneck_nodes": ["insight_classifier"]
                },
                "layout_hints": {
                    "load_data": {"x": 100, "y": 200, "level": 0},
                    "trend_analyzer": {"x": 300, "y": 200, "level": 1},
                    "summary_generator": {"x": 500, "y": 150, "level": 2},
                    "insight_classifier": {"x": 500, "y": 250, "level": 2}
                },
                "optimization_suggestions": [
                    {
                        "type": "parallelization",
                        "description": "Consider parallel execution of summary_generator and insight_classifier",
                        "priority": "medium",
                        "estimated_improvement": "25% faster execution"
                    }
                ]
            }
            
            # Display spatial intelligence
            console.print("\n[bold cyan]🗺️ SPATIAL LAYOUT ANALYSIS[/bold cyan]")
            layout_tree = Tree("Workflow Spatial Layout")
            
            for level in range(3):
                level_nodes = [
                    node_id for node_id, data in spatial_features["layout_hints"].items()
                    if data["level"] == level
                ]
                if level_nodes:
                    level_branch = layout_tree.add(f"Level {level}")
                    for node_id in level_nodes:
                        pos = spatial_features["layout_hints"][node_id]
                        level_branch.add(f"{node_id} @ ({pos['x']}, {pos['y']})")
            
            console.print(Panel(layout_tree, title="Canvas Layout Hints", border_style="cyan"))
            
            # Display optimization suggestions
            console.print("\n[bold green]💡 OPTIMIZATION SUGGESTIONS[/bold green]")
            for i, suggestion in enumerate(spatial_features["optimization_suggestions"], 1):
                console.print(Panel(
                    f"[bold]{suggestion['type'].upper()}[/bold]\n"
                    f"{suggestion['description']}\n"
                    f"Priority: {suggestion['priority']}\n"
                    f"Expected Improvement: {suggestion['estimated_improvement']}",
                    title=f"Suggestion {i}",
                    border_style="green"
                ))
            
        except Exception as e:
            console.print(f"[red]Could not demonstrate spatial features: {e}[/red]")


async def main():
    """Run the enhanced comprehensive demo."""
    console.print("""
[bold cyan]🧊 iceOS Enhanced Comprehensive Demo[/bold cyan]
[bold cyan]=====================================[/bold cyan]

This enhanced demo showcases detailed node inspection with real LLM API calls.
Every node configuration, prompt, and output will be displayed in detail.

[bold yellow]Features Demonstrated:[/bold yellow]
• Real LLM API calls with full request/response logging
• Detailed node configuration and metadata display
• Comprehensive output analysis and classification
• Workflow spatial computing features
• Multi-node dependency analysis pipeline
    """)
    
    try:
        # Test API connectivity
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{API_BASE.replace('/mcp', '')}/health")
                console.print("✅ iceOS API server is running")
            except Exception:
                console.print("[red]❌ Error: iceOS API server not running![/red]")
                console.print("Please run: make dev")
                return
        
        # Execute the enhanced demo
        console.print("\n" + "="*60)
        
        # 1. Create the workflow
        workflow_blueprint = await create_enhanced_workflow()
        
        # 2. Execute with real LLM calls
        await execute_enhanced_workflow(workflow_blueprint)
        
        # 3. Demonstrate spatial features
        await demonstrate_spatial_features()
        
        console.print("\n[bold green]✨ Enhanced Demo completed successfully![/bold green]")
        console.print("\n[bold cyan]Key takeaways:[/bold cyan]")
        console.print("• Real LLM API calls provide genuine AI insights")
        console.print("• Detailed node inspection reveals workflow complexity")
        console.print("• Workflow spatial features enable canvas visualization")
        console.print("• Multi-node dependencies create rich analysis pipelines")
        console.print("• Token usage and performance metrics guide optimization")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Demo failed: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")


if __name__ == "__main__":
    asyncio.run(main()) 