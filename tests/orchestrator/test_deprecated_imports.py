def test_deprecated_base_script_chain_import() -> None:
    """Importing from canonical location should expose the same symbols."""

    from ice_sdk.orchestrator.base_script_chain import (  # noqa: WPS433
        BaseScriptChain,
        FailurePolicy,
    )

    assert BaseScriptChain is not None
    assert FailurePolicy is not None
