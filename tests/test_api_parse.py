"""API HTML パース機能のストレステスト。"""

from __future__ import annotations

import pytest

from tdnet.api import (
    _build_jpx_url,
    _parse_list_html,
    _parse_search_html,
    download_file_with_fallback,
)
from tdnet.exceptions import TdnetAPIError, TdnetError


# ============================================================
# _parse_list_html
# ============================================================


class TestParseListHtml:
    """一覧ページ HTML パースのテスト。"""

    def test_valid_table(self):
        """正常なテーブルをパースする。"""
        html = """
        <html>
        <body>
        <table id="main-list-table">
        <tr>
            <td>15:00</td>
            <td>7203</td>
            <td>Toyota</td>
            <td><a href="doc.pdf">Earnings</a></td>
            <td><a href="doc.zip">XBRL</a></td>
            <td>TSE</td>
        </tr>
        <tr>
            <td>15:30</td>
            <td>6758</td>
            <td>Sony</td>
            <td><a href="doc2.pdf">Earnings</a></td>
            <td></td>
            <td>TSE</td>
        </tr>
        </table>
        </body>
        </html>
        """
        items = _parse_list_html(html, "20250306")
        assert len(items) == 2
        assert items[0]["company_code"] == "7203"
        assert items[0]["company_name"] == "Toyota"
        assert items[0]["title"] == "Earnings"
        assert "doc.zip" in items[0]["url_xbrl"]
        assert items[0]["pubdate"] == "2025-03-06 15:00:00"
        assert items[1]["company_code"] == "6758"
        assert items[1]["url_xbrl"] == ""

    def test_empty_table(self):
        """テーブルが空の場合。"""
        html = b"""
        <html><body>
        <table id="main-list-table"></table>
        </body></html>
        """
        items = _parse_list_html(html, "20250306")
        assert items == []

    def test_no_table(self):
        """テーブルが存在しない場合。"""
        html = b"<html><body><p>No table</p></body></html>"
        items = _parse_list_html(html, "20250306")
        assert items == []

    def test_too_few_cells_skipped(self):
        """セル数が不足する行はスキップ。"""
        html = b"""
        <html><body>
        <table id="main-list-table">
        <tr><td>Only</td><td>Two</td></tr>
        <tr>
            <td>15:00</td>
            <td>7203</td>
            <td>Test</td>
            <td>Title</td>
            <td></td>
            <td>TSE</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_list_html(html, "20250306")
        assert len(items) == 1

    def test_empty_code_skipped(self):
        """証券コードが空の行はスキップ。"""
        html = b"""
        <html><body>
        <table id="main-list-table">
        <tr>
            <td>15:00</td>
            <td></td>
            <td>Test</td>
            <td>Title</td>
            <td></td>
            <td>TSE</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_list_html(html, "20250306")
        assert items == []

    def test_absolute_url_preserved(self):
        """絶対 URL はそのまま保持される。"""
        html = b"""
        <html><body>
        <table id="main-list-table">
        <tr>
            <td>15:00</td>
            <td>1234</td>
            <td>Test</td>
            <td><a href="https://example.com/doc.pdf">Title</a></td>
            <td><a href="https://example.com/doc.zip">XBRL</a></td>
            <td>TSE</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_list_html(html, "20250306")
        assert items[0]["document_url"] == "https://example.com/doc.pdf"
        assert items[0]["url_xbrl"] == "https://example.com/doc.zip"

    def test_relative_url_has_base(self):
        """相対 URL にベース URL が付加される。"""
        html = b"""
        <html><body>
        <table id="main-list-table">
        <tr>
            <td>15:00</td>
            <td>1234</td>
            <td>Test</td>
            <td><a href="doc.pdf">Title</a></td>
            <td><a href="doc.zip">XBRL</a></td>
            <td>TSE</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_list_html(html, "20250306")
        assert items[0]["document_url"].startswith("https://www.release.tdnet.info")

    def test_string_html_input(self):
        """str 型の HTML 入力。"""
        html = """
        <html><body>
        <table id="main-list-table">
        <tr>
            <td>15:00</td>
            <td>9999</td>
            <td>TestCo</td>
            <td>Title</td>
            <td></td>
            <td>TSE</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_list_html(html, "20250306")
        assert len(items) == 1
        assert items[0]["company_code"] == "9999"

    def test_japanese_content_via_str(self):
        """日本語コンテンツを str で渡す。"""
        html = """
        <html><body>
        <table id="main-list-table">
        <tr>
            <td>15:00</td>
            <td>7203</td>
            <td>トヨタ自動車</td>
            <td><a href="doc.pdf">決算短信</a></td>
            <td><a href="doc.zip">XBRL</a></td>
            <td>東証</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_list_html(html, "20250306")
        assert len(items) == 1
        assert items[0]["company_name"] == "トヨタ自動車"
        assert items[0]["title"] == "決算短信"

    def test_japanese_content_via_encoded_bytes(self):
        """日本語コンテンツを encode した bytes で渡す。"""
        html_str = """
        <html><body>
        <table id="main-list-table">
        <tr>
            <td>15:00</td>
            <td>6758</td>
            <td>ソニー</td>
            <td>決算短信</td>
            <td></td>
            <td>東証</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_list_html(html_str.encode("utf-8"), "20250306")
        assert len(items) == 1
        assert items[0]["company_name"] == "ソニー"


# ============================================================
# _parse_search_html
# ============================================================


class TestParseSearchHtml:
    """検索結果 HTML パースのテスト。"""

    def test_valid_search_result(self):
        """正常な検索結果をパースする。"""
        html = b"""
        <html><body>
        <table id="maintable">
        <tr>
            <td>2025-03-06 15:00</td>
            <td>7203</td>
            <td>Toyota</td>
            <td><a href="/inbs/doc.pdf">Earnings</a></td>
            <td><a href="/inbs/doc.zip">XBRL</a></td>
            <td>TSE</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_search_html(html)
        assert len(items) == 1
        assert items[0]["company_code"] == "7203"
        assert "doc.pdf" in items[0]["document_url"]
        assert "doc.zip" in items[0]["url_xbrl"]

    def test_empty_search_result(self):
        """検索結果が空。"""
        html = b"""
        <html><body>
        <table id="maintable"></table>
        </body></html>
        """
        items = _parse_search_html(html)
        assert items == []

    def test_no_maintable(self):
        """maintable がない場合。"""
        html = b"<html><body></body></html>"
        items = _parse_search_html(html)
        assert items == []

    def test_search_absolute_urls(self):
        """検索結果の絶対 URL。"""
        html = b"""
        <html><body>
        <table id="maintable">
        <tr>
            <td>2025-03-06 15:00</td>
            <td>1234</td>
            <td>Test</td>
            <td><a href="https://example.com/doc.pdf">Title</a></td>
            <td><a href="https://example.com/doc.zip">XBRL</a></td>
            <td>TSE</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_search_html(html)
        assert items[0]["document_url"] == "https://example.com/doc.pdf"

    def test_search_relative_urls(self):
        """検索結果の相対 URL。"""
        html = b"""
        <html><body>
        <table id="maintable">
        <tr>
            <td>2025-03-06 15:00</td>
            <td>1234</td>
            <td>Test</td>
            <td><a href="/inbs/doc.pdf">Title</a></td>
            <td></td>
            <td>TSE</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_search_html(html)
        assert items[0]["document_url"].startswith("https://www.release.tdnet.info")

    def test_search_japanese_via_str(self):
        """日本語の検索結果を str で渡す。"""
        html = """
        <html><body>
        <table id="maintable">
        <tr>
            <td>2025-03-06 15:00</td>
            <td>7203</td>
            <td>トヨタ自動車</td>
            <td><a href="/inbs/doc.pdf">決算短信</a></td>
            <td></td>
            <td>東証</td>
        </tr>
        </table>
        </body></html>
        """
        items = _parse_search_html(html)
        assert len(items) == 1
        assert items[0]["company_name"] == "トヨタ自動車"


