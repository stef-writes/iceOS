#!/usr/bin/env python3
"""Verify that potentially dead code in workflow.py is truly unused.

This script performs multiple checks:
1. Direct imports/calls via AST
2. String-based references (getattr, configs, etc.)
3. Test file usage
4. Protocol/interface requirements
5. Dynamic imports or reflection
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List


class DeadCodeVerifier:
    def __init__(self, root_path: Path):
        self.root = root_path
        self.dead_candidates = {
            # Dead imports
            "ice_orchestrator.api_helpers": {
                "type": "module",
                "items": ["WorkflowSuggestions"]
            },
            "ice_orchestrator.debug": {
                "type": "module", 
                "items": ["WorkflowDebugger"]
            },
            # Potentially dead methods
            "get_execution_state": {
                "type": "method",
                "class": "Workflow"
            },
            "_agent_cache": {
                "type": "attribute",
                "class": "Workflow"
            }
        }
        
        self.results: Dict[str, Dict[str, List[str]]] = {}
        
    def verify_all(self) -> Dict[str, any]:
        """Run all verification checks."""
        print("🔍 Starting dead code verification...")
        
        # Check 1: Direct AST references
        print("\n1️⃣ Checking direct code references...")
        self._check_ast_references()
        
        # Check 2: String-based references
        print("\n2️⃣ Checking string-based references...")
        self._check_string_references()
        
        # Check 3: Test files
        print("\n3️⃣ Checking test files...")
        self._check_test_usage()
        
        # Check 4: Config/JSON files
        print("\n4️⃣ Checking config and JSON files...")
        self._check_config_references()
        
        # Check 5: Protocol requirements
        print("\n5️⃣ Checking protocol/interface requirements...")
        self._check_protocol_requirements()
        
        # Check 6: Dynamic imports
        print("\n6️⃣ Checking dynamic imports...")
        self._check_dynamic_imports()
        
        return self.results
    
    def _check_ast_references(self):
        """Check for direct code references using AST."""
        for py_file in self.root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".git", "venv", "_archive"]):
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                # Check imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            full_import = f"{module}.{alias.name}" if module else alias.name
                            
                            # Check if this imports our dead candidates
                            for candidate, info in self.dead_candidates.items():
                                if info["type"] == "module" and candidate in full_import:
                                    self._record_usage(candidate, str(py_file), f"Import: {full_import}")
                                    
                    # Check method calls
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute):
                            method_name = node.func.attr
                            if method_name in self.dead_candidates:
                                self._record_usage(method_name, str(py_file), f"Method call: {method_name}()")
                                
                    # Check attribute access
                    elif isinstance(node, ast.Attribute):
                        attr_name = node.attr
                        if attr_name == "_agent_cache":
                            self._record_usage(attr_name, str(py_file), f"Attribute access: {attr_name}")
                            
            except Exception:
                pass  # Skip files we can't parse
    
    def _check_string_references(self):
        """Check for string-based references (getattr, dict keys, etc)."""
        patterns = {
            "get_execution_state": [
                r'getattr\([^,]+,\s*["\']get_execution_state["\']',
                r'["\']get_execution_state["\']',
                r'hasattr\([^,]+,\s*["\']get_execution_state["\']'
            ],
            "_agent_cache": [
                r'["\']_agent_cache["\']',
                r'getattr\([^,]+,\s*["\']_agent_cache["\']'
            ],
            "api_helpers": [
                r'["\']api_helpers["\']',
                r'["\']ice_orchestrator\.api_helpers["\']'
            ],
            "WorkflowSuggestions": [
                r'["\']WorkflowSuggestions["\']'
            ],
            "WorkflowDebugger": [
                r'["\']WorkflowDebugger["\']'
            ]
        }
        
        for py_file in self.root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".git", "venv", "_archive"]):
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    
                for candidate, regexes in patterns.items():
                    for pattern in regexes:
                        matches = re.findall(pattern, content)
                        if matches:
                            self._record_usage(candidate, str(py_file), f"String ref: {matches[0][:50]}...")
                            
            except Exception:
                pass
    
    def _check_test_usage(self):
        """Specifically check test files for usage."""
        test_dirs = ["tests/", "test_"]
        
        for test_dir in test_dirs:
            test_path = self.root / test_dir
            if test_path.exists():
                for test_file in test_path.rglob("*.py"):
                    try:
                        with open(test_file, 'r') as f:
                            content = f.read()
                            
                        # Check for mock/patch references
                        if "get_execution_state" in content:
                            self._record_usage("get_execution_state", str(test_file), "Test reference")
                        if "_agent_cache" in content:
                            self._record_usage("_agent_cache", str(test_file), "Test reference")
                        if "WorkflowSuggestions" in content:
                            self._record_usage("WorkflowSuggestions", str(test_file), "Test reference")
                        if "WorkflowDebugger" in content:
                            self._record_usage("WorkflowDebugger", str(test_file), "Test reference")
                            
                    except Exception:
                        pass
    
    def _check_config_references(self):
        """Check JSON/YAML config files."""
        for config_file in self.root.rglob("*.json"):
            if any(skip in str(config_file) for skip in ["__pycache__", ".git", "node_modules", "_archive"]):
                continue
                
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    content = json.dumps(data)
                    
                for candidate in self.dead_candidates:
                    if candidate in content:
                        self._record_usage(candidate, str(config_file), "Config reference")
                        
            except Exception:
                pass
    
    def _check_protocol_requirements(self):
        """Check if methods are required by protocols/interfaces."""
        # Check BaseWorkflow to see if get_execution_state is required
        base_workflow = self.root / "src/ice_orchestrator/base_workflow.py"
        if base_workflow.exists():
            with open(base_workflow, 'r') as f:
                content = f.read()
                if "get_execution_state" in content and "@abstractmethod" in content:
                    self._record_usage("get_execution_state", str(base_workflow), "Protocol requirement")
    
    def _check_dynamic_imports(self):
        """Check for dynamic imports using importlib."""
        patterns = [
            r'importlib\.import_module\(["\']([^"\']+)["\']',
            r'__import__\(["\']([^"\']+)["\']'
        ]
        
        for py_file in self.root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".git", "venv", "_archive"]):
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if "api_helpers" in match or "debug" in match:
                            self._record_usage(match, str(py_file), f"Dynamic import: {match}")
                            
            except Exception:
                pass
    
    def _record_usage(self, item: str, location: str, context: str):
        """Record a usage of a potentially dead item."""
        if item not in self.results:
            self.results[item] = {"usages": []}
        
        self.results[item]["usages"].append({
            "file": location,
            "context": context
        })
    
    def print_report(self):
        """Print a formatted report of findings."""
        print("\n" + "="*70)
        print("📊 DEAD CODE VERIFICATION REPORT")
        print("="*70)
        
        truly_dead = []
        possibly_used = []
        
        for candidate in self.dead_candidates:
            if candidate in self.results and self.results[candidate]["usages"]:
                possibly_used.append(candidate)
            else:
                truly_dead.append(candidate)
        
        if truly_dead:
            print("\n✅ CONFIRMED DEAD CODE (safe to remove):")
            for item in truly_dead:
                print(f"  - {item}")
                info = self.dead_candidates[item]
                if info["type"] == "module":
                    print("    Type: Module import")
                    if "items" in info:
                        print(f"    Items: {', '.join(info['items'])}")
                else:
                    print(f"    Type: {info['type']}")
        
        if possibly_used:
            print("\n⚠️  POSSIBLY USED (needs manual verification):")
            for item in possibly_used:
                print(f"\n  - {item}")
                for usage in self.results[item]["usages"][:5]:  # Show first 5
                    print(f"    📍 {usage['file']}")
                    print(f"       Context: {usage['context']}")
                if len(self.results[item]["usages"]) > 5:
                    print(f"    ... and {len(self.results[item]['usages']) - 5} more")
        
        print("\n💡 RECOMMENDATIONS:")
        if truly_dead:
            print("  1. The confirmed dead code can be safely removed")
            print("  2. Consider removing thin wrapper methods that just delegate")
            print("  3. Update backwards compatibility code (Chain* → Workflow*)")
        else:
            print("  - All potentially dead code has references that need manual review")
        
        # Save detailed report
        report_path = self.root / "dead_code_verification_report.json"
        with open(report_path, 'w') as f:
            json.dump({
                "dead_candidates": self.dead_candidates,
                "results": self.results,
                "truly_dead": truly_dead,
                "possibly_used": possibly_used
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_path}")


def main():
    """Run dead code verification."""
    root = Path(__file__).parent.parent
    verifier = DeadCodeVerifier(root)
    
    results = verifier.verify_all()
    verifier.print_report()


if __name__ == "__main__":
    main() 