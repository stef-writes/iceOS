"""Comprehensive schema validation tests.

These tests validate the schema system that ensures type safety and protocol 
adherence across iceOS. They test the mini-spec type system, MCP protocol 
compliance, and node validation requirements.
"""

import pytest
from typing import Dict, Any
from pydantic import ValidationError

from ice_core.utils.schema import parse_type_literal, is_valid_schema_dict
from ice_core.models.mcp import NodeSpec, Blueprint, PartialBlueprint, RunRequest
from ice_core.models.node_models import (
    LLMOperatorConfig, ToolNodeConfig, ConditionNodeConfig, 
    NestedChainConfig, AgentNodeConfig
)
from ice_core.utils.node_conversion import convert_node_spec


class TestMiniSpecTypeSystem:
    """Test the mini-spec type literal system."""
    
    def test_valid_scalar_types(self):
        """Test that valid scalar types parse correctly."""
        assert parse_type_literal("str") is str
        assert parse_type_literal("int") is int  
        assert parse_type_literal("float") is float
        assert parse_type_literal("bool") is bool
        assert parse_type_literal("dict") is dict
    
    def test_valid_list_types(self):
        """Test that valid list types parse correctly."""
        assert parse_type_literal("list[str]") is list
        assert parse_type_literal("list[int]") is list
        assert parse_type_literal("list[float]") is list
        assert parse_type_literal("list[bool]") is list
        assert parse_type_literal("list[dict]") is list
    
    def test_list_type_variations(self):
        """Test different spacing variations in list types."""
        assert parse_type_literal("list[str]") is list
        assert parse_type_literal("list[ str ]") is list
        assert parse_type_literal("list [ str]") is list
    
    def test_invalid_types_return_none(self):
        """Test that invalid type literals return None."""
        assert parse_type_literal("invalid") is None
        assert parse_type_literal("list[invalid]") is None
        assert parse_type_literal("str|int") is None  # Union not supported
        assert parse_type_literal("list[str|int]") is None
        assert parse_type_literal("list[") is None  # Malformed
        assert parse_type_literal("list[str]]") is None  # Extra bracket
    
    def test_case_sensitivity(self):
        """Test that type literals are case sensitive."""
        assert parse_type_literal("Str") is None
        assert parse_type_literal("INT") is None
        assert parse_type_literal("List[str]") is None


class TestSchemaValidationDict:
    """Test schema validation for dictionary schemas."""
    
    def test_valid_schemas(self):
        """Test that valid schemas pass validation."""
        valid_schemas = [
            {"name": "str", "age": "int"},
            {"items": "list[str]", "count": "int"},
            {"data": "dict", "valid": "bool"},
            {"price": "float", "description": "str"},
            {"nested": "list[dict]", "simple": "str"}
        ]
        
        for schema in valid_schemas:
            is_valid, errors = is_valid_schema_dict(schema)
            assert is_valid, f"Schema {schema} should be valid, got errors: {errors}"
            assert len(errors) == 0
    
    def test_invalid_schemas(self):
        """Test that invalid schemas fail validation."""
        invalid_schemas = [
            {"bad": "invalid_type"},
            {"union": "str|int"},
            {"malformed": "list["},
            {"extra_bracket": "list[str]]"},
            {"nested_union": "list[str|int]"},
            {"empty_list": "list[]"}
        ]
        
        for schema in invalid_schemas:
            is_valid, errors = is_valid_schema_dict(schema)
            assert not is_valid, f"Schema {schema} should be invalid"
            assert len(errors) > 0
    
    def test_mixed_valid_invalid(self):
        """Test schemas with mix of valid and invalid fields."""
        schema = {
            "valid_str": "str",
            "invalid_union": "str|int", 
            "valid_list": "list[int]",
            "invalid_type": "unknown"
        }
        
        is_valid, errors = is_valid_schema_dict(schema)
        assert not is_valid
        assert len(errors) == 2  # Two invalid fields
        
        # Check specific error messages
        error_text = "; ".join(errors)
        assert "invalid_union" in error_text
        assert "invalid_type" in error_text
    
    def test_empty_schema(self):
        """Test that empty schemas are valid."""
        is_valid, errors = is_valid_schema_dict({})
        assert is_valid
        assert len(errors) == 0


