import os as _os

if _os.getenv("ICE_SDK_ENABLE_LEGACY_IMPORTS", "0") in {"1", "true", "True"}:
    # Users explicitly opted-in to legacy import path – re-export modern symbols.
    from importlib import import_module as _import_module

    _modern = _import_module("ice_sdk.providers.llm_service")
    globals().update({
        "LLMService": _modern.LLMService,  # type: ignore[attr-defined]
    })
    # Optional sub-package rendezvous
    _os.environ.setdefault("ICE_SDK_LEGACY_IMPORT_WARNING_SHOWN", "1")
else:
    raise ImportError(
        "'ice_tools' has been removed. Set ICE_SDK_ENABLE_LEGACY_IMPORTS=1 to temporarily re-enable."
    )

__all__ = ["LLMService"] 