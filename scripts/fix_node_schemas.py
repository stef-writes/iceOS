#!/usr/bin/env python3
"""Fix schema definitions in node files to use properties instead of class variables."""

import re
from pathlib import Path

def fix_schemas(file_path: Path) -> bool:
    """Convert class variable schemas to properties."""
    content = file_path.read_text()
    original = content
    
    # Pattern to find input_schema and output_schema class variables
    schema_pattern = r'(\s+)(input_schema|output_schema)\s*=\s*({[^}]+})'
    
    def replace_schema(match):
        indent = match.group(1)
        schema_name = match.group(2)
        schema_dict = match.group(3)
        
        return f'''{indent}@property
{indent}def {schema_name}(self) -> Dict[str, Any]:
{indent}    return {schema_dict}'''
    
    content = re.sub(schema_pattern, replace_schema, content, flags=re.MULTILINE | re.DOTALL)
    
    # Add typing import if needed
    if 'Dict[str, Any]' in content and 'from typing import' in content:
        if 'Dict' not in content.split('from typing import')[1].split('\n')[0]:
            content = re.sub(
                r'(from typing import[^)]+)\)',
                r'\1, Dict)',
                content
            )
    
    if content != original:
        file_path.write_text(content)
        return True
    return False

def main():
    """Fix all node files."""
    nodes_dir = Path("src/ice_orchestrator/nodes")
    
    fixed_count = 0
    for node_file in nodes_dir.glob("*.py"):
        if node_file.name == "__init__.py":
            continue
            
        if fix_schemas(node_file):
            print(f"Fixed schemas in: {node_file}")
            fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main() 