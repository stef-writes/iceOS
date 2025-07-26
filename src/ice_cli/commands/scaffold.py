"""Scaffolding commands for generating iceOS components."""
import click
from pathlib import Path
from typing import Dict, Any, List, Optional
import textwrap
import json

try:
    import inquirer
    HAS_INQUIRER = True
except ImportError:
    HAS_INQUIRER = False
    print("Note: Install 'inquirer' for interactive mode: pip install inquirer")


@click.group()
def scaffold():
    """Generate iceOS components from templates."""
    pass


@scaffold.command()
@click.option('--name', help='Tool name')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
@click.option('--output-dir', type=Path, default=Path('src/ice_sdk/tools/custom'))
def tool(name: Optional[str], interactive: bool, output_dir: Path):
    """Scaffold a new tool with best practices."""
    if interactive or not name:
        config = _interactive_tool_config(name)
    else:
        config = _basic_tool_config(name)
    
    # Generate tool file
    tool_path = output_dir / f"{config['file_name']}.py"
    tool_content = _generate_tool_code(config)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write tool file
    tool_path.write_text(tool_content)
    click.echo(f"✅ Created tool: {tool_path}")
    
    # Generate test if requested
    if config.get('generate_tests', True):
        test_path = Path('tests/unit/tools') / f"test_{config['file_name']}.py"
        test_content = _generate_tool_test(config)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(test_content)
        click.echo(f"✅ Created test: {test_path}")
    
    # Show next steps
    click.echo("\n📝 Next steps:")
    click.echo(f"1. Implement the execute() method in {tool_path}")
    click.echo(f"2. Run tests: pytest {test_path}")
    click.echo("3. The tool is auto-registered and ready to use!")


def _interactive_tool_config(name: Optional[str]) -> Dict[str, Any]:
    """Interactive prompts for tool configuration."""
    if not HAS_INQUIRER:
        click.echo("Error: inquirer not installed. Using basic config instead.")
        click.echo("Install with: pip install inquirer")
        return _basic_tool_config(name or "my_tool")
    
    questions = [
        inquirer.Text(
            'name',
            message='Tool name',
            default=name or 'my_tool',
            validate=lambda _, x: x.replace('_', '').isalnum()
        ),
        inquirer.Text(
            'description',
            message='Tool description',
            default='Describe what this tool does'
        ),
        inquirer.List(
            'category',
            message='Tool category',
            choices=['system', 'web', 'db', 'marketplace', 'custom']
        ),
        inquirer.Checkbox(
            'features',
            message='Select features',
            choices=[
                ('Async execution', 'async'),
                ('Retry logic', 'retry'),
                ('Input validation', 'validation'),
                ('Rate limiting', 'rate_limit'),
                ('Caching', 'cache'),
                ('External API calls', 'external_api')
            ],
            default=['async', 'validation']
        ),
        inquirer.Confirm(
            'generate_tests',
            message='Generate test file?',
            default=True
        )
    ]
    
    answers = inquirer.prompt(questions)
    
    # Input schema configuration
    click.echo("\n📋 Define input schema:")
    inputs = []
    while True:
        field_name = click.prompt("Field name (or 'done')", type=str)
        if field_name.lower() == 'done':
            break
        field_type = click.prompt("Field type", type=click.Choice(['string', 'integer', 'number', 'boolean', 'array', 'object']))
        required = click.confirm("Required?", default=True)
        description = click.prompt("Description", default="")
        
        inputs.append({
            'name': field_name,
            'type': field_type,
            'required': required,
            'description': description
        })
    
    # Output schema configuration  
    click.echo("\n📋 Define output schema:")
    outputs = []
    while True:
        field_name = click.prompt("Field name (or 'done')", type=str)
        if field_name.lower() == 'done':
            break
        field_type = click.prompt("Field type", type=click.Choice(['string', 'integer', 'number', 'boolean', 'array', 'object']))
        description = click.prompt("Description", default="")
        
        outputs.append({
            'name': field_name,
            'type': field_type,
            'description': description
        })
    
    config = answers
    config['inputs'] = inputs
    config['outputs'] = outputs
    config['class_name'] = ''.join(word.capitalize() for word in config['name'].split('_')) + 'Tool'
    config['file_name'] = config['name'] + '_tool'
    
    return config


