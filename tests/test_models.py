"""モデル層のストレステスト: CK, StatementType, LineItem, LabelInfo。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from xbrl_core import DimensionMember
from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.models.ck import CK
from tdnet.models.statement_type import StatementType
from tdnet.models.types import LabelInfo, LabelSource, LineItem

from tests.helpers import make_item, make_label


# ============================================================
# CK StrEnum
# ============================================================


class TestCK:
    """CK StrEnum の基本性質テスト。"""

    def test_ck_is_str(self):
        """CK メンバーは str のサブクラス。"""
        assert isinstance(CK.REVENUE, str)

    def test_ck_value_equals_str(self):
        """CK.REVENUE == "revenue" が成立する。"""
        assert CK.REVENUE == "revenue"

    def test_ck_can_be_dict_key(self):
        """CK を辞書キーとして使える。"""
        d = {CK.REVENUE: 100}
        assert d["revenue"] == 100
        assert d[CK.REVENUE] == 100

    def test_all_ck_members_are_unique(self):
        """全 CK メンバーの値が一意。"""
        values = [m.value for m in CK]
        assert len(values) == len(set(values))

    def test_all_ck_members_are_lowercase_snake(self):
        """全 CK メンバーの値が lowercase_snake_case。"""
        for m in CK:
            assert m.value == m.value.lower(), f"{m.name}: {m.value}"
            assert " " not in m.value

    def test_ck_membership(self):
        """str in CK で存在確認可能。"""
        assert "revenue" in [m.value for m in CK]

    def test_ck_frozenset_lookup(self):
        """frozenset での高速ルックアップ。"""
        members = frozenset(CK)
        assert CK.REVENUE in members
        assert "revenue" in members
        assert "nonexistent_key" not in members

    def test_ck_count_is_substantial(self):
        """CK に十分な数のメンバーが存在する。"""
        assert len(CK) > 100


# ============================================================
# StatementType
# ============================================================


class TestStatementType:
    """StatementType enum テスト。"""

    def test_all_statement_types(self):
        """全5種類の財務諸表タイプが存在する。"""
        expected = {
            "income_statement",
            "balance_sheet",
            "cash_flow_statement",
            "statement_of_changes_in_equity",
            "comprehensive_income",
        }
        actual = {st.value for st in StatementType}
        assert actual == expected


# ============================================================
# LabelInfo / LabelSource
# ============================================================


class TestLabelInfo:
    """LabelInfo の immutability とフィールドテスト。"""

    def test_label_info_is_frozen(self):
        """LabelInfo は frozen dataclass。"""
        label = make_label("売上高")
        with pytest.raises(AttributeError):
            label.text = "変更"  # type: ignore[misc]

    def test_label_sources(self):
        """LabelSource の全メンバー。"""
        assert set(LabelSource) == {
            LabelSource.STANDARD,
            LabelSource.FILER,
            LabelSource.FALLBACK,
        }


# ============================================================
# LineItem
# ============================================================


class TestLineItem:
    """LineItem の frozen / slots / 全フィールドテスト。"""

    def test_line_item_is_frozen(self):
        """LineItem は frozen dataclass。"""
        item = make_item("NetSales", Decimal("1000000"))
        with pytest.raises(AttributeError):
            item.value = Decimal("999")  # type: ignore[misc]

    def test_line_item_all_fields_accessible(self):
        """全フィールドにアクセスできる。"""
        item = make_item(
            "NetSales",
            Decimal("1000000"),
            unit_ref="JPY",
            context_id="CurrentYearDuration",
            entity_id="7203",
        )
        assert item.local_name == "NetSales"
        assert item.value == Decimal("1000000")
        assert item.unit_ref == "JPY"
        assert item.context_id == "CurrentYearDuration"
        assert item.entity_id == "7203"
        assert item.is_nil is False
        assert item.dimensions == ()

    def test_line_item_with_nil_value(self):
        """xsi:nil アイテム。"""
        item = make_item("NetSales", None, is_nil=True)
        assert item.value is None
        assert item.is_nil is True

    def test_line_item_with_string_value(self):
        """テキスト値。"""
        item = make_item("TextBlock", "ダミーテキスト", unit_ref=None)
        assert item.value == "ダミーテキスト"
        assert item.unit_ref is None

    def test_line_item_with_dimensions(self):
        """ディメンション付き LineItem。"""
        dim = DimensionMember(axis="SomeAxis", member="SomeMember")
        item = make_item("NetSales", Decimal("100"), dimensions=(dim,))
        assert len(item.dimensions) == 1
        assert item.dimensions[0].axis == "SomeAxis"

    def test_line_item_with_instant_period(self):
        """InstantPeriod の LineItem。"""
        period = InstantPeriod(instant=date(2025, 3, 31))
        item = make_item("Assets", Decimal("5000000"), period=period)
        assert isinstance(item.period, InstantPeriod)
        assert item.period.instant == date(2025, 3, 31)

    def test_line_item_with_duration_period(self):
        """DurationPeriod の LineItem。"""
        period = DurationPeriod(start_date=date(2024, 4, 1), end_date=date(2025, 3, 31))
        item = make_item("NetSales", Decimal("1000000"), period=period)
        assert isinstance(item.period, DurationPeriod)
        assert item.period.start_date == date(2024, 4, 1)
        assert item.period.end_date == date(2025, 3, 31)

    def test_line_item_large_decimal(self):
        """巨大数値。"""
        val = Decimal("99999999999999999999")
        item = make_item("TotalAssets", val)
        assert item.value == val

    def test_line_item_negative_decimal(self):
        """負の数値。"""
        val = Decimal("-5000000")
        item = make_item("TreasuryStock", val)
        assert item.value == val

    def test_line_item_zero_decimal(self):
        """ゼロ。"""
        item = make_item("ExtraordinaryLoss", Decimal("0"))
        assert item.value == Decimal("0")
