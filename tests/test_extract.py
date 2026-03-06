"""extract_values / extracted_to_dict のストレステスト。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from xbrl_core import DimensionMember
from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.models.ck import CK
from tdnet.models.extract import ExtractedValue, extract_values, extracted_to_dict
from tdnet.models.statements import Statements

from tests.helpers import (
    CURRENT_DURATION,
    CURRENT_INSTANT,
    PRIOR_DURATION,
    PRIOR_INSTANT,
    make_consolidated_dim,
    make_current_dim,
    make_dividend_schedule_dim,
    make_forecast_dim,
    make_item,
    make_prior_dim,
)


def _stmts(*items, entity_id: str = "7203") -> Statements:
    """テスト用 Statements を生成する。"""
    return Statements(items=tuple(items), entity_id=entity_id)


# ============================================================
# 基本的な抽出
# ============================================================


class TestExtractBasic:
    """extract_values の基本動作テスト。"""

    def test_extract_single_key(self):
        """単一キーの抽出。"""
        item = make_item(
            "NetSales",
            Decimal("10000000"),
            dimensions=(make_current_dim(), make_consolidated_dim(True)),
        )
        stmts = _stmts(item)
        result = extract_values(stmts, [CK.REVENUE])
        assert result[CK.REVENUE] is not None
        assert result[CK.REVENUE].value == Decimal("10000000")

    def test_extract_multiple_keys(self):
        """複数キーの抽出。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                dimensions=(make_current_dim(), make_consolidated_dim()),
            ),
            make_item(
                "OperatingIncome", Decimal("3000"),
                dimensions=(make_current_dim(), make_consolidated_dim()),
            ),
            make_item(
                "OrdinaryIncome", Decimal("3500"),
                dimensions=(make_current_dim(), make_consolidated_dim()),
            ),
        ]
        stmts = _stmts(*items)
        result = extract_values(
            stmts,
            [CK.REVENUE, CK.OPERATING_INCOME, CK.ORDINARY_INCOME],
        )
        assert result[CK.REVENUE].value == Decimal("10000")
        assert result[CK.OPERATING_INCOME].value == Decimal("3000")
        assert result[CK.ORDINARY_INCOME].value == Decimal("3500")

    def test_extract_missing_key_returns_none(self):
        """存在しないキーは None。"""
        stmts = _stmts(
            make_item("NetSales", Decimal("10000"), dimensions=(make_current_dim(),)),
        )
        result = extract_values(stmts, [CK.REVENUE, CK.OPERATING_INCOME])
        assert result[CK.REVENUE] is not None
        assert result[CK.OPERATING_INCOME] is None

    def test_extract_all_keys(self):
        """keys=None で全キーを抽出。"""
        items = [
            make_item("NetSales", Decimal("10000"), dimensions=(make_current_dim(),)),
            make_item("OperatingIncome", Decimal("3000"), dimensions=(make_current_dim(),)),
        ]
        stmts = _stmts(*items)
        result = extract_values(stmts)
        assert CK.REVENUE in result
        assert CK.OPERATING_INCOME in result

    def test_extract_empty_statements(self):
        """空の Statements からの抽出。"""
        stmts = _stmts()
        result = extract_values(stmts, [CK.REVENUE])
        assert result[CK.REVENUE] is None

    def test_extract_type_error_for_non_statements(self):
        """Statements 以外を渡すと TypeError。"""
        with pytest.raises(TypeError, match="Statements"):
            extract_values({"not": "statements"}, [CK.REVENUE])  # type: ignore[arg-type]


# ============================================================
# 期間フィルタ
# ============================================================


