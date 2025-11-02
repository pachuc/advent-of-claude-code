import pkgutil
import importlib

# Make all agents importable from "agents" directly.
# This dynamically imports every module in this package and exports
# its public symbols (module.__all__ if present, otherwise all non-_
# attributes).

__all__ = []

for _finder, mod_name, _ispkg in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f".{mod_name}", __name__)
    if hasattr(module, "__all__"):
        for name in module.__all__:
            globals()[name] = getattr(module, name)
            __all__.append(name)
    else:
        for name in dir(module):
            if not name.startswith("_"):
                globals()[name] = getattr(module, name)
                __all__.append(name)