"""TDnet ダウンロードファイルの永続ディスクキャッシュ。"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CacheInfo:
    enabled: bool
    cache_dir: Path | None
    entry_count: int
    total_bytes: int


class CacheStore:
    """ZIP ダウンロードのディスクキャッシュストア。"""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._downloads_dir = cache_dir / "downloads"

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def cache_path(self, key: str, *, suffix: str = ".zip") -> Path:
        return self._downloads_dir / f"{key}{suffix}"

    def get(self, key: str, *, suffix: str = ".zip") -> bytes | None:
        path = self.cache_path(key, suffix=suffix)
        if not path.exists():
            return None
        try:
            data = path.read_bytes()
            logger.debug("Cache hit: %s (%d bytes)", key, len(data))
            return data
        except OSError:
            logger.warning("Cache read failed: %s", key, exc_info=True)
            return None

    def put(self, key: str, data: bytes, *, suffix: str = ".zip") -> None:
        self._downloads_dir.mkdir(parents=True, exist_ok=True)
        target = self.cache_path(key, suffix=suffix)
        tmp_name: str | None = None
        try:
            fd = tempfile.NamedTemporaryFile(
                dir=self._downloads_dir, delete=False, suffix=".tmp",
            )
            tmp_name = fd.name
            try:
                fd.write(data)
                fd.flush()
            finally:
                fd.close()
            os.replace(tmp_name, target)
            tmp_name = None
            logger.debug("Cache saved: %s (%d bytes)", key, len(data))
        except OSError:
            logger.warning("Cache write failed: %s", key, exc_info=True)
        finally:
            if tmp_name is not None:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass

    def delete(self, key: str, *, suffix: str = ".zip") -> None:
        path = self.cache_path(key, suffix=suffix)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Cache delete failed: %s", key, exc_info=True)

    def clear(self) -> None:
        if self._downloads_dir.exists():
            shutil.rmtree(self._downloads_dir)
            logger.info("Cache cleared: %s", self._downloads_dir)

    def info(self) -> CacheInfo:
        if not self._downloads_dir.exists():
            return CacheInfo(enabled=True, cache_dir=self._cache_dir, entry_count=0, total_bytes=0)
        count = 0
        total = 0
        for f in self._downloads_dir.iterdir():
            if f.is_file() and not f.name.endswith(".tmp"):
                try:
                    total += f.stat().st_size
                    count += 1
                except OSError:
                    pass
        return CacheInfo(enabled=True, cache_dir=self._cache_dir, entry_count=count, total_bytes=total)


def _get_cache_store() -> CacheStore | None:
    from tdnet._config import get_config

    config = get_config()
    if config.cache_dir is None:
        return None
    return CacheStore(Path(config.cache_dir).expanduser())


def clear_cache() -> None:
    """キャッシュを全削除する。"""
    store = _get_cache_store()
    if store is None:
        return
    store.clear()


def cache_info() -> CacheInfo:
    """キャッシュの統計情報を返す。"""
    store = _get_cache_store()
    if store is None:
        return CacheInfo(enabled=False, cache_dir=None, entry_count=0, total_bytes=0)
    return store.info()