class TestExtractPeriodFilter:
    """period フィルタのテスト。"""

    def test_period_current_by_dimension(self):
        """period="current" でディメンション CurrentMember のみ取得。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                dimensions=(make_current_dim(),),
                period=CURRENT_DURATION,
            ),
            make_item(
                "NetSales", Decimal("8000"),
                dimensions=(make_prior_dim(),),
                period=PRIOR_DURATION,
            ),
        ]
        stmts = _stmts(*items)
        result = extract_values(stmts, [CK.REVENUE], period="current")
        assert result[CK.REVENUE].value == Decimal("10000")

    def test_period_prior_by_dimension(self):
        """period="prior" でディメンション PreviousMember のみ取得。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                dimensions=(make_current_dim(),),
                period=CURRENT_DURATION,
            ),
            make_item(
                "NetSales", Decimal("8000"),
                dimensions=(make_prior_dim(),),
                period=PRIOR_DURATION,
            ),
        ]
        stmts = _stmts(*items)
        result = extract_values(stmts, [CK.REVENUE], period="prior")
        assert result[CK.REVENUE].value == Decimal("8000")

    def test_period_current_by_context_id(self):
        """context_id が "Current" で始まるアイテム。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                context_id="CurrentYearDuration",
                period=CURRENT_DURATION,
            ),
            make_item(
                "NetSales", Decimal("8000"),
                context_id="PriorYearDuration",
                period=PRIOR_DURATION,
            ),
        ]
        stmts = _stmts(*items)
        result = extract_values(stmts, [CK.REVENUE], period="current")
        assert result[CK.REVENUE].value == Decimal("10000")

    def test_period_none_prefers_current(self):
        """period=None の場合 current が優先される。"""
        items = [
            make_item(
                "NetSales", Decimal("8000"),
                dimensions=(make_prior_dim(),),
                period=PRIOR_DURATION,
                order=0,
            ),
            make_item(
                "NetSales", Decimal("10000"),
                dimensions=(make_current_dim(),),
                period=CURRENT_DURATION,
                order=1,
            ),
        ]
        stmts = _stmts(*items)
        result = extract_values(stmts, [CK.REVENUE])
        assert result[CK.REVENUE].value == Decimal("10000")


# ============================================================
# 連結フィルタ
# ============================================================


class TestExtractConsolidatedFilter:
    """consolidated フィルタのテスト。"""

    def test_consolidated_true(self):
        """consolidated=True で連結のみ取得。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                dimensions=(make_current_dim(), make_consolidated_dim(True)),
            ),
            make_item(
                "NetSales", Decimal("5000"),
                dimensions=(make_current_dim(), make_consolidated_dim(False)),
            ),
        ]
        stmts = _stmts(*items)
        result = extract_values(stmts, [CK.REVENUE], consolidated=True)
        assert result[CK.REVENUE].value == Decimal("10000")

    def test_consolidated_false(self):
        """consolidated=False で個別のみ取得。"""
        items = [
            make_item(
                "NetSales", Decimal("10000"),
                dimensions=(make_current_dim(), make_consolidated_dim(True)),
            ),
            make_item(
                "NetSales", Decimal("5000"),
                dimensions=(make_current_dim(), make_consolidated_dim(False)),
            ),
        ]
        stmts = _stmts(*items)
        result = extract_values(stmts, [CK.REVENUE], consolidated=False)
        assert result[CK.REVENUE].value == Decimal("5000")

    def test_dps_always_nonconsolidated(self):
        """DPS は常に NonConsolidated → consolidated=True でもフィルタされない。"""
        item = make_item(
            "DividendPerShare",
            Decimal("50"),
            dimensions=(make_current_dim(), make_consolidated_dim(False)),
        )
        stmts = _stmts(item)
        result = extract_values(stmts, [CK.DPS], consolidated=True)
        assert result[CK.DPS] is not None
        assert result[CK.DPS].value == Decimal("50")

    def test_reit_bypasses_consolidated_filter(self):
        """REIT 概念は consolidated フィルタをバイパスする。"""
        item = make_item(
            "OperatingRevenuesREIT",
            Decimal("8000"),
            dimensions=(make_current_dim(), make_consolidated_dim(False)),
        )
        stmts = _stmts(item)
        result = extract_values(stmts, [CK.REVENUE], consolidated=True)
        assert result[CK.REVENUE] is not None
        assert result[CK.REVENUE].value == Decimal("8000")

    def test_no_consolidated_items_bypasses_filter(self):
        """ソースに連結アイテムが無い場合はフィルタ不適用。"""
        item = make_item(
            "NetSales",
            Decimal("5000"),
            dimensions=(make_current_dim(), make_consolidated_dim(False)),
        )
        stmts = _stmts(item)
        result = extract_values(stmts, [CK.REVENUE], consolidated=True)
        assert result[CK.REVENUE] is not None


# ============================================================
# 業績予想（Forecast）
# ============================================================


class TestExtractForecast:
    """業績予想の抽出テスト。"""

    def test_forecast_revenue(self):
        """ForecastMember 付きの売上高 → FORECAST_REVENUE。"""
        item = make_item(
            "NetSales",
            Decimal("12000"),
            dimensions=(make_forecast_dim(), make_current_dim()),
        )
        stmts = _stmts(item)
        result = extract_values(stmts, [CK.FORECAST_REVENUE])
        assert result[CK.FORECAST_REVENUE] is not None
        assert result[CK.FORECAST_REVENUE].value == Decimal("12000")

    def test_forecast_dps(self):
        """DividendPerShare + ForecastMember → FORECAST_DPS。"""
        item = make_item(
            "DividendPerShare",
            Decimal("60"),
            dimensions=(make_forecast_dim(),),
        )
        stmts = _stmts(item)
        result = extract_values(stmts, [CK.FORECAST_DPS])
        assert result[CK.FORECAST_DPS] is not None


# ============================================================
# マッパー優先度
# ============================================================


class TestExtractMapperPriority:
    """パイプラインの優先度テスト。"""

    def test_dividend_mapper_takes_priority_over_summary(self):
        """dividend_mapper は summary_mapper より先にマッチする。"""
        item = make_item(
            "DividendPerShare",
            Decimal("50"),
            dimensions=(make_current_dim(),),
        )
        stmts = _stmts(item)
        result = extract_values(stmts, [CK.DPS])
        assert result[CK.DPS] is not None
        assert result[CK.DPS].mapper_name == "dividend_mapper"

    def test_non_none_value_preferred(self):
        """非 None 値が None 値より優先される。"""
        items = [
            make_item(
                "NetSales", None,
                dimensions=(make_current_dim(),),
                is_nil=True,
                order=0,
            ),
            make_item(
                "NetSales", Decimal("10000"),
                dimensions=(make_current_dim(),),
                order=1,
            ),
        ]
        stmts = _stmts(*items)
        result = extract_values(stmts, [CK.REVENUE])
        assert result[CK.REVENUE].value == Decimal("10000")