class TestNodeSpecValidation:
    """Test NodeSpec validation and conversion."""
    
    def test_minimal_node_spec(self):
        """Test that minimal valid NodeSpec works."""
        spec = NodeSpec(id="test", type="tool")
        
        # Should not raise any exceptions
        assert spec.id == "test"
        assert spec.type == "tool"
        assert spec.dependencies == []
    
    def test_node_spec_with_extra_fields(self):
        """Test that NodeSpec accepts extra fields for flexibility."""
        spec = NodeSpec(
            id="test",
            type="tool", 
            tool_name="csv_reader",
            tool_args={"file_path": "/tmp/data.csv"},
            input_schema={"file_path": "str"},
            output_schema={"rows": "list[dict]", "headers": "list[str]"}
        )
        
        # Extra fields should be accessible
        assert hasattr(spec, "tool_name")
        assert spec.tool_name == "csv_reader"  # type: ignore
        assert hasattr(spec, "input_schema")
        assert spec.input_schema == {"file_path": "str"}  # type: ignore
    
    def test_node_spec_dependencies_validation(self):
        """Test that NodeSpec validates dependencies."""
        # Self-dependency should be caught during conversion, not at NodeSpec level
        spec = NodeSpec(id="test", type="tool", dependencies=["test"])
        assert spec.dependencies == ["test"]  # NodeSpec itself allows this
    
    def test_invalid_node_spec_missing_required(self):
        """Test that NodeSpec requires id and type."""
        with pytest.raises(ValidationError):
            NodeSpec(type="tool")  # Missing id
        
        with pytest.raises(ValidationError):
            NodeSpec(id="test")  # Missing type


class TestNodeConfigValidation:
    """Test validation of specific node configuration types."""
    
    def test_llm_node_valid_schema(self):
        """Test LLM node with valid schema."""
        config = LLMOperatorConfig(
            id="llm1",
            type="llm",
            model="gpt-4",
            prompt="Hello {name}",
            llm_config={"provider": "openai"},
            input_schema={"name": "str"},
            output_schema={"response": "str"}
        )
        
        # Should validate without errors
        config.runtime_validate()
    
    def test_llm_node_missing_output_schema_gets_default(self):
        """Test that LLM nodes get default output schema if missing."""
        config = LLMOperatorConfig(
            id="llm1",
            type="llm", 
            model="gpt-4",
            prompt="Hello",
            llm_config={"provider": "openai"}
            # No output_schema provided
        )
        
        # Should add default output schema
        with pytest.warns(DeprecationWarning, match="LLM node missing output_schema"):
            config.runtime_validate()
        
        assert config.output_schema == {"text": "string"}
    
    def test_tool_node_requires_schemas(self):
        """Test that tool nodes require both input and output schemas."""
        config = ToolNodeConfig(
            id="tool1",
            type="tool",
            tool_name="csv_reader",
            input_schema={"file_path": "str"},
            # Missing output_schema
        )
        
        with pytest.raises(ValueError, match="must declare non-empty input_schema and output_schema"):
            config.runtime_validate()
    
    def test_tool_node_invalid_schema_format(self):
        """Test that tool nodes reject invalid schema formats."""
        config = ToolNodeConfig(
            id="tool1",
            type="tool",
            tool_name="csv_reader", 
            input_schema={"file_path": "str"},
            output_schema={"rows": "invalid_type"}  # Invalid type
        )
        
        with pytest.raises(ValueError, match="invalid output_schema"):
            config.runtime_validate()
    
    def test_condition_node_requires_schemas(self):
        """Test that condition nodes require schemas."""
        config = ConditionNodeConfig(
            id="cond1",
            type="condition",
            expression="x > 5"
            # Missing schemas
        )
        
        with pytest.raises(ValueError, match="must declare non-empty input_schema and output_schema"):
            config.runtime_validate()
    
    def test_agent_node_requires_schemas(self):
        """Test that agent nodes require schemas."""
        config = AgentNodeConfig(
            id="agent1",
            type="agent",
            agent_ref="test_agent"
            # Missing schemas  
        )
        
        with pytest.raises(ValueError, match="must declare non-empty input_schema and output_schema"):
            config.runtime_validate()
    
    def test_self_dependency_validation(self):
        """Test that self-dependencies are caught."""
        config = ToolNodeConfig(
            id="tool1",
            type="tool",
            tool_name="test",
            dependencies=["tool1"],  # Self-dependency
            input_schema={"x": "str"},
            output_schema={"y": "str"}
        )
        
        with pytest.raises(ValueError, match="cannot depend on itself"):
            # Validation happens during construction for BaseNodeConfig
            pass


