from importlib import import_module

# Auto-import packaged chains to trigger their registration side-effects.
for _mod in (
    "ice_sdk.chains.inventory_summary_chain",
):
    try:
        import_module(_mod)
    except ModuleNotFoundError:
        continue 