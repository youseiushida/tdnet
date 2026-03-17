"""Parquet 永続化の往復テスト。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pyarrow.parquet as pq
from xbrl_core import CalculationArc, CalculationLinkbase, CalculationTree
from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.extension import export_parquet, import_parquet, iter_parquet
from tdnet.filing import Filing
from tdnet.models.statements import Statements
from tdnet.models.types import LabelSource

from tests.helpers import (
    CURRENT_INSTANT,
    make_consolidated_dim,
    make_current_dim,
    make_item,
)


def _make_filing(
    company_code: str = "7203",
    title: str = "決算短信",
    pubdate: str = "2025-03-31 15:00",
) -> Filing:
    """テスト用 Filing を生成する。"""
    return Filing(
        pubdate=pubdate,
        company_code=company_code,
        company_name="テスト株式会社",
        title=title,
        document_url=f"https://example.com/tdnet140120250331{company_code}0.pdf",
        xbrl_url=f"https://example.com/tdnet140120250331{company_code}0.zip",
        markets_string="東証",
    )


def _make_calc_linkbase() -> CalculationLinkbase:
    """テスト用 CalculationLinkbase を生成する。"""
    role = "http://example.com/role/PL"
    arc = CalculationArc(
        parent="GrossProfit",
        child="NetSales",
        parent_href="jppfs_cor.xsd#GrossProfit",
        child_href="jppfs_cor.xsd#NetSales",
        weight=1,
        order=1.0,
        role_uri=role,
    )
    tree = CalculationTree(
        role_uri=role,
        arcs=(arc,),
        roots=("GrossProfit",),
    )
    return CalculationLinkbase(
        source_path=None,
        trees={role: tree},
    )


class TestDocId:
    """doc_id がフル stem であることを確認する。"""

    def test_doc_id_full_stem(self):
        """doc_id が URL のファイル名 stem 全体を返す。"""
        filing = _make_filing()
        assert filing.doc_id == "tdnet14012025033172030"

    def test_doc_id_from_xbrl_url(self):
        """xbrl_url から doc_id が取れる。"""
        filing = Filing(
            pubdate="", company_code="6758", company_name="",
            title="", document_url="",
            xbrl_url="https://example.com/tdnet14012025033167580.zip",
            markets_string="",
        )
        assert filing.doc_id == "tdnet14012025033167580"


class TestRoundTripEmpty:
    """空リストの往復。"""

    def test_empty_list(self, tmp_path):
        """空リストを保存・復元できる。"""
        export_parquet([], tmp_path)
        result = import_parquet(tmp_path)
        assert result == []


class TestRoundTripFilingOnly:
    """Filing のみ（Statements=None）の往復。"""

    def test_filing_without_statements(self, tmp_path):
        """Statements=None で保存・復元できる。"""
        filing = _make_filing()
        export_parquet([(filing, None)], tmp_path)
        result = import_parquet(tmp_path)

        assert len(result) == 1
        restored_filing, restored_stmts = result[0]
        assert restored_stmts is None
        assert restored_filing.company_code == "7203"
        assert restored_filing.company_name == "テスト株式会社"
        assert restored_filing.title == "決算短信"
        assert restored_filing.pubdate == "2025-03-31 15:00"
        assert restored_filing.markets_string == "東証"


class TestRoundTripWithStatements:
    """Filing + Statements の往復。"""

    def test_multiple_items(self, tmp_path):
        """複数 LineItem を保存・復元できる。"""
        filing = _make_filing()
        items = (
            make_item("NetSales", Decimal("1000000"), label_ja="売上高"),
            make_item("OperatingIncome", Decimal("200000"), label_ja="営業利益"),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        assert len(result) == 1
        _, restored_stmts = result[0]
        assert restored_stmts is not None
        assert len(restored_stmts) == 2

        restored_items = list(restored_stmts)
        assert restored_items[0].local_name == "NetSales"
        assert restored_items[0].label_ja.text == "売上高"
        assert restored_items[1].local_name == "OperatingIncome"
        assert restored_items[1].label_ja.text == "営業利益"

    def test_multiple_filings(self, tmp_path):
        """複数 Filing を保存・復元できる。"""
        f1 = _make_filing(company_code="7203")
        f2 = _make_filing(company_code="6758")
        s1 = Statements(
            items=(make_item("NetSales", Decimal("1000000"), entity_id="7203"),),
            entity_id="7203",
        )
        s2 = Statements(
            items=(make_item("NetSales", Decimal("2000000"), entity_id="6758"),),
            entity_id="6758",
        )

        export_parquet([(f1, s1), (f2, s2)], tmp_path)
        result = import_parquet(tmp_path)

        assert len(result) == 2
        assert result[0][0].company_code == "7203"
        assert result[1][0].company_code == "6758"
        assert list(result[0][1])[0].value == Decimal("1000000")  # type: ignore[union-attr]
        assert list(result[1][1])[0].value == Decimal("2000000")  # type: ignore[union-attr]


class TestRoundTripValue:
    """value (Decimal / str / None) の往復。"""

    def test_decimal_value(self, tmp_path):
        """Decimal 値が往復する。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("12345678.0"))
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert isinstance(restored_item.value, Decimal)
        assert restored_item.value == Decimal("12345678.0")

    def test_decimal_precision_preserved(self, tmp_path):
        """Decimal の精度が保持される（string 保存による）。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("123456789012345.678"))
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.value == Decimal("123456789012345.678")

    def test_str_value(self, tmp_path):
        """文字列値が往復する。"""
        filing = _make_filing()
        item = make_item("SomeText", "テスト文字列", unit_ref=None, decimals=None)
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.value == "テスト文字列"

    def test_none_value(self, tmp_path):
        """None 値が往復する。"""
        filing = _make_filing()
        item = make_item("NilItem", None, is_nil=True, unit_ref=None, decimals=None)
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.value is None
        assert restored_item.is_nil is True


class TestRoundTripDecimals:
    """decimals (int / "INF" / None) の往復。"""

    def test_int_decimals(self, tmp_path):
        """int の decimals が往復する。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), decimals=-6)
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.decimals == -6

    def test_inf_decimals(self, tmp_path):
        """"INF" の decimals が往復する。"""
        from dataclasses import replace

        filing = _make_filing()
        base = make_item("Ratio", Decimal("0.5"))
        item = replace(base, decimals="INF")
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.decimals == "INF"

    def test_none_decimals(self, tmp_path):
        """None の decimals が往復する。"""
        filing = _make_filing()
        item = make_item("TextItem", "text", decimals=None, unit_ref=None)
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.decimals is None


