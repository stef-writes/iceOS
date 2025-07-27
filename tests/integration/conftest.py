"""Pytest configuration for integration tests.

Provides fixtures for Redis integration testing using Docker containers.
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import redis.asyncio as redis

try:
    from testcontainers.redis import RedisContainer
    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False
    RedisContainer = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def redis_container():
    """Provide a Redis container for integration tests.
    
    This fixture starts a Redis Docker container that persists for the entire
    test session. The container is automatically cleaned up after tests complete.
    """
    if not HAS_TESTCONTAINERS:
        pytest.skip("testcontainers not available - install with: pip install testcontainers")
    
    with RedisContainer() as container:
        yield container


@pytest_asyncio.fixture
async def redis_client(redis_container) -> AsyncGenerator[redis.Redis, None]:
    """Provide an async Redis client connected to the test container.
    
    This fixture creates a new Redis client for each test, ensuring test isolation.
    The client is automatically closed after the test completes.
    """
    # Get connection details
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    
    client = redis.from_url(
        f"redis://{host}:{port}/0",
        decode_responses=True
    )
    
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