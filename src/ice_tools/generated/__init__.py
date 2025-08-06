"""Package for generated scaffolds."""
from importlib import import_module
import pkgutil as _pkgutil
for _m in _pkgutil.iter_modules(__path__):
    import_module(f"{__name__}.{_m.name}")
