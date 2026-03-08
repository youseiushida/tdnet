import httpx
from _typeshed import Incomplete
from dataclasses import dataclass
from tdnet._config import get_config as get_config
from tdnet._version import __version__ as __version__
from tdnet.exceptions import TdnetAPIError as TdnetAPIError, TdnetError as TdnetError
from typing import Any

logger: Incomplete

@dataclass(frozen=True)
class _RetryDecision:
    should_retry: bool
    wait_seconds: float
    exception: TdnetError | None

def invalidate_client() -> None: ...
def get(url: str, params: dict[str, Any] | None = None) -> httpx.Response:
    """GET リクエストを送信する。リトライ・レート制限付き。"""
def post(url: str, data: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
    """POST リクエストを送信する。リトライ・レート制限付き。"""
async def aget(url: str, params: dict[str, Any] | None = None) -> httpx.Response:
    """非同期 GET リクエスト。リトライ・レート制限付き。"""
async def ainvalidate_client() -> None: ...
def invalidate_async_client_sync() -> None: ...
def close() -> None:
    """HTTP クライアントを閉じる。"""
async def aclose() -> None:
    """async HTTP クライアントを閉じる。"""
