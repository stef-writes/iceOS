"""Stub module for wasmtime to satisfy imports in tests."""

class Store:  # noqa: D401 – placeholder
    pass

class Module:  # noqa: D401
    def __init__(self, *args, **kwargs):
        pass

class Instance:  # noqa: D401
    def __init__(self, *args, **kwargs):
        pass

__all__ = ["Store", "Module", "Instance"]