def _basic_tool_config(name: str) -> Dict[str, Any]:
    """Basic tool configuration with defaults."""
    return {
        'name': name,
        'description': f'{name} tool',
        'category': 'custom',
        'features': ['async', 'validation'],
        'generate_tests': True,
        'class_name': ''.join(word.capitalize() for word in name.split('_')) + 'Tool',
        'file_name': name + '_tool',
        'inputs': [
            {'name': 'data', 'type': 'object', 'required': True, 'description': 'Input data'}
        ],
        'outputs': [
            {'name': 'result', 'type': 'object', 'description': 'Processing result'}
        ]
    }


def _generate_tool_code(config: Dict[str, Any]) -> str:
    """Generate tool Python code."""
    # Build imports
    imports = [
        "from typing import Dict, Any, Optional",
        "from ice_core.base_tool import ToolBase",
        "from ice_sdk.decorators import tool"
    ]
    
    if 'retry' in config.get('features', []):
        imports.append("from ice_sdk.utils.retry import retry_async")
    if 'rate_limit' in config.get('features', []):
        imports.append("from ice_sdk.utils.rate_limit import rate_limit")
    if 'external_api' in config.get('features', []):
        imports.append("import httpx")
        
    # Build input schema
    input_props = {}
    required_fields = []
    for inp in config['inputs']:
        input_props[inp['name']] = {
            "type": inp['type'],
            "description": inp['description']
        }
        if inp['required']:
            required_fields.append(inp['name'])
    
    input_schema = {
        "type": "object",
        "properties": input_props,
        "required": required_fields
    }
    
    # Build output schema
    output_props = {}
    for out in config['outputs']:
        output_props[out['name']] = {
            "type": out['type'],
            "description": out['description']
        }
    
    output_schema = {
        "type": "object",
        "properties": output_props,
        "required": list(output_props.keys())
    }
    
    # Generate execute method
    execute_method = _generate_execute_method(config)
    
    # Build the complete code
    code = f'''"""{config['description']}"""
{chr(10).join(imports)}


@tool(
    name="{config['name']}",
    auto_register=True,
    marketplace_metadata={{
        "category": "{config['category']}",
        "tags": [],
        "version": "1.0.0"
    }}
)
class {config['class_name']}(ToolBase):
    """{config['description']}
    
    This tool was scaffolded by the iceOS CLI.
    """
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Define input schema."""
        return {json.dumps(input_schema, indent=8).replace('"', "'")}
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Define output schema."""
        return {json.dumps(output_schema, indent=8).replace('"', "'")}
    
{execute_method}
'''
    
    return code


