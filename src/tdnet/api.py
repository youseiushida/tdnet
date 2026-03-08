"""TDnet データ取得 API。

やのしんWEB-API 経由のメタデータ取得 + release.tdnet.info からのファイルダウンロード。
"""

from __future__ import annotations

import logging
from datetime import date

from tdnet._config import get_config
from tdnet._http import aget, get, post
from tdnet.exceptions import TdnetAPIError, TdnetParseError

logger = logging.getLogger(__name__)


# ============================================================
# やのしんWEB-API
# ============================================================

def _yanoshin_list(
    condition: str,
    *,
    has_xbrl: bool = False,
    limit: int = 300,
) -> list[dict]:
    """やのしんWEB-API から開示一覧を取得する。

    Args:
        condition: 条件文字列 (e.g. "20260304", "recent", "7203")
        has_xbrl: True の場合 XBRL 付きのみ。
        limit: 最大取得件数。

    Returns:
        items のリスト。
    """
    config = get_config()
    url = f"{config.yanoshin_base_url}/{condition}.json2"
    params: dict[str, str | int] = {"limit": limit}
    if has_xbrl:
        params["hasXBRL"] = 1

    response = get(url, params=params)
    try:
        data = response.json()
    except Exception as exc:
        raise TdnetParseError(
            f"Failed to parse JSON response from {url}: {exc}"
        ) from exc
    return data.get("items", [])


def list_by_date(
    target_date: str | date,
    *,
    has_xbrl: bool = False,
    limit: int = 300,
) -> list[dict]:
    """特定日の開示一覧を取得する。"""
    if isinstance(target_date, date):
        target_date = target_date.strftime("%Y%m%d")
    return _yanoshin_list(target_date, has_xbrl=has_xbrl, limit=limit)


def list_recent(*, has_xbrl: bool = False, limit: int = 300) -> list[dict]:
    """最新の開示一覧を取得する。"""
    return _yanoshin_list("recent", has_xbrl=has_xbrl, limit=limit)


def list_by_code(
    code: str | int,
    *,
    has_xbrl: bool = False,
    limit: int = 300,
) -> list[dict]:
    """証券コードで開示一覧を取得する。"""
    return _yanoshin_list(str(code), has_xbrl=has_xbrl, limit=limit)


def list_by_range(
    start_date: str | date,
    end_date: str | date,
    *,
    has_xbrl: bool = False,
    limit: int = 300,
) -> list[dict]:
    """期間指定で開示一覧を取得する。"""
    if isinstance(start_date, date):
        start_date = start_date.strftime("%Y%m%d")
    if isinstance(end_date, date):
        end_date = end_date.strftime("%Y%m%d")
    return _yanoshin_list(f"{start_date}-{end_date}", has_xbrl=has_xbrl, limit=limit)


# ============================================================
# release.tdnet.info スクレイピング
# ============================================================

_BASE_URL = "https://www.release.tdnet.info"


def _scrape_list_page(target_date: str | date, page: int = 1) -> list[dict]:
    """日付別一覧ページをスクレイピングする。"""
    if isinstance(target_date, date):
        target_date = target_date.strftime("%Y%m%d")

    url = f"{_BASE_URL}/inbs/I_list_{page:03d}_{target_date}.html"
    response = get(url)
    return _parse_list_html(response.content, target_date)


def _parse_list_html(html: str | bytes, date_str: str) -> list[dict]:
    """一覧ページ HTML をパースする。"""
    from lxml import etree

    try:
        raw = html if isinstance(html, bytes) else html.encode("utf-8")
        parser = etree.HTMLParser(encoding="utf-8")
        doc = etree.HTML(raw, parser=parser)
    except Exception as exc:
        raise TdnetParseError(f"Failed to parse HTML: {exc}") from exc

    rows = doc.xpath('//table[@id="main-list-table"]//tr')
    items: list[dict] = []

    for row in rows:
        cells = row.xpath('.//td')
        if len(cells) < 6:
            continue

        time_text = _text(cells[0]).strip()
        code = _text(cells[1]).strip()
        name = _text(cells[2]).strip()

        # タイトルとPDFリンク
        title_cell = cells[3]
        title = _text(title_cell).strip()
        pdf_links = title_cell.xpath('.//a/@href')
        pdf_url = ""
        if pdf_links:
            href = pdf_links[0]
            if not href.startswith("http"):
                pdf_url = f"{_BASE_URL}/inbs/{href}"
            else:
                pdf_url = href

        # XBRL リンク
        xbrl_cell = cells[4]
        xbrl_links = xbrl_cell.xpath('.//a/@href')
        xbrl_url = ""
        if xbrl_links:
            href = xbrl_links[0]
            if not href.startswith("http"):
                xbrl_url = f"{_BASE_URL}/inbs/{href}"
            else:
                xbrl_url = href

        exchange = _text(cells[5]).strip() if len(cells) > 5 else ""

        if not code:
            continue

        items.append({
            "pubdate": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_text}:00",
            "company_code": code,
            "company_name": name,
            "title": title,
            "document_url": pdf_url,
            "url_xbrl": xbrl_url,
            "markets_string": exchange,
        })

    return items


def _text(element) -> str:
    """lxml element のテキストコンテンツを取得する。"""
    return "".join(element.itertext())


