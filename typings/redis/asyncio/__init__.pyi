from typing import Any, Protocol, TypeVar

T = TypeVar("T")

class _RedisProto(Protocol):
    ...

class Redis:  # minimal placeholder for typing
    ...

def from_url(url: str, *args: Any, **kwargs: Any) -> Redis: ...
