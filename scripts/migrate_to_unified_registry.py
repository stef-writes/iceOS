#!/usr/bin/env python3
"""Migrate from old registries to unified registry."""
import re
from pathlib import Path

REPLACEMENTS = [
    # Tool registrations
    (r'from ice_sdk\.registry\.tool import global_tool_registry', 
     'from ice_sdk.unified_registry import registry'),
    (r'global_tool_registry\.register\("([^"]+)", ([^)]+)\(\)\)',
     r'registry.register_instance(NodeType.TOOL, "\1", \2())'),
    
    # Operator registrations
    (r'from ice_sdk\.registry\.operator import\s+global_operator_registry',
     'from ice_sdk.unified_registry import registry\nfrom ice_core.models import NodeType'),
    (r'global_operator_registry\.register\(([^)]+)\)',
     r'registry.register_class(NodeType.LLM, \1)'),
    
    # Chain/Unit references (mark as TODO)
    (r'from ice_sdk\.registry\.chain import global_chain_registry',
     '# TODO: Migrate to unified registry\n# from ice_sdk.unified_registry import registry'),
    (r'from ice_sdk\.registry\.unit import.*',
     '# TODO: Migrate to unified registry'),
]

def migrate_file(filepath: Path) -> bool:
    """Migrate a single file."""
    try:
        content = filepath.read_text()
        original = content
        
        for old, new in REPLACEMENTS:
            content = re.sub(old, new, content)
        
        # Add NodeType import if we're using it
        if 'NodeType.TOOL' in content and 'from ice_core.models import NodeType' not in content:
            # Add after first import line
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    lines.insert(i + 1, 'from ice_core.models import NodeType')
                    break
            content = '\n'.join(lines)
        
        if content != original:
            filepath.write_text(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Run migration on entire codebase."""
    src_dir = Path(__file__).parent.parent / "src"
    
    changed_files = []
    
    for filepath in src_dir.rglob("*.py"):
        if migrate_file(filepath):
            changed_files.append(filepath)
    
    print(f"\nMigrated {len(changed_files)} files:")
    for f in sorted(changed_files):
        print(f"  - {f.relative_to(Path(__file__).parent.parent)}")

if __name__ == "__main__":
    main() 