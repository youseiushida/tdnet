from _typeshed import Incomplete
from dataclasses import dataclass
from pathlib import Path

logger: Incomplete

@dataclass(frozen=True, slots=True)
class CacheInfo:
    enabled: bool
    cache_dir: Path | None
    entry_count: int
    total_bytes: int

class CacheStore:
    """ZIP ダウンロードのディスクキャッシュストア。"""
    def __init__(self, cache_dir: Path) -> None: ...
    @property
    def cache_dir(self) -> Path: ...
    def cache_path(self, key: str, *, suffix: str = '.zip') -> Path: ...
    def get(self, key: str, *, suffix: str = '.zip') -> bytes | None: ...
    def put(self, key: str, data: bytes, *, suffix: str = '.zip') -> None: ...
    def delete(self, key: str, *, suffix: str = '.zip') -> None: ...
    def clear(self) -> None: ...
    def info(self) -> CacheInfo: ...

def clear_cache() -> None:
    """キャッシュを全削除する。"""
def cache_info() -> CacheInfo:
    """キャッシュの統計情報を返す。"""
