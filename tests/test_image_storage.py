from pathlib import Path

from app.services.image_storage import (
    LocalStorageBackend,
    StorageConfig,
    StorageFactory,
)


def test_local_storage_backend_saves_payload(tmp_path: Path) -> None:
    backend = LocalStorageBackend(root_dir=str(tmp_path))
    uri = backend.save_bytes(
        key="images/test/sample.txt",
        payload=b"hello-image",
        content_type="text/plain",
    )

    path = Path(uri)
    assert path.exists()
    assert path.read_bytes() == b"hello-image"


def test_storage_factory_builds_local_backend(tmp_path: Path) -> None:
    factory = StorageFactory()
    backend = factory.build(
        StorageConfig(
            backend="local",
            local_dir=str(tmp_path),
            bucket=None,
            endpoint=None,
        )
    )
    uri = backend.save_bytes(
        key="images/factory/file.bin",
        payload=b"data",
        content_type="application/octet-stream",
    )
    assert Path(uri).exists()
