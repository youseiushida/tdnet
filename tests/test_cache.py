"""キャッシュストアのストレステスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from tdnet.cache import CacheInfo, CacheStore


@pytest.fixture
def cache_store(tmp_path: Path) -> CacheStore:
    """テスト用キャッシュストアを生成する。"""
    return CacheStore(tmp_path / "tdnet_cache")


# ============================================================
# 基本操作
# ============================================================


class TestCacheStoreBasic:
    """CacheStore の基本操作テスト。"""

    def test_put_and_get(self, cache_store: CacheStore):
        """put → get でデータが取得できる。"""
        data = b"dummy zip data"
        cache_store.put("test_key", data)
        assert cache_store.get("test_key") == data

    def test_get_miss(self, cache_store: CacheStore):
        """存在しないキーは None。"""
        assert cache_store.get("nonexistent") is None

    def test_delete(self, cache_store: CacheStore):
        """delete でキャッシュが削除される。"""
        cache_store.put("to_delete", b"data")
        cache_store.delete("to_delete")
        assert cache_store.get("to_delete") is None

    def test_delete_nonexistent(self, cache_store: CacheStore):
        """存在しないキーの delete はエラーにならない。"""
        cache_store.delete("nonexistent")

    def test_clear(self, cache_store: CacheStore):
        """clear で全キャッシュが削除される。"""
        cache_store.put("key1", b"data1")
        cache_store.put("key2", b"data2")
        cache_store.clear()
        assert cache_store.get("key1") is None
        assert cache_store.get("key2") is None

    def test_cache_path(self, cache_store: CacheStore):
        """cache_path が正しいパスを返す。"""
        path = cache_store.cache_path("my_key")
        assert path.name == "my_key.zip"

    def test_cache_path_custom_suffix(self, cache_store: CacheStore):
        """カスタムサフィックス。"""
        path = cache_store.cache_path("my_key", suffix=".pdf")
        assert path.name == "my_key.pdf"


# ============================================================
# info
# ============================================================


class TestCacheInfo:
    """CacheStore.info() のテスト。"""

    def test_info_empty(self, cache_store: CacheStore):
        """空のキャッシュの info。"""
        info = cache_store.info()
        assert info.enabled is True
        assert info.entry_count == 0
        assert info.total_bytes == 0

    def test_info_with_entries(self, cache_store: CacheStore):
        """エントリがある場合の info。"""
        cache_store.put("key1", b"x" * 100)
        cache_store.put("key2", b"y" * 200)
        info = cache_store.info()
        assert info.entry_count == 2
        assert info.total_bytes == 300

    def test_info_after_clear(self, cache_store: CacheStore):
        """clear 後の info。"""
        cache_store.put("key1", b"data")
        cache_store.clear()
        info = cache_store.info()
        assert info.entry_count == 0


# ============================================================
# エッジケース
# ============================================================


class TestCacheEdgeCases:
    """キャッシュのエッジケーステスト。"""

    def test_overwrite_existing(self, cache_store: CacheStore):
        """同じキーで上書き。"""
        cache_store.put("key", b"old_data")
        cache_store.put("key", b"new_data")
        assert cache_store.get("key") == b"new_data"

    def test_empty_data(self, cache_store: CacheStore):
        """空データの保存。"""
        cache_store.put("empty", b"")
        assert cache_store.get("empty") == b""

    def test_large_data(self, cache_store: CacheStore):
        """大きなデータの保存。"""
        data = b"x" * (10 * 1024 * 1024)  # 10MB
        cache_store.put("large", data)
        assert cache_store.get("large") == data

    def test_special_characters_in_key(self, cache_store: CacheStore):
        """キーに特殊文字。"""
        cache_store.put("key_with-dash_2025", b"data")
        assert cache_store.get("key_with-dash_2025") == b"data"

    def test_multiple_puts_and_gets(self, cache_store: CacheStore):
        """多数のエントリ。"""
        for i in range(100):
            cache_store.put(f"key_{i:03d}", f"data_{i}".encode())
        for i in range(100):
            assert cache_store.get(f"key_{i:03d}") == f"data_{i}".encode()

    def test_clear_on_empty_cache(self, cache_store: CacheStore):
        """空キャッシュの clear はエラーにならない。"""
        cache_store.clear()
