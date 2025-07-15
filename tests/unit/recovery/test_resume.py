import pytest

# Module-level skip until resume implementation lands (issue #124)
pytest.skip(
    "Resume functionality not yet implemented; tracked in issue #124",
    allow_module_level=True,
)
