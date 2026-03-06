"""例外クラスのストレステスト。"""

from __future__ import annotations

import pytest

from tdnet.exceptions import (
    TdnetAPIError,
    TdnetConfigError,
    TdnetError,
    TdnetParseError,
    TdnetWarning,
)


class TestExceptionHierarchy:
    """例外の継承関係テスト。"""

    def test_tdnet_error_is_exception(self):
        assert issubclass(TdnetError, Exception)

    def test_config_error_is_tdnet_error(self):
        assert issubclass(TdnetConfigError, TdnetError)

    def test_api_error_is_tdnet_error(self):
        assert issubclass(TdnetAPIError, TdnetError)

    def test_parse_error_is_tdnet_error(self):
        assert issubclass(TdnetParseError, TdnetError)

    def test_warning_is_user_warning(self):
        assert issubclass(TdnetWarning, UserWarning)


class TestTdnetAPIError:
    """TdnetAPIError のテスト。"""

    def test_status_code(self):
        err = TdnetAPIError(404, "Not Found")
        assert err.status_code == 404

    def test_message_format(self):
        err = TdnetAPIError(500, "Internal Server Error")
        assert "HTTP 500" in str(err)
        assert "Internal Server Error" in str(err)

    def test_catchable_as_tdnet_error(self):
        """TdnetError として捕捉可能。"""
        with pytest.raises(TdnetError):
            raise TdnetAPIError(403, "Forbidden")

    def test_catchable_as_exception(self):
        """Exception として捕捉可能。"""
        with pytest.raises(Exception):
            raise TdnetAPIError(500, "Error")


class TestTdnetParseError:
    """TdnetParseError のテスト。"""

    def test_message(self):
        err = TdnetParseError("Failed to parse JSON")
        assert "Failed to parse JSON" in str(err)

    def test_catchable_as_tdnet_error(self):
        with pytest.raises(TdnetError):
            raise TdnetParseError("parse failed")


class TestTdnetConfigError:
    """TdnetConfigError のテスト。"""

    def test_message(self):
        err = TdnetConfigError("invalid config")
        assert "invalid config" in str(err)
