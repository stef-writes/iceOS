#!/usr/bin/env python3
"""Remove all deprecated code comprehensively."""
import re
from pathlib import Path

def remove_deprecated_code(filepath: Path) -> bool:
    """Remove deprecated code more aggressively."""
    try:
        content = filepath.read_text()
        original = content
        
        # Remove deprecated decorator lines
        content = re.sub(r'@deprecated\([^)]+\)\n', '', content)
        
        # Remove deprecation shim classes (any class ending with Shim/Skill that just has pass or raises)
        content = re.sub(
            r'class \w+(Shim|Skill)\b[^:]*:\s*(?:# [^\n]*\n)?\s*(?:"""[^"]*"""\n)?\s*(?:def __getattr__[^:]*:[^\n]*\n\s*raise[^\n]*\n|pass\n)',
            '', 
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        
        # Clean up extra blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        if content != original:
            filepath.write_text(content)
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    
    return False

def main():
    """Run cleanup on entire codebase."""
    src_dir = Path(__file__).parent.parent / "src"
    
    changed_files = []
    
    for filepath in src_dir.rglob("*.py"):
        if remove_deprecated_code(filepath):
            changed_files.append(filepath)
    
    print(f"\nCleaned {len(changed_files)} files:")
    for f in sorted(changed_files):
        print(f"  - {f.relative_to(Path(__file__).parent.parent)}")

if __name__ == "__main__":
    main() 