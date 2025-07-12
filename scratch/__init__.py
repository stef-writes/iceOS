"""Scratch-space for experimental code – excluded from unit tests & builds.

Modules in *scratch* are NOT considered production code. They are ignored by
pytest collection (via *testpaths*) and mypy static analysis (see mypy.ini)
so developers can iterate quickly without impacting CI.
"""

__all__: list[str] = []