def _generate_execute_method(config: Dict[str, Any]) -> str:
    """Generate the execute method based on features."""
    decorators = []
    if 'retry' in config.get('features', []):
        decorators.append("    @retry_async(max_attempts=3)")
    if 'rate_limit' in config.get('features', []):
        decorators.append("    @rate_limit(calls_per_minute=60)")
    
    # Input extraction
    input_extractions = []
    for inp in config['inputs']:
        if inp['required']:
            input_extractions.append(f"        {inp['name']} = kwargs['{inp['name']}']")
        else:
            input_extractions.append(f"        {inp['name']} = kwargs.get('{inp['name']}')")
    
    # Validation logic
    validation_lines = []
    if 'validation' in config.get('features', []):
        for inp in config['inputs']:
            if inp['required']:
                validation_lines.append(f"        if '{inp['name']}' not in kwargs:")
                validation_lines.append(f"            raise ValueError(\"Missing required field: {inp['name']}\")")
    
    # Build method
    method_lines = decorators + [
        "    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:",
        f'        """Execute the {config["name"]} tool.',
        "        ",
        "        Args:",
    ]
    
    # Add arg documentation
    for inp in config['inputs']:
        req = "Required" if inp['required'] else "Optional"
        method_lines.append(f"            {inp['name']}: {inp['description']} ({req})")
    
    method_lines.extend([
        "        ",
        "        Returns:",
        "            Dict containing:"
    ])
    
    for out in config['outputs']:
        method_lines.append(f"            - {out['name']}: {out['description']}")
    
    method_lines.append('        """')
    
    # Add validation
    if validation_lines:
        method_lines.extend(["        # Input validation"] + validation_lines + [""])
    
    # Add input extraction
    method_lines.extend(["        # Extract inputs"] + input_extractions + [""])
    
    # Add placeholder implementation
    method_lines.extend([
        "        # TODO: Implement your tool logic here",
        "        # This is where you add the actual functionality",
        "        ",
        "        # For now, return a placeholder result",
        "        return {"
    ])
    
    for out in config['outputs']:
        if out['type'] == 'string':
            default = f"'TODO: {out['name']}'"
        elif out['type'] in ['integer', 'number']:
            default = '0'
        elif out['type'] == 'boolean':
            default = 'False'
        elif out['type'] == 'array':
            default = '[]'
        else:
            default = '{}'
        method_lines.append(f"            '{out['name']}': {default},")
    
    method_lines.append("        }")
    
    return '\n'.join(method_lines)


def _generate_tool_test(config: Dict[str, Any]) -> str:
    """Generate test code for the tool."""
    # Build sample input
    sample_input = {}
    for inp in config['inputs']:
        if inp['type'] == 'string':
            sample_input[inp['name']] = f"test_{inp['name']}"
        elif inp['type'] == 'integer':
            sample_input[inp['name']] = 42
        elif inp['type'] == 'number':
            sample_input[inp['name']] = 3.14
        elif inp['type'] == 'boolean':
            sample_input[inp['name']] = True
        elif inp['type'] == 'array':
            sample_input[inp['name']] = []
        else:
            sample_input[inp['name']] = {}
    
    return f'''"""Tests for {config['class_name']}."""
import pytest
from typing import Dict, Any
from ice_sdk.tools.{config['category']}.{config['file_name']} import {config['class_name']}


class Test{config['class_name']}:
    """Test cases for {config['class_name']}."""
    
    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return {config['class_name']}()
    
    @pytest.fixture
    def sample_input(self) -> Dict[str, Any]:
        """Sample valid input."""
        return {json.dumps(sample_input, indent=12)}
    
    async def test_execute_success(self, tool, sample_input):
        """Test successful execution."""
        result = await tool.execute(sample_input)
        
        # Verify output structure
        assert isinstance(result, dict)
        {chr(10).join(f'        assert "{out["name"]}" in result' for out in config['outputs'])}
    
    async def test_input_validation(self, tool):
        """Test input validation."""
        # Test missing required fields
        {chr(10).join(self._generate_validation_tests(inp) for inp in config['inputs'] if inp['required'])}
    
    def test_input_schema(self, tool):
        """Test input schema is valid."""
        schema = tool.get_input_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        
        # Check all inputs are in schema
        {chr(10).join(f'        assert "{inp["name"]}" in schema["properties"]' for inp in config['inputs'])}
    
    def test_output_schema(self, tool):
        """Test output schema is valid."""
        schema = tool.get_output_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        
        # Check all outputs are in schema
        {chr(10).join(f'        assert "{out["name"]}" in schema["properties"]' for out in config['outputs'])}
'''

    def _generate_validation_tests(self, inp: Dict[str, Any]) -> str:
        return f'''
        with pytest.raises(ValueError, match="{inp['name']}"):
            await tool.execute({{}})''' 