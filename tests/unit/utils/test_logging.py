from ice_core.utils.logging import setup_logger


def test_setup_logger_idempotent():
    """Calling setup_logger twice returns the same logger instance with handlers."""

    logger1 = setup_logger()
    logger2 = setup_logger()

    assert logger1 is logger2
    assert logger1.handlers, "Logger should have at least one handler configured"
