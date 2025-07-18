from .json_merge_skill import JSONMergeSkill  # noqa: F401
from .sleep_skill import SleepSkill  # noqa: F401
from .sum_skill import SumSkill  # noqa: F401
from .computer_skill import ComputerSkill  # noqa: F401
from .markdown_to_html_skill import MarkdownToHTMLSkill  # noqa: F401
from .jinja_render_skill import JinjaRenderSkill  # noqa: F401

try:
    from ..registry import global_skill_registry

    global_skill_registry.register("json_merge", JSONMergeSkill())
    global_skill_registry.register("sleep", SleepSkill())
    global_skill_registry.register("sum", SumSkill())
    global_skill_registry.register("computer", ComputerSkill())
    global_skill_registry.register("markdown_to_html", MarkdownToHTMLSkill())
    global_skill_registry.register("jinja_render", JinjaRenderSkill())
except Exception:  # pragma: no cover
    pass 