# ============================================================
# ファイルダウンロード
# ============================================================

_JPX_BASE_URL = "https://www2.jpx.co.jp/disc"


def _build_jpx_url(tdnet_url: str, company_code: str) -> str:
    """release.tdnet.info の URL を JPX 永続 URL に変換する。

    Args:
        tdnet_url: release.tdnet.info のファイル URL。
        company_code: 証券コード (5桁)。

    Returns:
        JPX の永続 URL。
    """
    filename = tdnet_url.rsplit("/", 1)[-1]
    return f"{_JPX_BASE_URL}/{company_code}/{filename}"


def download_file(url: str) -> bytes:
    """URL からファイルをダウンロードする。"""
    response = get(url)
    return response.content


def download_file_with_fallback(
    url: str,
    company_code: str,
) -> tuple[bytes, str]:
    """ファイルをダウンロードする。TDnet で 403/404 の場合は JPX にフォールバックする。

    Args:
        url: ダウンロード URL (release.tdnet.info)。
        company_code: 証券コード (5桁)。

    Returns:
        (ファイルデータ, 実際にダウンロードした URL) のタプル。
    """
    try:
        data = download_file(url)
        return data, url
    except TdnetAPIError as exc:
        if exc.status_code not in (403, 404):
            raise
        status_code = exc.status_code

    jpx_url = _build_jpx_url(url, company_code)
    logger.info("TDnet %d, JPX にフォールバック: %s", status_code, jpx_url)
    data = download_file(jpx_url)
    return data, jpx_url


async def adownload_file(url: str) -> bytes:
    """非同期でファイルをダウンロードする。"""
    response = await aget(url)
    return response.content


async def adownload_file_with_fallback(
    url: str,
    company_code: str,
) -> tuple[bytes, str]:
    """非同期でファイルをダウンロードする。TDnet で 403/404 の場合は JPX にフォールバック。

    Args:
        url: ダウンロード URL (release.tdnet.info)。
        company_code: 証券コード (5桁)。

    Returns:
        (ファイルデータ, 実際にダウンロードした URL) のタプル。
    """
    try:
        data = await adownload_file(url)
        return data, url
    except TdnetAPIError as exc:
        if exc.status_code not in (403, 404):
            raise
        status_code = exc.status_code

    jpx_url = _build_jpx_url(url, company_code)
    logger.info("TDnet %d, JPX にフォールバック: %s", status_code, jpx_url)
    data = await adownload_file(jpx_url)
    return data, jpx_url


def download_xbrl(url: str) -> bytes:
    """XBRL ZIP をダウンロードする。"""
    return download_file(url)


def download_pdf(url: str) -> bytes:
    """PDF をダウンロードする。"""
    return download_file(url)


# ============================================================
# TDnet 検索
# ============================================================

def search(
    *,
    start_date: str | date,
    end_date: str | date,
    keyword: str = "",
    lang: int = 0,
) -> list[dict]:
    """TDnet 検索 API でキーワード検索する。"""
    if isinstance(start_date, date):
        start_date = start_date.strftime("%Y%m%d")
    if isinstance(end_date, date):
        end_date = end_date.strftime("%Y%m%d")

    url = f"{_BASE_URL}/onsf/TDJFSearch/TDJFSearch"
    data = {"t0": start_date, "t1": end_date, "q": keyword, "m": str(lang)}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = post(url, data=data, headers=headers)
    return _parse_search_html(response.content)


def _parse_search_html(html: str | bytes) -> list[dict]:
    """検索結果 HTML をパースする。"""
    from lxml import etree

    try:
        raw = html if isinstance(html, bytes) else html.encode("utf-8")
        parser = etree.HTMLParser(encoding="utf-8")
        doc = etree.HTML(raw, parser=parser)
    except Exception as exc:
        raise TdnetParseError(f"Failed to parse search HTML: {exc}") from exc

    rows = doc.xpath('//table[@id="maintable"]//tr')
    items: list[dict] = []

    for row in rows:
        cells = row.xpath('.//td')
        if len(cells) < 6:
            continue

        datetime_text = _text(cells[0]).strip()
        code = _text(cells[1]).strip()
        name = _text(cells[2]).strip()

        title_cell = cells[3]
        title = _text(title_cell).strip()
        pdf_links = title_cell.xpath('.//a/@href')
        pdf_url = ""
        if pdf_links:
            href = pdf_links[0]
            if not href.startswith("http"):
                pdf_url = f"{_BASE_URL}{href}"
            else:
                pdf_url = href

        xbrl_cell = cells[4]
        xbrl_links = xbrl_cell.xpath('.//a/@href')
        xbrl_url = ""
        if xbrl_links:
            href = xbrl_links[0]
            if not href.startswith("http"):
                xbrl_url = f"{_BASE_URL}{href}"
            else:
                xbrl_url = href

        exchange = _text(cells[5]).strip() if len(cells) > 5 else ""

        if not code:
            continue

        items.append({
            "pubdate": datetime_text,
            "company_code": code,
            "company_name": name,
            "title": title,
            "document_url": pdf_url,
            "url_xbrl": xbrl_url,
            "markets_string": exchange,
        })

    return items
