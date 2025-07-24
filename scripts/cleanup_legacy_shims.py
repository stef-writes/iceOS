#!/usr/bin/env python3
"""Remove legacy skill shims and other noisy code."""

import re
from pathlib import Path

def cleanup_skill_shims(file_path: Path) -> bool:
    """Remove legacy skill module shims."""
    content = file_path.read_text()
    original = content
    
    # Pattern to match the legacy skill shim blocks - simpler approach
    patterns = [
        # Match the full shim block
        r"# -+\n# Legacy module alias for backward compatibility \(import \.\.\._skill\)\n# -+\nimport sys as _sys\n_sys\.modules\.setdefault\(__name__\.replace\(\"_tool\", \"_skill\"\), _sys\.modules\[__name__\]\)",
        # Match deprecated alias wrapper
        r"# Deprecated alias wrapper\n+",
        # Match double separator lines
        r"# -+\n# -+\n+"
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, "", content, flags=re.MULTILINE)
    
    # Clean up multiple blank lines
    content = re.sub(r"\n{4,}", "\n\n\n", content)
    content = re.sub(r"\n+$", "\n", content)  # Single newline at EOF
    
    if content != original:
        file_path.write_text(content)
        return True
    return False

def cleanup_registry_warnings(file_path: Path) -> bool:
    """Remove deprecated registry warnings."""
    content = file_path.read_text()
    original = content
    
    # Remove import warnings if not used elsewhere
    if "DeprecationWarning" in content:
        # First check if warnings is used for anything else
        warning_uses = re.findall(r'warnings\.\w+', content)
        deprecation_only = all('warn' in use for use in warning_uses)
        
        if deprecation_only:
            # Remove the import
            content = re.sub(r'^import warnings\n', '', content, flags=re.MULTILINE)
    
    # Pattern to match warning blocks  
    patterns = [
        r'# Shim warning\nwarnings\.warn\([^)]+DeprecationWarning[^)]+\)',
        r'# Shim\nimport sys as _sys\n_sys\.modules\.setdefault[^\n]+\n\nwarnings\.warn\([^)]+DeprecationWarning[^)]+\)',
        r'warnings\.warn\(\s*["\'].*?DeprecationWarning.*?\n\s*stacklevel=\d+,?\s*\n\)',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE)
    
    # Clean up multiple blank lines
    content = re.sub(r"\n{4,}", "\n\n\n", content)
    content = re.sub(r"\n+$", "\n", content)  
    
    if content != original:
        file_path.write_text(content)
        return True
    return False

def cleanup_noisy_comments(file_path: Path) -> bool:
    """Remove overly verbose or noisy comments."""
    content = file_path.read_text()
    original = content
    
    # Remove excessive dashes in comments
    content = re.sub(r'# -{70,}\n', '# ' + '-' * 40 + '\n', content)
    
    # Clean up multiple blank lines
    content = re.sub(r"\n{4,}", "\n\n\n", content)
    
    if content != original:
        file_path.write_text(content)
        return True
    return False

def main():
    """Clean up legacy code."""
    src_dir = Path("src")
    
    cleaned_count = 0
    
    # Clean up skill shims in tools
    for tool_file in src_dir.glob("ice_sdk/tools/**/*.py"):
        if cleanup_skill_shims(tool_file):
            print(f"Cleaned skill shims from: {tool_file}")
            cleaned_count += 1
    
    # Clean up registry warnings
    for registry_file in src_dir.glob("ice_sdk/registry/*.py"):
        if cleanup_registry_warnings(registry_file):
            print(f"Cleaned warnings from: {registry_file}")
            cleaned_count += 1
    
    # Clean up noisy comments everywhere
    for py_file in src_dir.glob("ice_sdk/**/*.py"):
        if cleanup_noisy_comments(py_file):
            print(f"Cleaned comments in: {py_file}")
            cleaned_count += 1
    
    print(f"\nTotal files cleaned: {cleaned_count}")

if __name__ == "__main__":
    main() 