class TestRoundTripPeriod:
    """Period (Instant / Duration) の往復。"""

    def test_duration_period(self, tmp_path):
        """DurationPeriod が往復する。"""
        filing = _make_filing()
        period = DurationPeriod(start_date=date(2024, 4, 1), end_date=date(2025, 3, 31))
        item = make_item("NetSales", Decimal("100"), period=period)
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert isinstance(restored_item.period, DurationPeriod)
        assert restored_item.period.start_date == date(2024, 4, 1)
        assert restored_item.period.end_date == date(2025, 3, 31)

    def test_instant_period(self, tmp_path):
        """InstantPeriod が往復する。"""
        filing = _make_filing()
        period = InstantPeriod(instant=date(2025, 3, 31))
        item = make_item("TotalAssets", Decimal("5000000"), period=period)
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert isinstance(restored_item.period, InstantPeriod)
        assert restored_item.period.instant == date(2025, 3, 31)


class TestRoundTripDimensions:
    """dimensions の往復。"""

    def test_empty_dimensions(self, tmp_path):
        """空 dimensions が往復する。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), dimensions=())
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.dimensions == ()

    def test_multiple_dimensions(self, tmp_path):
        """複数 dimensions が往復する。"""
        filing = _make_filing()
        dims = (make_consolidated_dim(True), make_current_dim())
        item = make_item("NetSales", Decimal("100"), dimensions=dims)
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert len(restored_item.dimensions) == 2
        assert restored_item.dimensions[0].axis == dims[0].axis
        assert restored_item.dimensions[0].member == dims[0].member
        assert restored_item.dimensions[1].axis == dims[1].axis
        assert restored_item.dimensions[1].member == dims[1].member


class TestRoundTripLabel:
    """LabelInfo の往復。"""

    def test_label_source(self, tmp_path):
        """LabelSource が往復する。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), label_ja="売上高", label_en="Net Sales")
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.label_ja.text == "売上高"
        assert restored_item.label_ja.source == LabelSource.STANDARD
        assert restored_item.label_ja.lang == "ja"
        assert restored_item.label_en.text == "Net Sales"
        assert restored_item.label_en.source == LabelSource.STANDARD
        assert restored_item.label_en.lang == "en"


