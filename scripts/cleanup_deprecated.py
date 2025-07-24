#!/usr/bin/env python3
"""Remove all deprecated code since we have no users."""
import re
from pathlib import Path

def remove_deprecated_classes(filepath: Path) -> bool:
    """Remove deprecated class definitions and their imports."""
    content = filepath.read_text()
    original = content
    
    # Remove import of deprecated decorator
    content = re.sub(r'from ice_core\.utils\.deprecation import deprecated\n', '', content)
    content = re.sub(r'from \.\.\.utils\.deprecation import deprecated\n', '', content)
    
    # Remove deprecated class definitions (matches @deprecated decorator + class def + pass)
    content = re.sub(r'@deprecated\([^)]+\)\nclass \w+\([^)]+\):[^\n]*\n\s+pass\n', '', content)
    
    # Remove standalone "# Deprecated alias" comments followed by imports
    content = re.sub(r'# Deprecated alias\n', '', content)
    
    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    if content != original:
        filepath.write_text(content)
        return True
    return False

def main():
    """Run cleanup on entire codebase."""
    src_dir = Path(__file__).parent.parent / "src"
    
    changed_files = []
    
    for filepath in src_dir.rglob("*.py"):
        if remove_deprecated_classes(filepath):
            changed_files.append(filepath)
    
    print(f"\nCleaned {len(changed_files)} files:")
    for f in sorted(changed_files):
        print(f"  - {f.relative_to(Path(__file__).parent.parent)}")

if __name__ == "__main__":
    main() 