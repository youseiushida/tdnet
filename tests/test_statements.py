"""Statements コンテナのストレステスト。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.models.ck import CK
from tdnet.models.statement_type import StatementType
from tdnet.models.statements import Statements

from tests.helpers import (
    CURRENT_DURATION,
    CURRENT_INSTANT,
    PRIOR_DURATION,
    PRIOR_INSTANT,
    make_consolidated_dim,
    make_current_dim,
    make_item,
    make_prior_dim,
)

_JPPFS_NS = "http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/cor"


def _stmts(*items, entity_id: str = "7203") -> Statements:
    return Statements(items=tuple(items), entity_id=entity_id)


# ============================================================
# 基本操作
# ============================================================


class TestStatementsBasic:
    """Statements の基本操作テスト。"""

    def test_len(self):
        """__len__ が正しいアイテム数を返す。"""
        items = [make_item("A"), make_item("B"), make_item("C")]
        stmts = _stmts(*items)
        assert len(stmts) == 3

    def test_iter(self):
        """__iter__ で全アイテムを走査できる。"""
        items = [make_item("A"), make_item("B")]
        stmts = _stmts(*items)
        result = list(stmts)
        assert len(result) == 2

    def test_getitem_by_local_name(self):
        """__getitem__ で local_name 検索。"""
        stmts = _stmts(make_item("NetSales", Decimal("1000")))
        item = stmts["NetSales"]
        assert item.value == Decimal("1000")

    def test_getitem_by_label_ja(self):
        """__getitem__ で日本語ラベル検索。"""
        stmts = _stmts(
            make_item("NetSales", Decimal("1000"), label_ja="売上高"),
        )
        item = stmts["売上高"]
        assert item.value == Decimal("1000")

    def test_getitem_by_label_en(self):
        """__getitem__ で英語ラベル検索。"""
        stmts = _stmts(
            make_item("NetSales", Decimal("1000"), label_en="Net Sales"),
        )
        item = stmts["Net Sales"]
        assert item.value == Decimal("1000")

    def test_getitem_raises_keyerror(self):
        """存在しないキーで KeyError。"""
        stmts = _stmts(make_item("NetSales"))
        with pytest.raises(KeyError):
            stmts["NonExistent"]

    def test_get_returns_default(self):
        """get() は見つからない場合 default を返す。"""
        stmts = _stmts(make_item("NetSales"))
        assert stmts.get("NonExistent") is None

    def test_contains(self):
        """__contains__ (in 演算子)。"""
        stmts = _stmts(make_item("NetSales", label_ja="売上高"))
        assert "売上高" in stmts
        assert "NonExistent" not in stmts

    def test_contains_non_str(self):
        """str 以外は常に False。"""
        stmts = _stmts(make_item("NetSales"))
        assert 123 not in stmts

    def test_search(self):
        """search() でキーワード部分一致検索。"""
        items = [
            make_item("NetSales", label_ja="売上高"),
            make_item("NetIncome", label_ja="当期純利益"),
            make_item("NetAssets", label_ja="純資産"),
        ]
        stmts = _stmts(*items)
        result = stmts.search("Net")
        assert len(result) == 3

    def test_search_case_insensitive(self):
        """大文字小文字を区別しない検索。"""
        stmts = _stmts(make_item("NetSales", label_ja="売上高"))
        assert len(stmts.search("netsales")) == 1

    def test_search_no_match(self):
        """マッチなし。"""
        stmts = _stmts(make_item("NetSales"))
        assert len(stmts.search("ZZZZZ")) == 0

    def test_empty_statements(self):
        """空の Statements。"""
        stmts = _stmts()
        assert len(stmts) == 0
        assert list(stmts) == []
        assert stmts.get("anything") is None


# ============================================================
# income_statement
# ============================================================


class TestIncomeStatement:
    """損益計算書の組み立てテスト。"""

    def test_pl_items_filtered(self):
        """PL 科目のみ含む。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                unit_ref="JPY", period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
            ),
            make_item(
                "OperatingIncome", Decimal("3000"),
                unit_ref="JPY", period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
            ),
            # BS 科目は除外される
            make_item(
                "CashAndDeposits", Decimal("5000"),
                unit_ref="JPY", period=CURRENT_INSTANT,
                dimensions=(make_consolidated_dim(),),
            ),
        ]
        stmts = _stmts(*items)
        pl = stmts.income_statement()
        assert pl.statement_type == StatementType.INCOME_STATEMENT
        assert pl.consolidated is True
        # PL 科目のみ（DurationPeriod + monetary + PL keyword）
        for item in pl:
            assert isinstance(item.period, DurationPeriod)

    def test_pl_empty_returns_all_items(self):
        """PL 科目が0件の場合、全アイテムをフォールバック。"""
        items = [
            make_item("UnknownConcept", Decimal("100"), period=CURRENT_DURATION),
        ]
        stmts = _stmts(*items)
        pl = stmts.income_statement()
        assert len(pl) > 0


