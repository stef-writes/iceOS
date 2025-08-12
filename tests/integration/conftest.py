"""Pytest configuration for integration tests.

Provides fixtures for Redis integration testing using Docker containers.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio

try:
    import redis.asyncio as redis  # type: ignore

    HAS_REDIS = True
except Exception:
    HAS_REDIS = False

try:
    from testcontainers.redis import RedisContainer

    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False
    RedisContainer = None


# Removed custom event_loop fixture to let pytest-asyncio handle it automatically
# when using asyncio_mode = auto


@pytest_asyncio.fixture(scope="session")
async def redis_container():
    """Provide a Redis container for integration tests.

    This fixture starts a Redis Docker container that persists for the entire
    test session. The container is automatically cleaned up after tests complete.
    """
    if not HAS_TESTCONTAINERS or not HAS_REDIS:
        pytest.skip(
            "redis/testcontainers not available - install with: pip install redis testcontainers"
        )

    with RedisContainer() as container:
        yield container


@pytest_asyncio.fixture
async def redis_client(redis_container) -> AsyncGenerator[object, None]:
    """Provide an async Redis client connected to the test container.

    This fixture creates a new Redis client for each test, ensuring test isolation.
    The client is automatically closed after the test completes.
    """
    # Get connection details
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    client = redis.from_url(f"redis://{host}:{port}/0", decode_responses=True)

    # Ensure clean state
    await client.flushdb()

    yield client

    # Cleanup
    await client.close()


@pytest.fixture
def redis_url(redis_container) -> str:
    """Provide the Redis connection URL for tests that need it."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"