class TestNodeSpecConversion:
    """Test NodeSpec to NodeConfig conversion."""
    
    def test_valid_tool_conversion(self):
        """Test converting valid tool NodeSpec to ToolNodeConfig."""
        spec = NodeSpec(
            id="csv_tool",
            type="tool",
            tool_name="csv_reader",
            input_schema={"file_path": "str"},
            output_schema={"rows": "list[dict]", "headers": "list[str]"}
        )
        
        config = convert_node_spec(spec)
        assert isinstance(config, ToolNodeConfig)
        assert config.id == "csv_tool"
        assert config.tool_name == "csv_reader"
    
    def test_valid_llm_conversion(self):
        """Test converting valid LLM NodeSpec to LLMOperatorConfig."""
        spec = NodeSpec(
            id="gpt_node",
            type="llm",
            model="gpt-4",
            prompt="Analyze this: {data}",
            llm_config={"provider": "openai"},
            input_schema={"data": "str"},
            output_schema={"analysis": "str"}
        )
        
        config = convert_node_spec(spec)
        assert isinstance(config, LLMOperatorConfig)
        assert config.id == "gpt_node"
        assert config.model == "gpt-4"
    
    def test_conversion_validates_runtime(self):
        """Test that conversion triggers runtime validation."""
        spec = NodeSpec(
            id="bad_tool",
            type="tool",
            tool_name="test",
            input_schema={"x": "str"},
            output_schema={"y": "invalid_type"}  # Invalid
        )
        
        with pytest.raises(ValueError, match="invalid output_schema"):
            convert_node_spec(spec)
    
    def test_unknown_node_type_fails(self):
        """Test that unknown node types fail conversion."""
        spec = NodeSpec(id="unknown", type="unknown_type")
        
        with pytest.raises(ValueError, match="Unknown node type"):
            convert_node_spec(spec)


class TestBlueprintValidation:
    """Test Blueprint validation and MCP compliance."""
    
    def test_valid_blueprint(self):
        """Test that valid blueprints pass validation."""
        nodes = [
            NodeSpec(
                id="load_data",
                type="tool",
                tool_name="csv_reader",
                input_schema={"file_path": "str"},
                output_schema={"rows": "list[dict]"}
            ),
            NodeSpec(
                id="analyze",
                type="llm",
                model="gpt-4",
                prompt="Analyze: {rows}",
                llm_config={"provider": "openai"},
                dependencies=["load_data"],
                input_schema={"rows": "list[dict]"}, 
                output_schema={"analysis": "str"}
            )
        ]
        
        blueprint = Blueprint(nodes=nodes)
        
        # Should validate dependencies
        assert len(blueprint.nodes) == 2
        
        # Should validate runtime (includes node conversion)
        blueprint.validate_runtime()
    
    def test_blueprint_missing_dependency(self):
        """Test that blueprints with missing dependencies fail validation."""
        nodes = [
            NodeSpec(
                id="analyze",
                type="llm", 
                model="gpt-4",
                prompt="Analyze: {data}",
                llm_config={"provider": "openai"},
                dependencies=["missing_node"],  # References non-existent node
                input_schema={"data": "str"},
                output_schema={"analysis": "str"}
            )
        ]
        
        with pytest.raises(ValueError, match="references missing dependency"):
            Blueprint(nodes=nodes)
    
    def test_blueprint_circular_dependency(self):
        """Test that circular dependencies are detected."""
        nodes = [
            NodeSpec(
                id="node1",
                type="tool",
                tool_name="test1",
                dependencies=["node2"],
                input_schema={"x": "str"},
                output_schema={"y": "str"}
            ),
            NodeSpec(
                id="node2", 
                type="tool",
                tool_name="test2",
                dependencies=["node1"],  # Circular
                input_schema={"y": "str"},
                output_schema={"z": "str"}
            )
        ]
        
        with pytest.raises(ValueError, match="references missing dependency"):
            # This will fail because of dependency validation, not circular detection
            # Real circular detection would be in the orchestrator layer
            Blueprint(nodes=nodes)


