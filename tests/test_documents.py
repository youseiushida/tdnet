"""documents() のフォールバックテスト。"""

from __future__ import annotations

import pytest

import tdnet
import tdnet.api as api_mod
from tdnet.exceptions import TdnetAPIError, TdnetError


def _yanoshin_items() -> list[dict]:
    """やのしん API が返すダミーデータ。"""
    return [
        {
            "pubdate": "2025-03-06 15:00:00",
            "company_code": "72030",
            "company_name": "テスト",
            "title": "決算短信",
            "document_url": "https://example.com/doc.pdf",
            "url_xbrl": "https://example.com/doc.zip",
            "markets_string": "東証",
        },
    ]


def _scrape_items() -> list[dict]:
    """スクレイピングが返すダミーデータ。"""
    return [
        {
            "pubdate": "2025-03-06 15:30:00",
            "company_code": "67580",
            "company_name": "スクレイプ社",
            "title": "業績予想",
            "document_url": "https://example.com/scrape.pdf",
            "url_xbrl": "https://example.com/scrape.zip",
            "markets_string": "東証",
        },
    ]


class TestDocumentsFallback:
    """documents() のやのしん→スクレイピングフォールバック。"""

    def test_yanoshin_success_no_fallback(self, monkeypatch):
        """やのしん成功時はスクレイピングしない。"""
        monkeypatch.setattr(tdnet, "list_by_date", lambda *a, **kw: _yanoshin_items())
        scrape_called = False

        def fake_scrape(*a, **kw):
            nonlocal scrape_called
            scrape_called = True
            return []

        monkeypatch.setattr(api_mod, "_scrape_list_page", fake_scrape)

        result = tdnet.documents("20250306")
        assert len(result) == 1
        assert result[0].company_code == "72030"
        assert not scrape_called

    def test_fallback_on_network_error(self, monkeypatch):
        """やのしんがネットワークエラーならスクレイピングにフォールバック。"""
        def fail_yanoshin(*a, **kw):
            raise TdnetError("Network error")

        monkeypatch.setattr(tdnet, "list_by_date", fail_yanoshin)
        monkeypatch.setattr(api_mod, "_scrape_list_page", lambda *a, **kw: _scrape_items())

        result = tdnet.documents("20250306")
        assert len(result) == 1
        assert result[0].company_code == "67580"

    def test_fallback_on_500(self, monkeypatch):
        """やのしんが 500 ならスクレイピングにフォールバック。"""
        def fail_yanoshin(*a, **kw):
            raise TdnetAPIError(500, "Server Error")

        monkeypatch.setattr(tdnet, "list_by_date", fail_yanoshin)
        monkeypatch.setattr(api_mod, "_scrape_list_page", lambda *a, **kw: _scrape_items())

        result = tdnet.documents("20250306")
        assert len(result) == 1
        assert result[0].company_code == "67580"

    def test_no_fallback_on_404(self, monkeypatch):
        """やのしんが 404 ならフォールバックせず例外。"""
        def fail_yanoshin(*a, **kw):
            raise TdnetAPIError(404, "Not Found")

        monkeypatch.setattr(tdnet, "list_by_date", fail_yanoshin)

        with pytest.raises(TdnetAPIError, match="404"):
            tdnet.documents("20250306")

    def test_no_fallback_on_403(self, monkeypatch):
        """やのしんが 403 ならフォールバックせず例外。"""
        def fail_yanoshin(*a, **kw):
            raise TdnetAPIError(403, "Forbidden")

        monkeypatch.setattr(tdnet, "list_by_date", fail_yanoshin)

        with pytest.raises(TdnetAPIError, match="403"):
            tdnet.documents("20250306")

    def test_no_fallback_for_code_query(self, monkeypatch):
        """code 指定時はフォールバックせず例外。"""
        def fail_yanoshin(*a, **kw):
            raise TdnetError("Network error")

        monkeypatch.setattr(tdnet, "list_by_code", fail_yanoshin)

        with pytest.raises(TdnetError, match="Network error"):
            tdnet.documents(code="72030")

    def test_fallback_recent(self, monkeypatch):
        """target_date=None (最新) でもフォールバックする。"""
        def fail_yanoshin(*a, **kw):
            raise TdnetError("Network error")

        monkeypatch.setattr(tdnet, "list_recent", fail_yanoshin)
        monkeypatch.setattr(api_mod, "_scrape_list_page", lambda *a, **kw: _scrape_items())

        result = tdnet.documents()
        assert len(result) == 1
        assert result[0].company_code == "67580"

    def test_code_5digit_stripped_to_4digit(self, monkeypatch):
        """5桁コード(チェックディジット付き)は4桁に正規化される。"""
        captured_args: list[str] = []

        def capture_code(code, **kw):
            captured_args.append(code)
            return _yanoshin_items()

        monkeypatch.setattr(tdnet, "list_by_code", capture_code)

        tdnet.documents(code="72030")
        assert captured_args == ["7203"]

    def test_code_4digit_unchanged(self, monkeypatch):
        """4桁コードはそのまま渡される。"""
        captured_args: list[str] = []

        def capture_code(code, **kw):
            captured_args.append(code)
            return _yanoshin_items()

        monkeypatch.setattr(tdnet, "list_by_code", capture_code)

        tdnet.documents(code=7203)
        assert captured_args == ["7203"]

    def test_code_int_5digit_stripped(self, monkeypatch):
        """int型の5桁コードも4桁に正規化される。"""
        captured_args: list[str] = []

        def capture_code(code, **kw):
            captured_args.append(code)
            return _yanoshin_items()

        monkeypatch.setattr(tdnet, "list_by_code", capture_code)

        tdnet.documents(code=72030)
        assert captured_args == ["7203"]

    def test_fallback_filters_has_xbrl(self, monkeypatch):
        """フォールバック時に has_xbrl フィルタが適用される。"""
        def fail_yanoshin(*a, **kw):
            raise TdnetError("Network error")

        items_mixed = [
            {
                "pubdate": "2025-03-06 15:00:00",
                "company_code": "11110",
                "company_name": "XBRL有り",
                "title": "決算短信",
                "document_url": "https://example.com/a.pdf",
                "url_xbrl": "https://example.com/a.zip",
                "markets_string": "",
            },
            {
                "pubdate": "2025-03-06 15:30:00",
                "company_code": "22220",
                "company_name": "XBRL無し",
                "title": "お知らせ",
                "document_url": "https://example.com/b.pdf",
                "url_xbrl": "",
                "markets_string": "",
            },
        ]

        monkeypatch.setattr(tdnet, "list_by_date", fail_yanoshin)
        monkeypatch.setattr(api_mod, "_scrape_list_page", lambda *a, **kw: items_mixed)

        result = tdnet.documents("20250306", has_xbrl=True)
        assert len(result) == 1
        assert result[0].company_code == "11110"