# ============================================================
# _build_jpx_url
# ============================================================


class TestBuildJpxUrl:
    """JPX 永続 URL ビルダーのテスト。"""

    def test_basic(self):
        """TDnet URL を JPX URL に変換する。"""
        tdnet = "https://www.release.tdnet.info/inbs/140120260127539586.pdf"
        result = _build_jpx_url(tdnet, "37760")
        assert result == "https://www2.jpx.co.jp/disc/37760/140120260127539586.pdf"

    def test_zip(self):
        """ZIP ファイルでも同様に変換する。"""
        tdnet = "https://www.release.tdnet.info/inbs/081220260128540006.zip"
        result = _build_jpx_url(tdnet, "45520")
        assert result == "https://www2.jpx.co.jp/disc/45520/081220260128540006.zip"


# ============================================================
# download_file_with_fallback
# ============================================================


class TestDownloadFileWithFallback:
    """JPX フォールバック付きダウンロードのテスト。"""

    def test_tdnet_success_no_fallback(self, monkeypatch):
        """TDnet が成功すればフォールバックしない。"""
        import tdnet.api as api_mod

        monkeypatch.setattr(api_mod, "download_file", lambda url: b"ok")

        data, source_url = download_file_with_fallback(
            "https://www.release.tdnet.info/inbs/test.pdf", "12340",
        )
        assert data == b"ok"
        assert source_url == "https://www.release.tdnet.info/inbs/test.pdf"

    def test_fallback_on_404(self, monkeypatch):
        """TDnet 404 で JPX にフォールバックする。"""
        import tdnet.api as api_mod

        call_urls: list[str] = []

        def fake_download(url: str) -> bytes:
            call_urls.append(url)
            if "release.tdnet.info" in url:
                raise TdnetAPIError(404, "Not Found")
            return b"jpx-data"

        monkeypatch.setattr(api_mod, "download_file", fake_download)

        data, source_url = download_file_with_fallback(
            "https://www.release.tdnet.info/inbs/test.pdf", "12340",
        )
        assert data == b"jpx-data"
        assert source_url == "https://www2.jpx.co.jp/disc/12340/test.pdf"
        assert len(call_urls) == 2

    def test_fallback_on_403(self, monkeypatch):
        """TDnet 403 でも JPX にフォールバックする。"""
        import tdnet.api as api_mod

        def fake_download(url: str) -> bytes:
            if "release.tdnet.info" in url:
                raise TdnetAPIError(403, "Forbidden")
            return b"jpx-data"

        monkeypatch.setattr(api_mod, "download_file", fake_download)

        data, source_url = download_file_with_fallback(
            "https://www.release.tdnet.info/inbs/test.pdf", "12340",
        )
        assert data == b"jpx-data"
        assert "jpx.co.jp" in source_url

    def test_no_fallback_on_500(self, monkeypatch):
        """500 エラーはフォールバックせず例外を投げる。"""
        import tdnet.api as api_mod

        monkeypatch.setattr(
            api_mod, "download_file",
            lambda url: (_ for _ in ()).throw(TdnetAPIError(500, "Server Error")),
        )

        with pytest.raises(TdnetAPIError, match="500"):
            download_file_with_fallback(
                "https://www.release.tdnet.info/inbs/test.pdf", "12340",
            )

    def test_jpx_also_fails_raises(self, monkeypatch):
        """JPX もダウンロード失敗なら例外を投げる。"""
        import tdnet.api as api_mod

        def fake_download(url: str) -> bytes:
            if "release.tdnet.info" in url:
                raise TdnetAPIError(404, "Not Found")
            raise TdnetAPIError(404, "JPX Not Found")

        monkeypatch.setattr(api_mod, "download_file", fake_download)

        with pytest.raises(TdnetAPIError, match="JPX Not Found"):
            download_file_with_fallback(
                "https://www.release.tdnet.info/inbs/test.pdf", "12340",
            )