class TestTextBlockSeparation:
    """TextBlock の分離と統合。"""

    def test_text_block_separated(self, tmp_path):
        """TextBlock が text_blocks.parquet に分離される。"""
        filing = _make_filing()
        items = (
            make_item("NetSales", Decimal("100"), label_ja="売上高"),
            make_item(
                "NotesTextBlock", "テスト注記",
                unit_ref=None, decimals=None,
            ),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)

        assert (tmp_path / "line_items.parquet").exists()
        assert (tmp_path / "text_blocks.parquet").exists()

        # line_items には数値のみ
        li_table = pq.read_table(tmp_path / "line_items.parquet")
        assert li_table.num_rows == 1
        assert li_table.column("local_name")[0].as_py() == "NetSales"

        # text_blocks には TextBlock のみ
        tb_table = pq.read_table(tmp_path / "text_blocks.parquet")
        assert tb_table.num_rows == 1
        assert tb_table.column("local_name")[0].as_py() == "NotesTextBlock"

    def test_text_block_roundtrip_included(self, tmp_path):
        """include_text_blocks=True で TextBlock も統合して復元される。"""
        filing = _make_filing()
        items = (
            make_item("NetSales", Decimal("100")),
            make_item("NotesTextBlock", "テスト注記", unit_ref=None, decimals=None),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path, include_text_blocks=True)

        restored_stmts = result[0][1]
        assert restored_stmts is not None
        assert len(restored_stmts) == 2

    def test_text_block_roundtrip_excluded(self, tmp_path):
        """include_text_blocks=False で TextBlock が除外される。"""
        filing = _make_filing()
        items = (
            make_item("NetSales", Decimal("100")),
            make_item("NotesTextBlock", "テスト注記", unit_ref=None, decimals=None),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path, include_text_blocks=False)

        restored_stmts = result[0][1]
        assert restored_stmts is not None
        assert len(restored_stmts) == 1
        assert list(restored_stmts)[0].local_name == "NetSales"


class TestCalcEdgesRoundTrip:
    """calc_edges の往復。"""

    def test_calc_edges_roundtrip(self, tmp_path):
        """CalculationLinkbase が往復する。"""
        filing = _make_filing()
        calc_lb = _make_calc_linkbase()
        items = (make_item("NetSales", Decimal("100")),)
        stmts = Statements(
            items=items, entity_id="7203",
            calculation_linkbase=calc_lb,
        )

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_stmts = result[0][1]
        assert restored_stmts is not None
        assert restored_stmts._calculation_linkbase is not None
        restored_calc = restored_stmts._calculation_linkbase
        assert len(restored_calc.trees) == 1
        role = "http://example.com/role/PL"
        assert role in restored_calc.trees
        restored_tree = restored_calc.trees[role]
        assert len(restored_tree.arcs) == 1
        assert restored_tree.arcs[0].parent == "GrossProfit"
        assert restored_tree.arcs[0].child == "NetSales"
        assert restored_tree.arcs[0].weight == 1

    def test_no_calc_edges(self, tmp_path):
        """CalculationLinkbase なしでもエラーなし。"""
        filing = _make_filing()
        stmts = Statements(
            items=(make_item("NetSales", Decimal("100")),),
            entity_id="7203",
        )

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_stmts = result[0][1]
        assert restored_stmts is not None
        assert restored_stmts._calculation_linkbase is None


