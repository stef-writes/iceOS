import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


def get_nested_value(data: Union[Dict[str, Any], List[Any]], key_path: str) -> Any:
    """
    Retrieves a value from a nested dictionary or list using a dot-separated key path.

    Args:
        data: The dictionary or list to traverse.
        key_path: A string representing the path to the desired value,
                  e.g., "level1.level2_list.0.name".

    Returns:
        The value found at the specified path, or None if the path is invalid
        or any intermediate key/index is not found.
    """
    if not key_path:
        return None

    parts = key_path.split(".")
    current_data = data

    for i, part in enumerate(parts):
        if isinstance(current_data, dict):
            if part in current_data:
                current_data = current_data[part]
            else:
                logger.debug(
                    f"Key '{part}' not found in dict at path segment '{'.'.join(parts[:i+1])}'"
                )
                return None
        elif isinstance(current_data, list):
            try:
                index = int(part)
                if 0 <= index < len(current_data):
                    current_data = current_data[index]
                else:
                    logger.debug(
                        f"Index {index} out of bounds for list at path segment '{'.'.join(parts[:i+1])}' (length: {len(current_data)})"
                    )
                    return None
            except ValueError:
                logger.debug(
                    f"Invalid index '{part}' for list at path segment '{'.'.join(parts[:i+1])}'"
                )
                return None
        else:
            # If current_data is not a dict or list, we can't go deeper
            logger.debug(
                f"Cannot traverse further. Path segment '{'.'.join(parts[:i+1])}' leads to a non-collection type: {type(current_data)}"
            )
            return None

    return current_data
