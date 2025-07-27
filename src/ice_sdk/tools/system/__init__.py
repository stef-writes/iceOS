from .computer_tool import ComputerTool
from ice_core.models import NodeType
from .jinja_render_tool import JinjaRenderTool
from .json_merge_tool import JSONMergeTool
from .markdown_to_html_tool import MarkdownToHTMLTool
from .rows_validator_tool import RowsValidatorTool
from .sleep_tool import SleepTool
from .sum_tool import SumTool

try:
    from ice_core.unified_registry import registry

    registry.register_instance(NodeType.TOOL, "computer", ComputerTool())
    registry.register_instance(NodeType.TOOL, "jinja_render", JinjaRenderTool())
    registry.register_instance(NodeType.TOOL, "json_merge", JSONMergeTool())
    registry.register_instance(NodeType.TOOL, "markdown_to_html", MarkdownToHTMLTool())
    registry.register_instance(NodeType.TOOL, "rows_validator", RowsValidatorTool())
    registry.register_instance(NodeType.TOOL, "sleep", SleepTool())
    registry.register_instance(NodeType.TOOL, "sum", SumTool())
except Exception:  # pragma: no cover
    pass
