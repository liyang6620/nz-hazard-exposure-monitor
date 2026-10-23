from __future__ import annotations

import os
import tempfile
from pathlib import Path, PurePosixPath


class LocalObjectStore:
    CONTAINERS = frozenset({"raw", "curated", "gold", "briefings", "web"})

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        for container in self.CONTAINERS:
            (self._root / container).mkdir(parents=True, exist_ok=True)

    def put_bytes(self, container: str, path: str, data: bytes) -> None:
        destination = self._path(container, path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(dir=destination.parent)
        try:
            with os.fdopen(descriptor, "wb") as temporary:
                temporary.write(data)
            os.replace(temporary_name, destination)
        finally:
            Path(temporary_name).unlink(missing_ok=True)

    def get_bytes(self, container: str, path: str) -> bytes:
        return self._path(container, path).read_bytes()

    def _path(self, container: str, path: str) -> Path:
        if container not in self.CONTAINERS:
            raise ValueError(f"Unknown storage container: {container}")
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Storage path must be relative and cannot contain '..'")
        return self._root / container / Path(*relative.parts)


class LocalStaticSitePublisher:
    def __init__(self, objects: LocalObjectStore) -> None:
        self._objects = objects

    def publish(self, path: str, content: bytes) -> None:
        self._objects.put_bytes("web", path, content)
