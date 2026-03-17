"""adump_to_parquet() のテスト。"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from tdnet.extension import DumpResult, adump_to_parquet, import_parquet
from tdnet.filing import Filing
from tdnet.models.statements import Statements

from tests.helpers import make_item


def _make_filing(
    company_code: str = "7203",
    title: str = "決算短信",
    has_xbrl: bool = True,
) -> Filing:
    """テスト用 Filing を生成する。"""
    xbrl_url = (
        f"https://example.com/tdnet140120250331{company_code}0.zip"
        if has_xbrl
        else ""
    )
    return Filing(
        pubdate="2025-03-31 15:00",
        company_code=company_code,
        company_name="テスト株式会社",
        title=title,
        document_url=f"https://example.com/tdnet140120250331{company_code}0.pdf",
        xbrl_url=xbrl_url,
        markets_string="東証",
    )


def _make_stmts(entity_id: str = "7203") -> Statements:
    """テスト用 Statements を生成する。"""
    return Statements(
        items=(
            make_item("NetSales", Decimal("1000000"), entity_id=entity_id),
            make_item("OperatingIncome", Decimal("200000"), entity_id=entity_id),
        ),
        entity_id=entity_id,
    )


class TestAdumpBasic:
    """adump_to_parquet() の基本動作テスト。"""

    def test_basic_roundtrip(self, tmp_path, monkeypatch):
        """dump → import_parquet で復元できる。"""
        f1 = _make_filing(company_code="7203")
        f2 = _make_filing(company_code="6758")
        s1 = _make_stmts("7203")
        s2 = _make_stmts("6758")

        monkeypatch.setattr(
            "tdnet.documents",
            lambda *_a, **_kw: [f1, f2],
        )

        async def _mock_axbrl(self, **_kw):
            return s1 if self.company_code == "7203" else s2

        monkeypatch.setattr(Filing, "axbrl", _mock_axbrl)

        result = asyncio.run(
            adump_to_parquet(output_dir=tmp_path)
        )

        assert isinstance(result, DumpResult)
        assert result.total_filings == 2
        assert result.xbrl_count == 2
        assert result.xbrl_ok == 2
        assert result.errors == 0
        assert "filings" in result.paths
        assert "line_items" in result.paths

        # import_parquet で復元
        restored = import_parquet(tmp_path)
        assert len(restored) == 2

    def test_result_counts(self, tmp_path, monkeypatch):
        """DumpResult のカウントが正しい。"""
        xbrl_filing = _make_filing(company_code="7203", has_xbrl=True)
        no_xbrl_filing = _make_filing(company_code="9999", has_xbrl=False)

        monkeypatch.setattr(
            "tdnet.documents",
            lambda *_a, **_kw: [xbrl_filing, no_xbrl_filing],
        )

        async def _mock_axbrl(self, **_kw):
            return _make_stmts(self.company_code)

        monkeypatch.setattr(Filing, "axbrl", _mock_axbrl)

        result = asyncio.run(
            adump_to_parquet(output_dir=tmp_path)
        )

        assert result.total_filings == 2
        assert result.xbrl_count == 1
        assert result.xbrl_ok == 1
        assert result.errors == 0

    def test_non_xbrl_only(self, tmp_path, monkeypatch):
        """XBRL なし書類のみ → filings.parquet だけ生成。"""
        f1 = _make_filing(company_code="9999", has_xbrl=False)

        monkeypatch.setattr(
            "tdnet.documents",
            lambda *_a, **_kw: [f1],
        )

        result = asyncio.run(
            adump_to_parquet(output_dir=tmp_path)
        )

        assert result.total_filings == 1
        assert result.xbrl_count == 0
        assert result.xbrl_ok == 0
        assert "filings" in result.paths
        assert "line_items" not in result.paths


class TestAdumpErrorHandling:
    """エラー処理のテスト。"""

    def test_xbrl_error_continues(self, tmp_path, monkeypatch):
        """axbrl エラー時も中断せず続行し、errors カウントが増える。"""
        f1 = _make_filing(company_code="7203")
        f2 = _make_filing(company_code="6758")

        monkeypatch.setattr(
            "tdnet.documents",
            lambda *_a, **_kw: [f1, f2],
        )

        async def _mock_axbrl(self, **_kw):
            if self.company_code == "7203":
                raise RuntimeError("parse error")
            return _make_stmts(self.company_code)

        monkeypatch.setattr(Filing, "axbrl", _mock_axbrl)

        result = asyncio.run(
            adump_to_parquet(output_dir=tmp_path)
        )

        assert result.total_filings == 2
        assert result.xbrl_count == 2
        assert result.xbrl_ok == 1
        assert result.errors == 1

        # エラーの filing も filings.parquet に含まれる
        restored = import_parquet(tmp_path)
        assert len(restored) == 2

        # エラー側は Statements=None で復元される
        by_code = {f.company_code: s for f, s in restored}
        assert by_code["7203"] is None
        assert by_code["6758"] is not None
        assert len(by_code["6758"]) == 2


class TestAdumpSchema:
    """スキーマ・圧縮関連テスト。"""

    def test_explicit_schema_applied(self, tmp_path, monkeypatch):
        """Parquet メタデータで dictionary encoding を検証する。"""
        import pyarrow.parquet as pq

        f1 = _make_filing(company_code="7203")

        monkeypatch.setattr(
            "tdnet.documents",
            lambda *_a, **_kw: [f1],
        )

        async def _mock_axbrl(self, **_kw):
            return _make_stmts(self.company_code)

        monkeypatch.setattr(Filing, "axbrl", _mock_axbrl)

        asyncio.run(adump_to_parquet(output_dir=tmp_path))

        # line_items の namespace_uri は dictionary encoding のはず
        schema = pq.read_schema(tmp_path / "line_items.parquet")
        ns_field = schema.field("namespace_uri")
        assert "dictionary" in str(ns_field.type).lower()

    def test_compression_zstd(self, tmp_path, monkeypatch):
        """デフォルト圧縮が zstd である。"""
        import pyarrow.parquet as pq

        f1 = _make_filing(company_code="7203")

        monkeypatch.setattr(
            "tdnet.documents",
            lambda *_a, **_kw: [f1],
        )

        async def _mock_axbrl(self, **_kw):
            return _make_stmts(self.company_code)

        monkeypatch.setattr(Filing, "axbrl", _mock_axbrl)

        asyncio.run(adump_to_parquet(output_dir=tmp_path))

        meta = pq.read_metadata(tmp_path / "line_items.parquet")
        codec = meta.row_group(0).column(0).compression
        assert codec == "ZSTD"

    def test_prefix(self, tmp_path, monkeypatch):
        """prefix が出力ファイル名に反映される。"""
        f1 = _make_filing(company_code="7203")

        monkeypatch.setattr(
            "tdnet.documents",
            lambda *_a, **_kw: [f1],
        )

        async def _mock_axbrl(self, **_kw):
            return _make_stmts(self.company_code)

        monkeypatch.setattr(Filing, "axbrl", _mock_axbrl)

        asyncio.run(
            adump_to_parquet(output_dir=tmp_path, prefix="2026-03-04_")
        )

        assert (tmp_path / "2026-03-04_filings.parquet").exists()
        assert (tmp_path / "2026-03-04_line_items.parquet").exists()

        # prefix 付きで import できる
        restored = import_parquet(tmp_path, prefix="2026-03-04_")
        assert len(restored) == 1


class TestAdumpRangeQuery:
    """日付範囲クエリのテスト。"""

    def test_start_end_uses_list_by_range(self, tmp_path, monkeypatch):
        """start/end 指定時に list_by_range が呼ばれる。"""
        called_with: dict = {}

        def _mock_list_by_range(start, end, **_kw):
            called_with["start"] = start
            called_with["end"] = end
            return []

        monkeypatch.setattr(
            "tdnet.api.list_by_range",
            _mock_list_by_range,
        )

        result = asyncio.run(
            adump_to_parquet(
                start="20260301", end="20260305",
                output_dir=tmp_path,
            )
        )

        assert called_with["start"] == "20260301"
        assert called_with["end"] == "20260305"
        assert result.total_filings == 0
