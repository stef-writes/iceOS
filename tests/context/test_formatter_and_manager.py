from ice_sdk.context.formatter import ContextFormatter
from ice_sdk.context.manager import GraphContext, GraphContextManager
from ice_sdk.context.store import ContextStore
from ice_sdk.models.node_models import ContextFormat, ContextRule


def test_context_formatter_truncates_long_text(tmp_path):
    formatter = ContextFormatter()
    rule = ContextRule(format=ContextFormat.TEXT, max_tokens=5)  # ~20 chars budget
    long_text = "x" * 200
    formatted = formatter.format(long_text, rule)
    assert len(formatted) <= 20  # approx 4 chars per token


def test_graph_context_manager_update_and_get(tmp_path):
    store_path = tmp_path / "ctx.json"
    store = ContextStore(context_store_path=str(store_path))
    ctx_mgr = GraphContextManager(store=store)
    gc = GraphContext(session_id="sess1")
    ctx_mgr.set_context(gc)

    node_id = "node123"
    data = {"foo": "bar"}
    ctx_mgr.update_node_context(node_id, data)
    retrieved = ctx_mgr.get_node_context(node_id)
    assert retrieved == data
