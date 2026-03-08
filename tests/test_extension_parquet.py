"""Parquet 永続化の往復テスト。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.extension import from_parquet, to_parquet
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


class TestRoundTripEmpty:
    """空リストの往復。"""

    def test_empty_list(self, tmp_path):
        """空リストを保存・復元できる。"""
        to_parquet([], tmp_path)
        result = from_parquet(tmp_path)
        assert result == []


class TestRoundTripFilingOnly:
    """Filing のみ（Statements=None）の往復。"""

    def test_filing_without_statements(self, tmp_path):
        """Statements=None で保存・復元できる。"""
        filing = _make_filing()
        to_parquet([(filing, None)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(f1, s1), (f2, s2)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert isinstance(restored_item.value, Decimal)
        assert restored_item.value == Decimal("12345678.0")

    def test_str_value(self, tmp_path):
        """文字列値が往復する。"""
        filing = _make_filing()
        item = make_item("SomeText", "テスト文字列", unit_ref=None, decimals=None)
        stmts = Statements(items=(item,), entity_id="7203")

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.value == "テスト文字列"

    def test_none_value(self, tmp_path):
        """None 値が往復する。"""
        filing = _make_filing()
        item = make_item("NilItem", None, is_nil=True, unit_ref=None, decimals=None)
        stmts = Statements(items=(item,), entity_id="7203")

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.decimals == -6

    def test_inf_decimals(self, tmp_path):
        """"INF" の decimals が往復する。"""
        from dataclasses import replace

        filing = _make_filing()
        base = make_item("Ratio", Decimal("0.5"))
        item = replace(base, decimals="INF")
        stmts = Statements(items=(item,), entity_id="7203")

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.decimals == "INF"

    def test_none_decimals(self, tmp_path):
        """None の decimals が往復する。"""
        filing = _make_filing()
        item = make_item("TextItem", "text", decimals=None, unit_ref=None)
        stmts = Statements(items=(item,), entity_id="7203")

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.dimensions == ()

    def test_multiple_dimensions(self, tmp_path):
        """複数 dimensions が往復する。"""
        filing = _make_filing()
        dims = (make_consolidated_dim(True), make_current_dim())
        item = make_item("NetSales", Decimal("100"), dimensions=dims)
        stmts = Statements(items=(item,), entity_id="7203")

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

        restored_item = list(result[0][1])[0]  # type: ignore[union-attr]
        assert restored_item.label_ja.text == "売上高"
        assert restored_item.label_ja.source == LabelSource.STANDARD
        assert restored_item.label_ja.lang == "ja"
        assert restored_item.label_en.text == "Net Sales"
        assert restored_item.label_en.source == LabelSource.STANDARD
        assert restored_item.label_en.lang == "en"


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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

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

        to_parquet([(filing, stmts)], tmp_path)
        result = from_parquet(tmp_path)

        restored_stmts = result[0][1]
        assert restored_stmts is not None
        extracted = extract_values(restored_stmts, [CK.REVENUE])
        assert CK.REVENUE in extracted

    def test_doc_id_property(self, tmp_path):
        """復元後の Filing.doc_id が正しい。"""
        filing = _make_filing()
        to_parquet([(filing, None)], tmp_path)
        result = from_parquet(tmp_path)

        restored_filing = result[0][0]
        assert restored_filing.doc_id == filing.doc_id
        assert restored_filing.doc_id != ""
