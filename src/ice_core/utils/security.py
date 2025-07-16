"""Security utilities (path sanitisation, etc.)."""

from __future__ import annotations

from pathlib import Path

from ice_core.exceptions import SecurityViolationError

__all__ = ["sanitize_path"]


def sanitize_path(
    user_path: str | Path, *, root: Path | None = None
) -> Path:  # noqa: D401
    root_dir = (root or Path.cwd()).resolve()
    resolved = Path(user_path).expanduser().resolve()
    try:
        resolved.relative_to(root_dir)
    except ValueError as exc:
        raise SecurityViolationError(str(user_path)) from exc
    return resolved
