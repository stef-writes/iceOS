from typing import Any


def resolve_nested_path(data: Any, path: str) -> Any:
    """
    Resolve a nested path like 'concepts.0' or 'data.items.1.name' in the data structure.
    Args:
        data: The data structure to traverse
        path: Dot-separated path (supports array indexing with integers)
    Returns:
        The value at the specified path
    Raises:
        KeyError: If the path doesn't exist
        IndexError: If array index is out of bounds
        TypeError: If trying to index a non-indexable type
    """
    if not path:
        return data
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(
                    f"Key '{part}' not found in dict. Available keys: {list(current.keys())}"
                )
            current = current[part]
        elif isinstance(current, (list, tuple)):
            try:
                index = int(part)
                if index < 0 or index >= len(current):
                    raise IndexError(
                        f"Index {index} out of bounds for array of length {len(current)}"
                    )
                current = current[index]
            except ValueError:
                raise TypeError(f"Cannot use non-integer key '{part}' to index array")
        else:
            raise TypeError(f"Cannot access '{part}' on type {type(current)}")
    return current
