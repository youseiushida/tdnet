"""TDnet 向け HTTP 通信層。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from random import uniform
from typing import Any

import httpx

from tdnet._config import get_config
from tdnet._version import __version__
from tdnet.exceptions import TdnetAPIError, TdnetError

logger = logging.getLogger(__name__)

_client: httpx.Client | None = None
_last_request_time: float = 0.0

_async_client: httpx.AsyncClient | None = None
_async_last_request_time: float = 0.0
_async_rate_limit_lock: asyncio.Lock | None = None

_USER_AGENT = f"tdnet-python/{__version__}"


# ============================================================
# リトライ判定
# ============================================================

@dataclass(frozen=True)
class _RetryDecision:
    should_retry: bool
    wait_seconds: float
    exception: TdnetError | None


def _backoff_seconds(attempt: int, max_retries: int) -> float:
    if attempt >= max_retries:
        return 0.0
    base_delay = 2 ** (attempt - 1)
    jitter = uniform(0, base_delay * 0.5)
    return base_delay + jitter


def _evaluate_response(
    response: httpx.Response | None,
    *,
    transport_error: httpx.TransportError | None,
    attempt: int,
    max_retries: int,
    url: str,
) -> _RetryDecision:
    is_last = attempt >= max_retries

    if transport_error is not None:
        logger.debug(
            "Transport error %s on %s (attempt %d/%d)",
            type(transport_error).__name__, url, attempt, max_retries,
        )
        exc = TdnetError("Network error")
        if is_last:
            return _RetryDecision(should_retry=False, wait_seconds=0.0, exception=exc)
        return _RetryDecision(
            should_retry=True,
            wait_seconds=_backoff_seconds(attempt, max_retries),
            exception=exc,
        )

    assert response is not None

    if response.status_code == 200:
        return _RetryDecision(should_retry=False, wait_seconds=0.0, exception=None)

    if response.status_code == 429:
        retry_after = _parse_retry_after(response)
        exc = TdnetAPIError(429, "Too Many Requests")
        if is_last:
            return _RetryDecision(should_retry=False, wait_seconds=0.0, exception=exc)
        return _RetryDecision(
            should_retry=True,
            wait_seconds=float(retry_after),
            exception=exc,
        )

    if response.status_code >= 500:
        exc = TdnetAPIError(response.status_code, f"HTTP {response.status_code}")
        if is_last:
            return _RetryDecision(should_retry=False, wait_seconds=0.0, exception=exc)
        return _RetryDecision(
            should_retry=True,
            wait_seconds=_backoff_seconds(attempt, max_retries),
            exception=exc,
        )

    return _RetryDecision(
        should_retry=False,
        wait_seconds=0.0,
        exception=TdnetAPIError(response.status_code, f"HTTP {response.status_code}"),
    )


# ============================================================
# 同期クライアント
# ============================================================

def _get_client() -> httpx.Client:
    global _client
    config = get_config()
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(
                connect=config.timeout,
                read=config.timeout,
                write=config.timeout,
                pool=config.timeout,
            ),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        )
    return _client


def invalidate_client() -> None:
    global _client, _last_request_time
    if _client is not None:
        _client.close()
        _client = None
    _last_request_time = 0.0


def _wait_for_rate_limit() -> None:
    global _last_request_time
    config = get_config()
    now = time.monotonic()
    elapsed = now - _last_request_time
    if _last_request_time > 0 and elapsed < config.rate_limit:
        sleep_time = config.rate_limit - elapsed
        logger.debug("Rate limit: sleeping %.2f seconds", sleep_time)
        time.sleep(sleep_time)


def _record_request_time() -> None:
    global _last_request_time
    _last_request_time = time.monotonic()


def get(url: str, params: dict[str, Any] | None = None) -> httpx.Response:
    """GET リクエストを送信する。リトライ・レート制限付き。"""
    config = get_config()
    client = _get_client()
    last_exception: TdnetError | None = None

    for attempt in range(1, config.max_retries + 1):
        _wait_for_rate_limit()
        _record_request_time()

        response: httpx.Response | None = None
        transport_error: httpx.TransportError | None = None
        try:
            response = client.get(url, params=params)
        except httpx.TransportError as exc:
            transport_error = exc

        decision = _evaluate_response(
            response,
            transport_error=transport_error,
            attempt=attempt,
            max_retries=config.max_retries,
            url=url,
        )

        if not decision.should_retry:
            if decision.exception is not None:
                raise decision.exception
            assert response is not None
            return response

        last_exception = decision.exception
        if decision.wait_seconds > 0:
            time.sleep(decision.wait_seconds)

    raise TdnetError(
        f"Request failed after {config.max_retries} attempts: {last_exception}"
    )


def post(
    url: str,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """POST リクエストを送信する。リトライ・レート制限付き。"""
    config = get_config()
    client = _get_client()
    last_exception: TdnetError | None = None

    for attempt in range(1, config.max_retries + 1):
        _wait_for_rate_limit()
        _record_request_time()

        response: httpx.Response | None = None
        transport_error: httpx.TransportError | None = None
        try:
            response = client.post(url, data=data, headers=headers)
        except httpx.TransportError as exc:
            transport_error = exc

        decision = _evaluate_response(
            response,
            transport_error=transport_error,
            attempt=attempt,
            max_retries=config.max_retries,
            url=url,
        )

        if not decision.should_retry:
            if decision.exception is not None:
                raise decision.exception
            assert response is not None
            return response

        last_exception = decision.exception
        if decision.wait_seconds > 0:
            time.sleep(decision.wait_seconds)

    raise TdnetError(
        f"Request failed after {config.max_retries} attempts: {last_exception}"
    )


def _parse_retry_after(response: httpx.Response) -> int:
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return max(1, int(retry_after))
        except ValueError:
            pass
    return 60


# ============================================================
# async クライアント
# ============================================================

def _get_async_client() -> httpx.AsyncClient:
    global _async_client
    config = get_config()
    if _async_client is None:
        _async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=config.timeout,
                read=config.timeout,
                write=config.timeout,
                pool=config.timeout,
            ),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        )
    return _async_client


def _get_async_rate_limit_lock() -> asyncio.Lock:
    global _async_rate_limit_lock
    if _async_rate_limit_lock is None:
        _async_rate_limit_lock = asyncio.Lock()
    return _async_rate_limit_lock


async def _async_wait_for_rate_limit() -> None:
    global _async_last_request_time
    config = get_config()
    async with _get_async_rate_limit_lock():
        now = time.monotonic()
        elapsed = now - _async_last_request_time
        if _async_last_request_time > 0 and elapsed < config.rate_limit:
            sleep_time = config.rate_limit - elapsed
            await asyncio.sleep(sleep_time)
        _async_last_request_time = time.monotonic()


async def aget(url: str, params: dict[str, Any] | None = None) -> httpx.Response:
    """非同期 GET リクエスト。リトライ・レート制限付き。"""
    config = get_config()
    client = _get_async_client()
    last_exception: TdnetError | None = None

    for attempt in range(1, config.max_retries + 1):
        await _async_wait_for_rate_limit()

        response: httpx.Response | None = None
        transport_error: httpx.TransportError | None = None
        try:
            response = await client.get(url, params=params)
        except httpx.TransportError as exc:
            transport_error = exc

        decision = _evaluate_response(
            response,
            transport_error=transport_error,
            attempt=attempt,
            max_retries=config.max_retries,
            url=url,
        )

        if not decision.should_retry:
            if decision.exception is not None:
                raise decision.exception
            assert response is not None
            return response

        last_exception = decision.exception
        if decision.wait_seconds > 0:
            await asyncio.sleep(decision.wait_seconds)

    raise TdnetError(
        f"Request failed after {config.max_retries} attempts: {last_exception}"
    )


async def ainvalidate_client() -> None:
    global _async_client, _async_last_request_time, _async_rate_limit_lock
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None
    _async_last_request_time = 0.0
    _async_rate_limit_lock = None


def invalidate_async_client_sync() -> None:
    global _async_client, _async_last_request_time, _async_rate_limit_lock
    if _async_client is not None:
        _async_client = None
    _async_last_request_time = 0.0
    _async_rate_limit_lock = None


def close() -> None:
    """HTTP クライアントを閉じる。"""
    invalidate_client()


async def aclose() -> None:
    """async HTTP クライアントを閉じる。"""
    await ainvalidate_client()