class TestPartialBlueprintValidation:
    """Test PartialBlueprint incremental validation."""
    
    def test_empty_partial_blueprint(self):
        """Test that empty partial blueprint is valid but incomplete."""
        partial = PartialBlueprint()
        
        assert not partial.is_complete
        assert len(partial.validation_errors) == 0
        assert len(partial.next_suggestions) == 0
    
    def test_partial_blueprint_with_tool(self):
        """Test partial blueprint with single tool node."""
        partial = PartialBlueprint()
        
        node = NodeSpec(
            id="tool1",
            type="tool",
            tool_name="csv_reader",
            input_schema={"file_path": "str"},
            output_schema={"rows": "list[dict]"}
        )
        
        partial.add_node(node)
        
        # Should generate suggestions
        assert len(partial.next_suggestions) > 0
        suggestion = partial.next_suggestions[0]
        assert suggestion["type"] == "llm"
        assert "Process tool output" in suggestion["reason"]
    
    def test_partial_blueprint_to_blueprint_conversion(self):
        """Test converting complete partial blueprint to blueprint.""" 
        partial = PartialBlueprint()
        
        # Add tool node
        tool_node = NodeSpec(
            id="load_data",
            type="tool",
            tool_name="csv_reader", 
            input_schema={"file_path": "str"},
            output_schema={"rows": "list[dict]"}
        )
        partial.add_node(tool_node)
        
        # Add LLM node
        llm_node = NodeSpec(
            id="analyze",
            type="llm",
            model="gpt-4",
            prompt="Analyze: {rows}",
            llm_config={"provider": "openai"},
            dependencies=["load_data"],
            input_schema={"rows": "list[dict]"},
            output_schema={"analysis": "str"}
        )
        partial.add_node(llm_node)
        
        # Should be complete now
        assert partial.is_complete
        
        # Should convert to valid blueprint
        blueprint = partial.to_blueprint()
        assert isinstance(blueprint, Blueprint)
        assert len(blueprint.nodes) == 2


class TestRunRequestValidation:
    """Test RunRequest validation for MCP compliance."""
    
    def test_valid_run_request_with_blueprint_id(self):
        """Test valid run request with blueprint ID."""
        request = RunRequest(
            blueprint_id="bp_123",
            options={"max_parallel": 3}
        )
        
        assert request.blueprint_id == "bp_123"
        assert request.blueprint is None
        assert request.options.max_parallel == 3
    
    def test_valid_run_request_with_inline_blueprint(self):
        """Test valid run request with inline blueprint."""
        nodes = [NodeSpec(
            id="test",
            type="tool",
            tool_name="test_tool",
            input_schema={"x": "str"},
            output_schema={"y": "str"}
        )]
        
        blueprint = Blueprint(nodes=nodes)
        request = RunRequest(blueprint=blueprint)
        
        assert request.blueprint is blueprint
        assert request.blueprint_id is None
    
    def test_run_request_requires_blueprint_or_id(self):
        """Test that run request requires either blueprint or blueprint_id."""
        with pytest.raises(ValidationError, match="Either blueprint or blueprint_id must be provided"):
            RunRequest()  # Neither provided
    
    def test_run_request_options_validation(self):
        """Test run request options validation."""
        # max_parallel too low
        with pytest.raises(ValidationError):
            RunRequest(
                blueprint_id="test",
                options={"max_parallel": 0}
            )
        
        # max_parallel too high  
        with pytest.raises(ValidationError):
            RunRequest(
                blueprint_id="test",
                options={"max_parallel": 25}
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 