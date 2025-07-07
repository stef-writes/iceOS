from __future__ import annotations

"""High-level Typer sub-applications.

For the first incremental refactor step, we simply re-export the existing
command groups from *ice_cli.commands*.  Follow-up commits can migrate the
actual implementations into dedicated modules under this package while keeping
a stable public import path (``ice_cli.apps.<name>_app``).
"""

from ice_cli.commands.chain import chain_app  # noqa: F401
from ice_cli.commands.connect import connect_app  # noqa: F401
from ice_cli.commands.doctor import doctor_app  # noqa: F401
from ice_cli.commands.flow import flow_app  # noqa: F401
from ice_cli.commands.make import make_app  # noqa: F401
from ice_cli.commands.node import node_app  # noqa: F401
from ice_cli.commands.space import space_app  # noqa: F401
from ice_cli.commands.tool import tool_app  # noqa: F401
from ice_cli.commands.update import update_app  # noqa: F401

__all__ = [
    "chain_app",
    "tool_app",
    "connect_app",
    "node_app",
    "space_app",
    "flow_app",
    "doctor_app",
    "update_app",
    "make_app",
]