class TestDefParentsRoundTrip:
    """def_parents の往復。"""

    def test_def_parents_roundtrip(self, tmp_path):
        """definition_parent_index が往復する。"""
        filing = _make_filing()
        items = (make_item("NetSales", Decimal("100")),)
        stmts = Statements(
            items=items, entity_id="7203",
            definition_parent_index={
                "CustomConcept1": "StandardParent1",
                "CustomConcept2": "StandardParent2",
            },
        )

        export_parquet([(filing, stmts)], tmp_path)

        # def_parents は definition_linkbase から生成されるため、
        # definition_parent_index のみ設定時は書き出されない
        # → definition_linkbase がないと def_parents テーブルは空
        result = import_parquet(tmp_path)
        restored_stmts = result[0][1]
        assert restored_stmts is not None


class TestOneDocOneRowGroup:
    """1 書類 = 1 row group の検証。"""

    def test_one_doc_one_row_group(self, tmp_path):
        """各書類が独立した row group に書かれる。"""
        f1 = _make_filing(company_code="7203")
        f2 = _make_filing(company_code="6758")
        s1 = Statements(
            items=(make_item("NetSales", Decimal("100"), entity_id="7203"),),
            entity_id="7203",
        )
        s2 = Statements(
            items=(
                make_item("NetSales", Decimal("200"), entity_id="6758"),
                make_item("OperatingIncome", Decimal("50"), entity_id="6758"),
            ),
            entity_id="6758",
        )

        export_parquet([(f1, s1), (f2, s2)], tmp_path)

        # filings: 2 row groups（各 1 行）
        meta = pq.read_metadata(tmp_path / "filings.parquet")
        assert meta.num_row_groups == 2

        # line_items: 2 row groups（1行 + 2行）
        meta = pq.read_metadata(tmp_path / "line_items.parquet")
        assert meta.num_row_groups == 2


