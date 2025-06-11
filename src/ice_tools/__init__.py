"""Side-effecting Tools used by ice-OS.

Public façade so code can simply write::

    from ice_tools import WordCountTool

The concrete implementations live in sub-packages such as
``ice_tools.builtins``.
"""

from ice_tools.builtins.word_count import WordCountTool  # noqa: F401

__all__ = [
    "WordCountTool",
]
