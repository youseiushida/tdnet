"""tdnet ライブラリのグローバル設定管理。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tdnet.exceptions import TdnetConfigError

_UNSET: Any = object()


@dataclass
class _Config:
    """ライブラリのグローバル設定。直接インスタンス化しない。"""

    base_url: str = "https://www.release.tdnet.info"
    yanoshin_base_url: str = "https://webapi.yanoshin.jp/webapi/tdnet/list"
    timeout: float = 30.0
    max_retries: int = 3
    rate_limit: float = 0.0  # リトライ・指数バックオフで制御、固定スリープ不要
    taxonomy_path: str | None = None
    cache_dir: str | None = None


_global_config = _Config()

_CLIENT_PARAMS = {"base_url", "timeout"}


def configure(
    *,
    taxonomy_path: str | None = _UNSET,
    cache_dir: str | None = _UNSET,
    timeout: float = _UNSET,
    max_retries: int = _UNSET,
    rate_limit: float = _UNSET,
    base_url: str = _UNSET,
    yanoshin_base_url: str = _UNSET,
) -> None:
    """ライブラリのグローバル設定を更新する。"""
    global _global_config
    need_invalidate = False
    updates: dict[str, Any] = {}

    if taxonomy_path is not _UNSET:
        updates["taxonomy_path"] = taxonomy_path
    if cache_dir is not _UNSET:
        updates["cache_dir"] = cache_dir
    if timeout is not _UNSET:
        updates["timeout"] = timeout
    if max_retries is not _UNSET:
        updates["max_retries"] = max_retries
    if rate_limit is not _UNSET:
        updates["rate_limit"] = rate_limit
    if base_url is not _UNSET:
        updates["base_url"] = base_url
    if yanoshin_base_url is not _UNSET:
        updates["yanoshin_base_url"] = yanoshin_base_url

    _NOT_NONE = {"base_url", "yanoshin_base_url", "timeout", "max_retries", "rate_limit"}
    for name in _NOT_NONE:
        if name in updates and updates[name] is None:
            raise TdnetConfigError(
                f"{name} must not be None. "
                f"Only taxonomy_path and cache_dir can be cleared with None."
            )
    if "timeout" in updates and updates["timeout"] <= 0:
        raise TdnetConfigError("timeout must be positive")
    if "max_retries" in updates and updates["max_retries"] < 1:
        raise TdnetConfigError("max_retries must be >= 1")
    if "rate_limit" in updates and updates["rate_limit"] < 0:
        raise TdnetConfigError("rate_limit must be >= 0")

    for name, value in updates.items():
        setattr(_global_config, name, value)
        if name in _CLIENT_PARAMS:
            need_invalidate = True

    if need_invalidate:
        from tdnet._http import invalidate_client, invalidate_async_client_sync

        invalidate_client()
        invalidate_async_client_sync()


def get_config() -> _Config:
    """現在のグローバル設定を返す（内部用）。"""
    return _global_config


def _reset_for_testing() -> None:
    """テスト用: グローバル設定をデフォルトに戻す。"""
    global _global_config
    _global_config = _Config()
