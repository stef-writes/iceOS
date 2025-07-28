#!/usr/bin/env python3
"""Analyze codebase dependencies to identify safe-to-remove duplicates.

This script helps identify:
1. Files that are imported vs never imported
2. Duplicate implementations across the codebase
3. Migration paths from old to new components
"""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json

class DependencyAnalyzer:
    def __init__(self, root_path: Path):
        self.root = root_path
        self.imports: Dict[str, Set[str]] = defaultdict(set)  # file -> imported modules
        self.imported_by: Dict[str, Set[str]] = defaultdict(set)  # module -> files that import it
        self.class_definitions: Dict[str, List[str]] = defaultdict(list)  # class -> files defining it
        self.function_definitions: Dict[str, List[str]] = defaultdict(list)  # function -> files defining it
        
    def analyze(self) -> Dict[str, any]:
        """Run complete dependency analysis."""
        print("🔍 Analyzing Python files...")
        self._scan_python_files()
        
        print("\n📊 Analyzing dependencies...")
        never_imported = self._find_never_imported_files()
        duplicates = self._find_duplicate_implementations()
        migration_paths = self._suggest_migration_paths()
        
        return {
            "never_imported": list(never_imported),
            "duplicate_implementations": duplicates,
            "migration_paths": migration_paths,
            "import_graph": {k: list(v) for k, v in self.imported_by.items()},
        }
    
    def _scan_python_files(self):
        """Scan all Python files for imports and definitions."""
        for py_file in self.root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".git", "venv", ".venv"]):
                continue
                
            rel_path = str(py_file.relative_to(self.root))
            
            try:
                with open(py_file, 'r') as f:
                    tree = ast.parse(f.read())
                    
                # Extract imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.imports[rel_path].add(alias.name)
                            self.imported_by[alias.name].add(rel_path)
                            
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module
                            self.imports[rel_path].add(module)
                            self.imported_by[module].add(rel_path)
                            
                            # Track specific imports
                            for alias in node.names:
                                full_name = f"{module}.{alias.name}"
                                self.imported_by[full_name].add(rel_path)
                    
                    # Track class definitions
                    elif isinstance(node, ast.ClassDef):
                        self.class_definitions[node.name].append(rel_path)
                    
                    # Track function definitions
                    elif isinstance(node, ast.FunctionDef):
                        self.function_definitions[node.name].append(rel_path)
                        
            except Exception as e:
                print(f"⚠️  Error parsing {rel_path}: {e}")
    
    def _find_never_imported_files(self) -> Set[str]:
        """Find Python files that are never imported."""
        all_files = set()
        for py_file in self.root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".git", "venv", ".venv", "test_"]):
                continue
            all_files.add(str(py_file.relative_to(self.root)))
        
        # Convert file paths to module names
        imported_files = set()
        for module in self.imported_by:
            # Convert module path to file path
            file_path = module.replace('.', '/') + '.py'
            imported_files.add(file_path)
            
            # Also check if it's a package
            init_path = module.replace('.', '/') + '/__init__.py'
            imported_files.add(init_path)
        
        # Files that exist but are never imported
        never_imported = all_files - imported_files
        
        # Filter out special files
        never_imported = {f for f in never_imported if not (
            f.endswith('__main__.py') or 
            f.endswith('setup.py') or
            'scripts/' in f or
            'tests/' in f or
            'use_cases/' in f and 'run_' in f  # Runner scripts
        )}
        
        return never_imported
    
    def _find_duplicate_implementations(self) -> Dict[str, List[str]]:
        """Find duplicate class/function implementations."""
        duplicates = {}
        
        # Check for duplicate classes
        for class_name, files in self.class_definitions.items():
            if len(files) > 1:
                duplicates[f"class:{class_name}"] = files
        
        # Check for specific known duplicates
        known_duplicates = [
            ("AgentNode", ["orchestrator/agent", "orchestrator/nodes/agent"]),
            ("CodeNode", ["orchestrator/nodes/code", "core/models/node_models"]),
            ("registry", ["core/registry", "core/unified_registry"]),
        ]
        
        for name, patterns in known_duplicates:
            matching_files = []
            for f in self.class_definitions.get(name, []) + self.function_definitions.get(name, []):
                if any(p in f for p in patterns):
                    matching_files.append(f)
            if len(matching_files) > 1:
                duplicates[f"known:{name}"] = matching_files
        
        return duplicates
    
    def _suggest_migration_paths(self) -> List[Dict[str, str]]:
        """Suggest migration paths from old to new components."""
        migrations = []
        
        # Known migrations
        migration_map = [
            {
                "old": "src/ice_orchestrator/nodes/agent.py",
                "new": "src/ice_orchestrator/execution/executors/unified.py",
                "function": "agent_executor",
                "reason": "Individual node files consolidated into unified executor"
            },
            {
                "old": "src/ice_orchestrator/nodes/code.py", 
                "new": "src/ice_orchestrator/execution/executors/unified.py",
                "function": "code_executor",
                "reason": "Individual node files consolidated into unified executor"
            },
            {
                "old": "src/ice_core/registry.py",
                "new": "src/ice_core/unified_registry.py",
                "function": "Registry class",
                "reason": "Old registry replaced with unified registry"
            },
            {
                "old": "src/ice_sdk/agents/",
                "new": "src/ice_orchestrator/agent/",
                "function": "Agent implementations",
                "reason": "Agent logic moved to orchestrator layer"
            },
        ]
        
        for m in migration_map:
            if Path(self.root / m["old"]).exists():
                migrations.append(m)
        
        return migrations


def main():
    """Run dependency analysis and generate report."""
    root = Path(__file__).parent.parent
    analyzer = DependencyAnalyzer(root)
    
    print(f"🏗️  Analyzing iceOS codebase at: {root}")
    results = analyzer.analyze()
    
    # Save results
    output_file = root / "dependency_analysis_report.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n📋 Summary:")
    print(f"- Never imported files: {len(results['never_imported'])}")
    print(f"- Duplicate implementations: {len(results['duplicate_implementations'])}")
    print(f"- Suggested migrations: {len(results['migration_paths'])}")
    
    # Show top never-imported files
    if results['never_imported']:
        print("\n🚫 Never imported files (top 10):")
        for f in sorted(results['never_imported'])[:10]:
            print(f"  - {f}")
    
    # Show duplicates
    if results['duplicate_implementations']:
        print("\n♻️  Duplicate implementations:")
        for name, files in results['duplicate_implementations'].items():
            print(f"  - {name}:")
            for f in files:
                print(f"    • {f}")
    
    # Show migration paths
    if results['migration_paths']:
        print("\n🔄 Suggested migrations:")
        for m in results['migration_paths']:
            print(f"  - {m['old']} → {m['new']}")
            print(f"    Reason: {m['reason']}")
    
    print(f"\n✅ Full report saved to: {output_file}")


if __name__ == "__main__":
    main() 