# ============================================================
# balance_sheet
# ============================================================


class TestBalanceSheet:
    """貸借対照表の組み立てテスト。"""

    def test_bs_items_filtered(self):
        """BS 科目のみ含む。"""
        items = [
            make_item(
                "CashAndDeposits", Decimal("5000"),
                unit_ref="JPY", period=CURRENT_INSTANT,
                dimensions=(make_consolidated_dim(),),
            ),
            make_item(
                "TotalAssets", Decimal("50000"),
                unit_ref="JPY", period=CURRENT_INSTANT,
                dimensions=(make_consolidated_dim(),),
                label_ja="総資産",
            ),
            # PL 科目は除外される
            make_item(
                "NetSales", Decimal("10000"),
                unit_ref="JPY", period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
            ),
        ]
        stmts = _stmts(*items)
        bs = stmts.balance_sheet()
        assert bs.statement_type == StatementType.BALANCE_SHEET
        for item in bs:
            assert isinstance(item.period, InstantPeriod)


# ============================================================
# cash_flow_statement
# ============================================================


class TestCashFlowStatement:
    """CF 計算書の組み立てテスト。"""

    def test_cf_items_filtered(self):
        """CF 科目のみ含む。"""
        items = [
            make_item(
                "NetCashProvidedByUsedInOperatingActivities", Decimal("2000"),
                unit_ref="JPY", period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
                label_ja="営業CF",
            ),
            make_item(
                "DepreciationAndAmortizationOpeCF", Decimal("500"),
                unit_ref="JPY", period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
            ),
        ]
        stmts = _stmts(*items)
        cf = stmts.cash_flow_statement()
        assert cf.statement_type == StatementType.CASH_FLOW_STATEMENT
        assert len(cf) >= 1


# ============================================================
# to_dataframe
# ============================================================


class TestStatementsDataFrame:
    """DataFrame 変換テスト。"""

    def test_to_dataframe_columns(self):
        """必要なカラムが存在する。"""
        items = [
            make_item("NetSales", Decimal("10000"), label_ja="売上高"),
        ]
        stmts = _stmts(*items)
        df = stmts.to_dataframe()
        expected_cols = {
            "label_ja", "label_en", "value", "value_text", "unit",
            "concept", "context_id", "local_name", "namespace_uri",
            "decimals", "is_nil", "order", "period", "dimensions",
        }
        assert expected_cols.issubset(set(df.columns))

    def test_to_dataframe_decimal_to_float(self):
        """Decimal → float 変換。"""
        items = [make_item("NetSales", Decimal("10000"))]
        stmts = _stmts(*items)
        df = stmts.to_dataframe()
        assert df["value"].iloc[0] == 10000.0

    def test_to_dataframe_string_value(self):
        """テキスト値は value_text カラム。"""
        items = [make_item("TextBlock", "テスト文字列", unit_ref=None)]
        stmts = _stmts(*items)
        df = stmts.to_dataframe()
        assert df["value_text"].iloc[0] == "テスト文字列"
        assert df["value"].iloc[0] is None or str(df["value"].iloc[0]) == "nan"

    def test_to_dataframe_empty(self):
        """空の Statements でも DataFrame を返す。"""
        stmts = _stmts()
        df = stmts.to_dataframe()
        assert len(df) == 0


# ============================================================
# FinancialStatement
# ============================================================


class TestFinancialStatement:
    """FinancialStatement のテスト。"""

    def test_financial_statement_getitem(self):
        """FinancialStatement の __getitem__。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                label_ja="売上高", unit_ref="JPY",
                period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
            ),
        ]
        stmts = _stmts(*items)
        pl = stmts.income_statement()
        item = pl["売上高"]
        assert item.value == Decimal("10000")

    def test_financial_statement_to_dict(self):
        """to_dict() の形式。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                label_ja="売上高", label_en="Net Sales",
                unit_ref="JPY", period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
            ),
        ]
        stmts = _stmts(*items)
        pl = stmts.income_statement()
        dicts = pl.to_dict()
        assert len(dicts) > 0
        d = dicts[0]
        assert "label_ja" in d
        assert "label_en" in d
        assert "value" in d

    def test_financial_statement_to_dataframe(self):
        """to_dataframe() が DataFrame を返す。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                unit_ref="JPY", period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
            ),
        ]
        stmts = _stmts(*items)
        pl = stmts.income_statement()
        df = pl.to_dataframe()
        assert len(df) > 0

    def test_financial_statement_to_dataframe_full(self):
        """to_dataframe(full=True) で全カラム。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                unit_ref="JPY", period=CURRENT_DURATION,
                dimensions=(make_consolidated_dim(),),
            ),
        ]
        stmts = _stmts(*items)
        pl = stmts.income_statement()
        df = pl.to_dataframe(full=True)
        assert "context_id" in df.columns
        assert "local_name" in df.columns
        assert "dimensions" in df.columns
