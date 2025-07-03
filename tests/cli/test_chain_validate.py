from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ice_cli.cli import app


def _write_minimal_chain(path: Path) -> None:
    content = (
        "from ice_orchestrator.script_chain import ScriptChain\n"
        "from ice_sdk.models.node_models import AiNodeConfig, LLMConfig, ModelProvider\n\n"
        "# Minimal node config --------------------------------------------\n"
        "nodes = [\n"
        "    AiNodeConfig(\n"
        '        id="n0",\n'
        '        type="ai",\n'
        '        name="Hello",\n'
        '        model="gpt-3.5-turbo",\n'
        '        prompt="Say hi",\n'
        '        llm_config=LLMConfig(provider=ModelProvider.OPENAI, model="gpt-3.5-turbo"),\n'
        "    )\n"
        "]\n\n"
        'chain = ScriptChain(nodes=nodes, name="demo")\n'
    )
    path.write_text(content)


def test_sdk_chain_validate_pass(tmp_path: Path) -> None:  # noqa: D401
    chain_file = tmp_path / "hello.chain.py"
    _write_minimal_chain(chain_file)

    runner = CliRunner()
    result = runner.invoke(app, ["sdk", "chain-validate", str(chain_file)])

    assert result.exit_code == 0, result.output
    assert "Chain is valid" in result.output
