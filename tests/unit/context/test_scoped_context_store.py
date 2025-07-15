from ice_sdk.context.scoped_context_store import ScopedContextStore


def test_scoped_context_store_isolation(tmp_path):
    """Data for one scope must not bleed into another."""
    db_path = tmp_path / "store.json"

    store_a = ScopedContextStore("alpha", context_store_path=str(db_path))
    store_b = ScopedContextStore("bravo", context_store_path=str(db_path))

    store_a.set("node1", {"value": 1})
    store_b.set("node1", {"value": 2})

    assert store_a.get("node1") == {"value": 1}
    assert store_b.get("node1") == {"value": 2}

    store_a.clear()
    assert store_a.get("node1") == {}
    assert store_b.get("node1") == {"value": 2}
