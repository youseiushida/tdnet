"""Filing クラスのストレステスト。"""

from __future__ import annotations

import pytest

from tdnet.exceptions import TdnetAPIError, TdnetError
from tdnet.filing import DownloadResult, Filing


def _sample_filing(**overrides) -> Filing:
    """テスト用 Filing を生成する。"""
    defaults = {
        "pubdate": "2025-03-06 15:00:00",
        "company_code": "72030",
        "company_name": "テスト株式会社",
        "title": "2025年3月期 決算短信",
        "document_url": "https://www.release.tdnet.info/inbs/140120250306553722.pdf",
        "xbrl_url": "https://www.release.tdnet.info/inbs/140120250306553722.zip",
        "markets_string": "東証プライム",
    }
    defaults.update(overrides)
    return Filing(**defaults)


# ============================================================
# DownloadResult
# ============================================================


class TestDownloadResult:
    """DownloadResult のテスト。"""

    def test_basic(self):
        """基本的なフィールドアクセス。"""
        result = DownloadResult(data=b"hello", source_url="https://example.com/f.pdf")
        assert result.data == b"hello"
        assert result.source_url == "https://example.com/f.pdf"

    def test_frozen(self):
        """frozen なので変更不可。"""
        result = DownloadResult(data=b"x", source_url="url")
        with pytest.raises(AttributeError):
            result.data = b"y"  # type: ignore[misc]


# ============================================================
# Filing 基本プロパティ
# ============================================================


class TestFilingProperties:
    """Filing の基本プロパティのテスト。"""

    def test_has_xbrl_true(self):
        """xbrl_url が存在する場合 True。"""
        filing = _sample_filing()
        assert filing.has_xbrl is True

    def test_has_xbrl_false(self):
        """xbrl_url が空の場合 False。"""
        filing = _sample_filing(xbrl_url="")
        assert filing.has_xbrl is False

    def test_doc_id_from_url(self):
        """URL から doc_id を抽出。"""
        filing = _sample_filing()
        doc_id = filing.doc_id
        assert doc_id == "553722"

    def test_doc_id_short_url(self):
        """短い URL の doc_id。"""
        filing = _sample_filing(
            document_url="https://example.com/short.pdf",
            xbrl_url="",
        )
        # stem = "short", len < 18 → stem そのまま
        assert filing.doc_id == "short"

    def test_doc_id_no_url(self):
        """URL がない場合は空文字。"""
        filing = _sample_filing(document_url="", xbrl_url="")
        assert filing.doc_id == ""

    def test_frozen_dataclass(self):
        """frozen dataclass なので変更不可。"""
        filing = _sample_filing()
        with pytest.raises(AttributeError):
            filing.title = "変更"  # type: ignore[misc]

    def test_cache_key(self):
        """_cache_key がファイル名のステムを返す。"""
        filing = _sample_filing()
        key = filing._cache_key()
        assert key == "140120250306553722"


# ============================================================
# from_yanoshin
# ============================================================


class TestFromYanoshin:
    """from_yanoshin のテスト。"""

    def test_basic_conversion(self):
        """やのしんAPIレスポンスから Filing を生成。"""
        item = {
            "pubdate": "2025-03-06 15:00:00",
            "company_code": "72030",
            "company_name": "テスト",
            "title": "決算短信",
            "document_url": "https://example.com/doc.pdf",
            "url_xbrl": "https://example.com/doc.zip",
            "markets_string": "東証",
        }
        filing = Filing.from_yanoshin(item)
        assert filing.company_code == "72030"
        assert filing.xbrl_url == "https://example.com/doc.zip"

    def test_missing_fields_default_to_empty(self):
        """フィールドが欠損している場合は空文字。"""
        filing = Filing.from_yanoshin({})
        assert filing.pubdate == ""
        assert filing.company_code == ""
        assert filing.xbrl_url == ""

    def test_extra_fields_ignored(self):
        """未知のフィールドは無視される。"""
        item = {
            "pubdate": "2025-01-01",
            "company_code": "12340",
            "company_name": "Test",
            "title": "Title",
            "document_url": "",
            "url_xbrl": "",
            "markets_string": "",
            "extra_field": "should be ignored",
        }
        filing = Filing.from_yanoshin(item)
        assert filing.company_code == "12340"


