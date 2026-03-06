"""HTTP 通信層のストレステスト（リトライ・レート制限ロジック）。"""

from __future__ import annotations

import pytest
import httpx

from tdnet._http import _RetryDecision, _backoff_seconds, _evaluate_response, _parse_retry_after
from tdnet.exceptions import TdnetAPIError, TdnetError


# ============================================================
# _backoff_seconds
# ============================================================


class TestBackoffSeconds:
    """バックオフ計算のテスト。"""

    def test_first_attempt(self):
        """attempt=1 → 基底 1 秒 + ジッター。"""
        delay = _backoff_seconds(1, 3)
        assert 1.0 <= delay <= 1.5

    def test_second_attempt(self):
        """attempt=2 → 基底 2 秒 + ジッター。"""
        delay = _backoff_seconds(2, 3)
        assert 2.0 <= delay <= 3.0

    def test_last_attempt_returns_zero(self):
        """最終試行 → 0.0。"""
        assert _backoff_seconds(3, 3) == 0.0

    def test_beyond_max_returns_zero(self):
        """max_retries 超過 → 0.0。"""
        assert _backoff_seconds(5, 3) == 0.0


# ============================================================
# _evaluate_response
# ============================================================


class TestEvaluateResponse:
    """レスポンス評価ロジックのテスト。"""

    def _make_response(self, status_code: int, headers: dict | None = None) -> httpx.Response:
        """テスト用レスポンスを生成する。"""
        return httpx.Response(
            status_code=status_code,
            headers=headers or {},
            request=httpx.Request("GET", "https://example.com"),
        )

    def test_200_no_retry(self):
        """200 → リトライなし、例外なし。"""
        resp = self._make_response(200)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is False
        assert decision.exception is None

    def test_429_retries(self):
        """429 → リトライ（最終試行以外）。"""
        resp = self._make_response(429)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is True
        assert isinstance(decision.exception, TdnetAPIError)

    def test_429_last_attempt_no_retry(self):
        """429 最終試行 → リトライなし。"""
        resp = self._make_response(429)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=3, max_retries=3, url="test",
        )
        assert decision.should_retry is False
        assert isinstance(decision.exception, TdnetAPIError)

    def test_500_retries(self):
        """500 → リトライ。"""
        resp = self._make_response(500)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is True

    def test_502_retries(self):
        """502 → リトライ。"""
        resp = self._make_response(502)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is True

    def test_503_retries(self):
        """503 → リトライ。"""
        resp = self._make_response(503)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is True

    def test_400_no_retry(self):
        """400 → リトライなし。"""
        resp = self._make_response(400)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is False
        assert isinstance(decision.exception, TdnetAPIError)

    def test_403_no_retry(self):
        """403 → リトライなし。"""
        resp = self._make_response(403)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is False
        assert isinstance(decision.exception, TdnetAPIError)

    def test_404_no_retry(self):
        """404 → リトライなし。"""
        resp = self._make_response(404)
        decision = _evaluate_response(
            resp, transport_error=None, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is False

    def test_transport_error_retries(self):
        """TransportError → リトライ。"""
        err = httpx.ConnectError("Connection refused")
        decision = _evaluate_response(
            None, transport_error=err, attempt=1, max_retries=3, url="test",
        )
        assert decision.should_retry is True
        assert isinstance(decision.exception, TdnetError)

    def test_transport_error_last_attempt(self):
        """TransportError 最終試行 → リトライなし。"""
        err = httpx.ConnectError("Connection refused")
        decision = _evaluate_response(
            None, transport_error=err, attempt=3, max_retries=3, url="test",
        )
        assert decision.should_retry is False
        assert isinstance(decision.exception, TdnetError)


# ============================================================
# _parse_retry_after
# ============================================================


class TestParseRetryAfter:
    """Retry-After ヘッダーの解析テスト。"""

    def _make_response(self, headers: dict) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            headers=headers,
            request=httpx.Request("GET", "https://example.com"),
        )

    def test_numeric_retry_after(self):
        """数値の Retry-After。"""
        resp = self._make_response({"Retry-After": "30"})
        assert _parse_retry_after(resp) == 30

    def test_retry_after_minimum_1(self):
        """Retry-After=0 → 最小 1。"""
        resp = self._make_response({"Retry-After": "0"})
        assert _parse_retry_after(resp) == 1

    def test_no_retry_after_header(self):
        """ヘッダーなし → 60。"""
        resp = self._make_response({})
        assert _parse_retry_after(resp) == 60

    def test_invalid_retry_after(self):
        """不正な値 → 60。"""
        resp = self._make_response({"Retry-After": "not-a-number"})
        assert _parse_retry_after(resp) == 60