# ============================================================
# カスタムマッパー
# ============================================================


class TestExtractCustomMapper:
    """カスタムマッパーのテスト。"""

    def test_single_custom_mapper(self):
        """単一のカスタムマッパーで抽出。"""
        from tdnet.mapper import dict_mapper

        custom = dict_mapper({"MyCustomConcept": "custom_revenue"})
        item = make_item("MyCustomConcept", Decimal("999"))
        stmts = _stmts(item)
        result = extract_values(stmts, ["custom_revenue"], mapper=custom)
        assert result["custom_revenue"] is not None
        assert result["custom_revenue"].value == Decimal("999")

    def test_custom_mapper_pipeline(self):
        """カスタムマッパーのパイプライン。"""
        from tdnet.mapper import dict_mapper, summary_mapper

        custom = dict_mapper({"SpecialConcept": "special_key"})
        items = [
            make_item("SpecialConcept", Decimal("111")),
            make_item("NetSales", Decimal("222"), dimensions=(make_current_dim(),)),
        ]
        stmts = _stmts(*items)
        result = extract_values(
            stmts,
            ["special_key", CK.REVENUE],
            mapper=[custom, summary_mapper],
        )
        assert result["special_key"].value == Decimal("111")
        assert result[CK.REVENUE].value == Decimal("222")


# ============================================================
# extracted_to_dict
# ============================================================


class TestExtractedToDict:
    """extracted_to_dict のテスト。"""

    def test_basic_conversion(self):
        """基本的な変換。"""
        item = make_item("NetSales", Decimal("10000"), dimensions=(make_current_dim(),))
        stmts = _stmts(item)
        result = extract_values(stmts, [CK.REVENUE])
        d = extracted_to_dict(result)
        assert d[CK.REVENUE] == Decimal("10000")

    def test_missing_key_is_none(self):
        """存在しないキーは None。"""
        stmts = _stmts()
        result = extract_values(stmts, [CK.REVENUE])
        d = extracted_to_dict(result)
        assert d[CK.REVENUE] is None

    def test_merge_multiple_dicts(self):
        """複数辞書のマージ。"""
        item1 = make_item("NetSales", Decimal("10000"), dimensions=(make_current_dim(),))
        item2 = make_item("TotalAssets", Decimal("50000"), period=CURRENT_INSTANT)
        stmts1 = _stmts(item1)
        stmts2 = _stmts(item2)
        r1 = extract_values(stmts1, [CK.REVENUE])
        r2 = extract_values(stmts2, [CK.TOTAL_ASSETS])
        d = extracted_to_dict(r1, r2)
        assert d[CK.REVENUE] == Decimal("10000")
        assert d[CK.TOTAL_ASSETS] == Decimal("50000")


# ============================================================
# 大量データのストレステスト
# ============================================================


class TestExtractStress:
    """大量データでの抽出パフォーマンス確認。"""

    def test_large_number_of_items(self):
        """1000 個の LineItem を処理できる。"""
        items = []
        for i in range(1000):
            items.append(
                make_item(
                    "NetSales",
                    Decimal(str(i * 1000)),
                    dimensions=(make_current_dim(),),
                    order=i,
                )
            )
        stmts = _stmts(*items)
        result = extract_values(stmts, [CK.REVENUE])
        assert result[CK.REVENUE] is not None

    def test_all_ck_keys_extraction(self):
        """全 CK キーのリクエストでもエラーしない。"""
        item = make_item("NetSales", Decimal("10000"), dimensions=(make_current_dim(),))
        stmts = _stmts(item)
        all_keys = list(CK)
        result = extract_values(stmts, all_keys)
        assert result[CK.REVENUE] is not None
        # 未マッチのキーは None
        none_count = sum(1 for v in result.values() if v is None)
        assert none_count > 0

    def test_many_different_concepts(self):
        """多数の異なる概念が正しくマップされる。"""
        concepts = [
            ("NetSales", CK.REVENUE),
            ("CostOfSales", CK.COST_OF_SALES),
            ("GrossProfit", CK.GROSS_PROFIT),
            ("OperatingIncome", CK.OPERATING_INCOME),
            ("OrdinaryIncome", CK.ORDINARY_INCOME),
            ("ProfitLossAttributableToOwnersOfParent", CK.NET_INCOME_PARENT),
        ]
        items = [
            make_item(
                concept,
                Decimal(str(i * 1000000)),
                dimensions=(make_current_dim(), make_consolidated_dim()),
                order=i,
            )
            for i, (concept, _) in enumerate(concepts)
        ]
        stmts = _stmts(*items)
        keys = [ck for _, ck in concepts]
        result = extract_values(stmts, keys, period="current", consolidated=True)
        for concept, ck in concepts:
            assert result[ck] is not None, f"{concept} -> {ck} should be found"