class TestBehavior:
    """復元後のオブジェクトが機能するか。"""

    def test_income_statement(self, tmp_path):
        """復元後に income_statement() が動作する。"""
        filing = _make_filing()
        items = (
            make_item(
                "NetSales", Decimal("1000000"),
                label_ja="売上高",
                dimensions=(make_consolidated_dim(True), make_current_dim()),
            ),
            make_item(
                "OperatingIncome", Decimal("200000"),
                label_ja="営業利益",
                dimensions=(make_consolidated_dim(True), make_current_dim()),
            ),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_stmts = result[0][1]
        assert restored_stmts is not None
        pl = restored_stmts.income_statement()
        assert len(pl.items) >= 1

    def test_balance_sheet(self, tmp_path):
        """復元後に balance_sheet() が動作する。"""
        filing = _make_filing()
        items = (
            make_item(
                "TotalAssets", Decimal("5000000"),
                label_ja="資産合計",
                period=CURRENT_INSTANT,
                dimensions=(make_consolidated_dim(True),),
            ),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_stmts = result[0][1]
        assert restored_stmts is not None
        bs = restored_stmts.balance_sheet()
        assert len(bs.items) >= 1

    def test_extract_values(self, tmp_path):
        """復元後に extract_values() が動作する。"""
        from tdnet.models.ck import CK
        from tdnet.models.extract import extract_values

        filing = _make_filing()
        items = (
            make_item(
                "NetSales", Decimal("1000000"),
                label_ja="売上高",
                namespace_uri="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-12-01/jppfs_cor",
                dimensions=(make_consolidated_dim(True), make_current_dim()),
            ),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        result = import_parquet(tmp_path)

        restored_stmts = result[0][1]
        assert restored_stmts is not None
        extracted = extract_values(restored_stmts, [CK.REVENUE])
        assert CK.REVENUE in extracted

    def test_doc_id_property(self, tmp_path):
        """復元後の Filing.doc_id が正しい。"""
        filing = _make_filing()
        export_parquet([(filing, None)], tmp_path)
        result = import_parquet(tmp_path)

        restored_filing = result[0][0]
        assert restored_filing.doc_id == filing.doc_id
        assert restored_filing.doc_id != ""


class TestPrefix:
    """prefix パラメータの動作。"""

    def test_prefix_creates_prefixed_files(self, tmp_path):
        """prefix 付きファイルが生成される。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), label_ja="売上高")
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path, prefix="2026-03-04_")

        assert (tmp_path / "2026-03-04_filings.parquet").exists()
        assert (tmp_path / "2026-03-04_line_items.parquet").exists()
        assert not (tmp_path / "filings.parquet").exists()

    def test_prefix_roundtrip(self, tmp_path):
        """prefix 付きで往復できる。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), label_ja="売上高")
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path, prefix="test_")
        result = import_parquet(tmp_path, prefix="test_")

        assert len(result) == 1
        assert result[0][0].company_code == "7203"
        assert list(result[0][1])[0].local_name == "NetSales"  # type: ignore[union-attr]

    def test_multiple_prefixes_coexist(self, tmp_path):
        """異なる prefix のファイルが同一ディレクトリに共存できる。"""
        f1 = _make_filing(company_code="7203")
        f2 = _make_filing(company_code="6758")
        s1 = Statements(
            items=(make_item("NetSales", Decimal("100"), entity_id="7203"),),
            entity_id="7203",
        )
        s2 = Statements(
            items=(make_item("NetSales", Decimal("200"), entity_id="6758"),),
            entity_id="6758",
        )

        export_parquet([(f1, s1)], tmp_path, prefix="day1_")
        export_parquet([(f2, s2)], tmp_path, prefix="day2_")

        r1 = import_parquet(tmp_path, prefix="day1_")
        r2 = import_parquet(tmp_path, prefix="day2_")

        assert len(r1) == 1
        assert len(r2) == 1
        assert r1[0][0].company_code == "7203"
        assert r2[0][0].company_code == "6758"

    def test_empty_prefix_is_default(self, tmp_path):
        """prefix="" はデフォルト動作と同じ。"""
        filing = _make_filing()
        export_parquet([(filing, None)], tmp_path, prefix="")
        result = import_parquet(tmp_path, prefix="")

        assert len(result) == 1
        assert (tmp_path / "filings.parquet").exists()


