from _typeshed import Incomplete
from datetime import date
from tdnet._config import get_config as get_config
from tdnet._http import aget as aget, get as get, post as post
from tdnet.exceptions import TdnetAPIError as TdnetAPIError, TdnetParseError as TdnetParseError

logger: Incomplete

def list_by_date(target_date: str | date, *, has_xbrl: bool = False, limit: int = 300) -> list[dict]:
    """特定日の開示一覧を取得する。"""
def list_recent(*, has_xbrl: bool = False, limit: int = 300) -> list[dict]:
    """最新の開示一覧を取得する。"""
def list_by_code(code: str | int, *, has_xbrl: bool = False, limit: int = 300) -> list[dict]:
    """証券コードで開示一覧を取得する。"""
def list_by_range(start_date: str | date, end_date: str | date, *, has_xbrl: bool = False, limit: int = 300) -> list[dict]:
    """期間指定で開示一覧を取得する。"""
def download_file(url: str) -> bytes:
    """URL からファイルをダウンロードする。"""
def download_file_with_fallback(url: str, company_code: str) -> tuple[bytes, str]:
    """ファイルをダウンロードする。TDnet で 403/404 の場合は JPX にフォールバックする。

    Args:
        url: ダウンロード URL (release.tdnet.info)。
        company_code: 証券コード (5桁)。

    Returns:
        (ファイルデータ, 実際にダウンロードした URL) のタプル。
    """
async def adownload_file(url: str) -> bytes:
    """非同期でファイルをダウンロードする。"""
async def adownload_file_with_fallback(url: str, company_code: str) -> tuple[bytes, str]:
    """非同期でファイルをダウンロードする。TDnet で 403/404 の場合は JPX にフォールバック。

    Args:
        url: ダウンロード URL (release.tdnet.info)。
        company_code: 証券コード (5桁)。

    Returns:
        (ファイルデータ, 実際にダウンロードした URL) のタプル。
    """
def download_xbrl(url: str) -> bytes:
    """XBRL ZIP をダウンロードする。"""
def download_pdf(url: str) -> bytes:
    """PDF をダウンロードする。"""
def search(*, start_date: str | date, end_date: str | date, keyword: str = '', lang: int = 0) -> list[dict]:
    """TDnet 検索 API でキーワード検索する。"""
