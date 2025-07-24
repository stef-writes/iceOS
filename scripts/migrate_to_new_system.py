#!/usr/bin/env python3
"""Migrate codebase to new unified node system."""
import os
import re
from pathlib import Path

# Define all replacements
REPLACEMENTS = [
    # Core class renames
    (r'\bSkillBase\b', 'ToolBase'),
    (r'\bSkillRegistry\b', 'ToolRegistry'),
    (r'\bglobal_skill_registry\b', 'global_tool_registry'),
    
    # Import updates
    (r'from ice_sdk\.skills', 'from ice_sdk.tools'),
    (r'from ice_sdk\.tools\.base import ToolBase, SkillBase', 'from ice_sdk.tools.base import ToolBase'),
    (r'from ice_sdk\.skills\.base import SkillBase', 'from ice_sdk.tools.base import ToolBase'),
    (r'from \.\.base import SkillBase', 'from ..base import ToolBase'),
    (r'from \.base import SkillBase', 'from .base import ToolBase'),
    
    # Node type updates
    (r'"skill"', '"tool"'),
    (r"'skill'", "'tool'"),
    (r'NodeType\.SKILL', 'NodeType.TOOL'),
    
    # Variable/parameter names
    (r'\bskill:', 'tool:'),
    (r'\bskill\s*=', 'tool ='),
    (r'_skills\b', '_tools'),
    (r'\.skills\b', '.tools'),
    (r'\[skill\]', '[tool]'),
    (r'"skill":', '"tool":'),
    (r"'skill':", "'tool':"),
    
    # Comments and docstrings
    (r'\*Skill\*', '*Tool*'),
    (r'\*skill\*', '*tool*'),
    (r'Skill\s+', 'Tool '),
    (r'skill\s+', 'tool '),
]

def migrate_file(filepath: Path) -> bool:
    """Migrate a single Python file. Returns True if changes were made."""
    try:
        content = filepath.read_text()
        original = content
        
        # Apply all replacements
        for old, new in REPLACEMENTS:
            content = re.sub(old, new, content)
        
        # Special case: Remove duplicate ToolBase imports
        content = re.sub(r'from ice_sdk\.tools\.base import ToolBase, ToolBase', 
                        'from ice_sdk.tools.base import ToolBase', content)
        
        # Write back if changed
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
    tests_dir = Path(__file__).parent.parent / "tests"
    
    changed_files = []
    
    for directory in [src_dir, tests_dir]:
        for filepath in directory.rglob("*.py"):
            if migrate_file(filepath):
                changed_files.append(filepath)
    
    print(f"\nMigrated {len(changed_files)} files:")
    for f in sorted(changed_files):
        print(f"  - {f.relative_to(Path(__file__).parent.parent)}")
    
    # Remove the SkillBase alias from tools/base.py
    base_file = src_dir / "ice_sdk/tools/base.py"
    if base_file.exists():
        content = base_file.read_text()
        # Remove the alias lines
        content = re.sub(r'class SkillBase\(ToolBase\):.*?\n.*?\n.*?\n', '', content, flags=re.DOTALL)
        content = re.sub(r'SkillBase = ToolBase.*?\n', '', content)
        base_file.write_text(content)
        print(f"\nRemoved SkillBase alias from {base_file.relative_to(Path(__file__).parent.parent)}")

if __name__ == "__main__":
    main() 