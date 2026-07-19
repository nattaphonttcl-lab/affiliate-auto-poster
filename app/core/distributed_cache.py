from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError


class RedisHealth:
    def __init__(self, redis_url: str) -> None:
        self._client = Redis.from_url(redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            return False
