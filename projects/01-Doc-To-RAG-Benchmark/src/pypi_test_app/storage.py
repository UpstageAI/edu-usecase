from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List
from uuid import uuid4

from fastapi import UploadFile

from .schemas import UploadMetadata


class UploadStorage:
    """Stores uploaded files on disk alongside metadata in JSON."""

    def __init__(self, base_directory: Path | None = None) -> None:
        default_root = Path(os.getenv("PYPI_TEST_APP_STORAGE", Path.home() / ".pypi_test_app" / "uploads"))
        self.base_directory = base_directory or default_root
        self.metadata_path = self.base_directory / "metadata.json"
        self._lock = asyncio.Lock()

    async def ensure_ready(self) -> None:
        await asyncio.to_thread(self.base_directory.mkdir, parents=True, exist_ok=True)
        if not self.metadata_path.exists():
            await asyncio.to_thread(self.metadata_path.write_text, "[]", encoding="utf-8")

    async def list_uploads(self) -> List[UploadMetadata]:
        await self.ensure_ready()
        raw_items = await self._read_metadata()
        return [UploadMetadata.model_validate(item) for item in raw_items]

    async def save_files(self, files: Iterable[UploadFile]) -> List[UploadMetadata]:
        saved_items: List[UploadMetadata] = []
        for upload in files:
            data = await upload.read()
            metadata = await self.save_bytes(data=data, original_name=upload.filename or "unnamed")
            saved_items.append(metadata)
            await upload.close()
        return saved_items

    async def save_bytes(self, data: bytes, original_name: str, *, extension: str | None = None) -> UploadMetadata:
        await self.ensure_ready()

        suffix = Path(original_name).suffix
        if extension:
            suffix = f".{extension.lower().lstrip('.')}"
        suffix = suffix.lower()
        extension_value = suffix[1:] if suffix.startswith(".") else suffix

        timestamp = datetime.now(timezone.utc)
        stored_name = f"{timestamp.strftime('%Y%m%d%H%M%S')}_{uuid4().hex}{suffix}"
        destination = self.base_directory / stored_name

        metadata = UploadMetadata(
            id=str(uuid4()),
            original_name=original_name,
            stored_name=stored_name,
            size_bytes=len(data),
            extension=extension_value,
            uploaded_at=timestamp,
        )

        async with self._lock:
            await asyncio.to_thread(destination.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(destination.write_bytes, data)
            existing = await self._read_metadata()
            existing.append(metadata.model_dump(mode="json"))
            await self._write_metadata(existing)

        return metadata

    async def _read_metadata(self) -> list[dict]:
        if not self.metadata_path.exists():
            return []
        content = await asyncio.to_thread(self.metadata_path.read_text, encoding="utf-8")
        try:
            data = json.loads(content) if content.strip() else []
        except json.JSONDecodeError:
            data = []
        return data

    async def _write_metadata(self, data: list[dict]) -> None:
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        await asyncio.to_thread(self.metadata_path.write_text, serialized, encoding="utf-8")
