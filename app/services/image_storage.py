from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.exceptions import AppException


class ImageStorageBackend(Protocol):
    def save_bytes(self, *, key: str, payload: bytes, content_type: str) -> str: ...


@dataclass(frozen=True)
class StorageConfig:
    backend: str
    local_dir: str
    bucket: str | None
    endpoint: str | None


class LocalStorageBackend(ImageStorageBackend):
    def __init__(self, *, root_dir: str) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, *, key: str, payload: bytes, content_type: str) -> str:
        _ = content_type
        safe_key = key.replace("..", "").lstrip("/")
        target = self._root / safe_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return str(target)


class S3CompatibleStorageBackend(ImageStorageBackend):
    def __init__(
        self, *, bucket: str, endpoint: str | None, provider_name: str
    ) -> None:
        self._bucket = bucket
        self._endpoint = endpoint
        self._provider_name = provider_name

    def save_bytes(self, *, key: str, payload: bytes, content_type: str) -> str:
        _ = (payload, content_type)
        if not self._endpoint:
            raise AppException(
                status_code=500,
                detail=f"{self._provider_name} endpoint is not configured",
            )
        return f"{self._provider_name}://{self._bucket}/{key}"


class StorageFactory:
    def build(self, config: StorageConfig) -> ImageStorageBackend:
        backend = config.backend.lower()
        if backend == "local":
            return LocalStorageBackend(root_dir=config.local_dir)

        if backend in {"s3", "r2", "minio"}:
            if not config.bucket:
                raise AppException(status_code=500, detail="Storage bucket is required")
            return S3CompatibleStorageBackend(
                bucket=config.bucket,
                endpoint=config.endpoint,
                provider_name=backend,
            )

        raise AppException(status_code=422, detail="Storage backend is not supported")
