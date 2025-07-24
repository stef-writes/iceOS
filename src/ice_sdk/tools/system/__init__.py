from .computer_tool import ComputerTool
from ice_core.models import NodeType
from .csv_reader_tool import CSVReaderTool
from .csv_writer_tool import CSVWriterTool
from .insights_tool import InsightsTool
from .jinja_render_tool import JinjaRenderTool
from .json_merge_tool import JSONMergeTool
from .line_item_generator_tool import LineItemGeneratorTool
from .markdown_to_html_tool import MarkdownToHTMLTool
from .rows_validator_tool import RowsValidatorTool
from .sleep_tool import SleepTool
from .sum_tool import SumTool
from .summarizer_tool import SummarizerTool

try:
    from ice_sdk.unified_registry import registry

    registry.register_instance(NodeType.TOOL, "computer", ComputerTool())
    registry.register_instance(NodeType.TOOL, "csv_reader", CSVReaderTool())
    registry.register_instance(NodeType.TOOL, "csv_writer", CSVWriterTool())
    registry.register_instance(NodeType.TOOL, "insights", InsightsTool())
    registry.register_instance(NodeType.TOOL, "jinja_render", JinjaRenderTool())
    registry.register_instance(NodeType.TOOL, "json_merge", JSONMergeTool())
    registry.register_instance(NodeType.TOOL, "line_item_generator", LineItemGeneratorTool())
    registry.register_instance(NodeType.TOOL, "markdown_to_html", MarkdownToHTMLTool())
    registry.register_instance(NodeType.TOOL, "rows_validator", RowsValidatorTool())
    registry.register_instance(NodeType.TOOL, "sleep", SleepTool())
    registry.register_instance(NodeType.TOOL, "sum", SumTool())
    registry.register_instance(NodeType.TOOL, "summarizer", SummarizerTool())
except Exception:  # pragma: no cover
    pass
