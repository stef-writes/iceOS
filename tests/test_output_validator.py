from app.nodes.ai.output_validator import OutputValidator


def test_empty_plain_output_fails():
    # Empty output should fail validation for simple schema requiring text
    schema = {"text": "str"}
    output, success, error = OutputValidator.validate_and_coerce(
        generated_text="   ", output_format="plain", output_schema=schema
    )
    assert not success
    assert error is not None
    assert output is None


def test_nonempty_plain_output_passes():
    schema = {"text": "str"}
    output, success, error = OutputValidator.validate_and_coerce(
        generated_text="Hola mundo", output_format="plain", output_schema=schema
    )
    assert success
    assert error is None
    assert output == {"text": "Hola mundo"} 