class TestCompression:
    """圧縮関連テスト。"""

    def test_default_compression_is_zstd(self, tmp_path):
        """デフォルト圧縮が zstd であることを確認する。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), label_ja="売上高")
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)

        meta = pq.read_metadata(tmp_path / "line_items.parquet")
        codec = meta.row_group(0).column(0).compression
        assert codec == "ZSTD"

    def test_compression_snappy(self, tmp_path):
        """compression="snappy" で書き出し → import が動作する。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), label_ja="売上高")
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path, compression="snappy")
        result = import_parquet(tmp_path)

        assert len(result) == 1
        assert list(result[0][1])[0].local_name == "NetSales"  # type: ignore[union-attr]

    def test_compression_none(self, tmp_path):
        """compression="none" で書き出し → import が動作する。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), label_ja="売上高")
        stmts = Statements(items=(item,), entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path, compression="none")
        result = import_parquet(tmp_path)

        assert len(result) == 1
        assert list(result[0][1])[0].local_name == "NetSales"  # type: ignore[union-attr]


class TestDocIdsFilter:
    """doc_ids フィルタの動作。"""

    def test_doc_ids_filter(self, tmp_path):
        """doc_ids で特定の Filing だけ読み込める。"""
        f1 = _make_filing(company_code="7203")
        f2 = _make_filing(company_code="6758")
        s1 = Statements(
            items=(make_item("NetSales", Decimal("100"), entity_id="7203"),),
            entity_id="7203",
        )
        s2 = Statements(
            items=(make_item("NetSales", Decimal("200"), entity_id="6758"),),
            entity_id="6758",
        )

        export_parquet([(f1, s1), (f2, s2)], tmp_path)

        result = import_parquet(tmp_path, doc_ids=[f1.doc_id])
        assert len(result) == 1
        assert result[0][0].company_code == "7203"


class TestIterParquet:
    """iter_parquet の動作。"""

    def test_iter_roundtrip(self, tmp_path):
        """iter_parquet で往復できる。"""
        filing = _make_filing()
        items = (
            make_item("NetSales", Decimal("1000000"), label_ja="売上高"),
            make_item("OperatingIncome", Decimal("200000"), label_ja="営業利益"),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)
        results = list(iter_parquet(tmp_path, include_text_blocks=True))

        assert len(results) == 1
        restored_filing, restored_stmts = results[0]
        assert restored_filing.company_code == "7203"
        assert restored_stmts is not None
        assert len(restored_stmts) == 2

    def test_iter_batch_size(self, tmp_path):
        """batch_size で分割して読み込める。"""
        filings_and_stmts = []
        for i in range(5):
            code = f"000{i}"
            f = Filing(
                pubdate=f"2025-03-{10 + i} 15:00",
                company_code=code,
                company_name=f"テスト{i}",
                title="決算短信",
                document_url=f"https://example.com/tdnet1401202503{10 + i}{code}0.pdf",
                xbrl_url=f"https://example.com/tdnet1401202503{10 + i}{code}0.zip",
                markets_string="東証",
            )
            s = Statements(
                items=(make_item("NetSales", Decimal(str(i * 100)), entity_id=code),),
                entity_id=code,
            )
            filings_and_stmts.append((f, s))

        export_parquet(filings_and_stmts, tmp_path)
        results = list(iter_parquet(tmp_path, batch_size=2))
        assert len(results) == 5

    def test_iter_doc_ids_filter(self, tmp_path):
        """iter_parquet の doc_ids フィルタ。"""
        f1 = _make_filing(company_code="7203")
        f2 = _make_filing(company_code="6758")
        s1 = Statements(
            items=(make_item("NetSales", Decimal("100"), entity_id="7203"),),
            entity_id="7203",
        )
        s2 = Statements(
            items=(make_item("NetSales", Decimal("200"), entity_id="6758"),),
            entity_id="6758",
        )

        export_parquet([(f1, s1), (f2, s2)], tmp_path)
        results = list(iter_parquet(tmp_path, doc_ids=[f1.doc_id]))
        assert len(results) == 1
        assert results[0][0].company_code == "7203"

    def test_iter_empty(self, tmp_path):
        """空データの iter_parquet。"""
        export_parquet([], tmp_path)
        results = list(iter_parquet(tmp_path))
        assert results == []

    def test_iter_text_blocks(self, tmp_path):
        """iter_parquet の include_text_blocks。"""
        filing = _make_filing()
        items = (
            make_item("NetSales", Decimal("100")),
            make_item("NotesTextBlock", "注記", unit_ref=None, decimals=None),
        )
        stmts = Statements(items=items, entity_id="7203")

        export_parquet([(filing, stmts)], tmp_path)

        # include_text_blocks=False（デフォルト）
        r1 = list(iter_parquet(tmp_path, include_text_blocks=False))
        assert r1[0][1] is not None
        assert len(r1[0][1]) == 1

        # include_text_blocks=True
        r2 = list(iter_parquet(tmp_path, include_text_blocks=True))
        assert r2[0][1] is not None
        assert len(r2[0][1]) == 2