# ============================================================
# from_scrape
# ============================================================


class TestFromScrape:
    """from_scrape のテスト。"""

    def test_basic_conversion(self):
        """スクレイピング結果から Filing を生成。"""
        item = {
            "pubdate": "2025-03-06 15:00:00",
            "company_code": "72030",
            "company_name": "テスト",
            "title": "決算短信",
            "document_url": "https://example.com/doc.pdf",
            "url_xbrl": "https://example.com/doc.zip",
            "markets_string": "東証",
        }
        filing = Filing.from_scrape(item)
        assert filing.company_code == "72030"
        assert filing.xbrl_url == "https://example.com/doc.zip"


# ============================================================
# fetch_xbrl
# ============================================================


class TestFetchXbrl:
    """fetch_xbrl のテスト。"""

    def test_no_xbrl_url_raises(self):
        """xbrl_url が空の場合 TdnetError。"""
        filing = _sample_filing(xbrl_url="")
        with pytest.raises(TdnetError, match="no XBRL"):
            filing.fetch_xbrl()

    def test_returns_download_result(self, monkeypatch):
        """正常時は DownloadResult を返す。"""
        import tdnet.api as api_mod

        monkeypatch.setattr(
            api_mod, "download_file", lambda url: b"zip-data",
        )
        monkeypatch.setattr(
            "tdnet.filing._get_cache_store", lambda: None,
        )

        filing = _sample_filing()
        result = filing.fetch_xbrl()

        assert isinstance(result, DownloadResult)
        assert result.data == b"zip-data"
        assert result.source_url == filing.xbrl_url

    def test_jpx_fallback_on_404(self, monkeypatch):
        """TDnet 404 で JPX にフォールバックし source_url が JPX になる。"""
        import tdnet.api as api_mod

        def fake_download(url: str) -> bytes:
            if "release.tdnet.info" in url:
                raise TdnetAPIError(404, "Not Found")
            return b"jpx-zip"

        monkeypatch.setattr(api_mod, "download_file", fake_download)
        monkeypatch.setattr(
            "tdnet.filing._get_cache_store", lambda: None,
        )

        filing = _sample_filing()
        result = filing.fetch_xbrl()

        assert result.data == b"jpx-zip"
        assert "jpx.co.jp" in result.source_url
        assert "72030" in result.source_url


# ============================================================
# fetch_pdf
# ============================================================


class TestFetchPdf:
    """fetch_pdf のテスト。"""

    def test_no_document_url_raises(self):
        """document_url が空の場合 TdnetError。"""
        filing = _sample_filing(document_url="", xbrl_url="")
        with pytest.raises(TdnetError, match="no PDF URL"):
            filing.fetch_pdf()

    def test_returns_download_result_with_pdf(self, monkeypatch):
        """PDF データの場合 DownloadResult を返す。"""
        import tdnet.api as api_mod

        monkeypatch.setattr(
            api_mod, "download_file", lambda url: b"%PDF-1.4 content",
        )

        filing = _sample_filing()
        result = filing.fetch_pdf()

        assert isinstance(result, DownloadResult)
        assert result.data == b"%PDF-1.4 content"
        assert result.source_url == filing.document_url

    def test_jpx_fallback_on_404(self, monkeypatch):
        """TDnet 404 で JPX にフォールバックする。"""
        import tdnet.api as api_mod

        def fake_download(url: str) -> bytes:
            if "release.tdnet.info" in url:
                raise TdnetAPIError(404, "Not Found")
            return b"%PDF-1.4 jpx"

        monkeypatch.setattr(api_mod, "download_file", fake_download)

        filing = _sample_filing()
        result = filing.fetch_pdf()

        assert result.data == b"%PDF-1.4 jpx"
        assert "jpx.co.jp" in result.source_url
