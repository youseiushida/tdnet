"""設定管理のストレステスト。"""

from __future__ import annotations

import pytest

from tdnet._config import _Config, _reset_for_testing, configure, get_config
from tdnet.exceptions import TdnetConfigError


@pytest.fixture(autouse=True)
def _reset_config():
    """各テスト後に設定をリセットする。"""
    yield
    _reset_for_testing()


# ============================================================
# configure
# ============================================================


class TestConfigure:
    """configure() のテスト。"""

    def test_default_config(self):
        """デフォルト設定値の確認。"""
        config = get_config()
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.rate_limit == 1.0
        assert config.taxonomy_path is None
        assert config.cache_dir is None

    def test_update_timeout(self):
        """timeout の更新。"""
        configure(timeout=60.0)
        assert get_config().timeout == 60.0

    def test_update_max_retries(self):
        """max_retries の更新。"""
        configure(max_retries=5)
        assert get_config().max_retries == 5

    def test_update_rate_limit(self):
        """rate_limit の更新。"""
        configure(rate_limit=2.0)
        assert get_config().rate_limit == 2.0

    def test_update_taxonomy_path(self):
        """taxonomy_path の更新。"""
        configure(taxonomy_path="/tmp/taxonomy")
        assert get_config().taxonomy_path == "/tmp/taxonomy"

    def test_clear_taxonomy_path(self):
        """taxonomy_path を None にクリア。"""
        configure(taxonomy_path="/tmp/taxonomy")
        configure(taxonomy_path=None)
        assert get_config().taxonomy_path is None

    def test_update_cache_dir(self):
        """cache_dir の更新。"""
        configure(cache_dir="/tmp/cache")
        assert get_config().cache_dir == "/tmp/cache"

    def test_update_multiple_at_once(self):
        """複数設定を同時に更新。"""
        configure(timeout=10.0, max_retries=2, rate_limit=0.5)
        config = get_config()
        assert config.timeout == 10.0
        assert config.max_retries == 2
        assert config.rate_limit == 0.5


# ============================================================
# バリデーション
# ============================================================


class TestConfigValidation:
    """設定バリデーションのテスト。"""

    def test_timeout_must_be_positive(self):
        """timeout が 0 以下で TdnetConfigError。"""
        with pytest.raises(TdnetConfigError, match="timeout must be positive"):
            configure(timeout=0.0)

    def test_timeout_negative(self):
        """timeout が負で TdnetConfigError。"""
        with pytest.raises(TdnetConfigError, match="timeout must be positive"):
            configure(timeout=-1.0)

    def test_max_retries_must_be_at_least_1(self):
        """max_retries < 1 で TdnetConfigError。"""
        with pytest.raises(TdnetConfigError, match="max_retries must be >= 1"):
            configure(max_retries=0)

    def test_rate_limit_must_be_non_negative(self):
        """rate_limit < 0 で TdnetConfigError。"""
        with pytest.raises(TdnetConfigError, match="rate_limit must be >= 0"):
            configure(rate_limit=-1.0)

    def test_rate_limit_zero_is_ok(self):
        """rate_limit=0 は許可。"""
        configure(rate_limit=0.0)
        assert get_config().rate_limit == 0.0

    def test_base_url_cannot_be_none(self):
        """base_url を None にできない。"""
        with pytest.raises(TdnetConfigError, match="base_url must not be None"):
            configure(base_url=None)  # type: ignore[arg-type]

    def test_yanoshin_base_url_cannot_be_none(self):
        """yanoshin_base_url を None にできない。"""
        with pytest.raises(TdnetConfigError, match="yanoshin_base_url must not be None"):
            configure(yanoshin_base_url=None)  # type: ignore[arg-type]

    def test_timeout_cannot_be_none(self):
        """timeout を None にできない。"""
        with pytest.raises(TdnetConfigError, match="timeout must not be None"):
            configure(timeout=None)  # type: ignore[arg-type]


# ============================================================
# _reset_for_testing
# ============================================================


class TestResetForTesting:
    """テスト用リセットのテスト。"""

    def test_reset_restores_defaults(self):
        """リセットでデフォルト値に戻る。"""
        configure(timeout=99.0, max_retries=10)
        _reset_for_testing()
        config = get_config()
        assert config.timeout == 30.0
        assert config.max_retries == 3
