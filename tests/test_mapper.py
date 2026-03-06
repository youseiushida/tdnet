"""マッパーパイプラインのストレステスト。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tdnet.mapper import (
    MapperContext,
    dict_mapper,
    dividend_mapper,
    forecast_mapper,
    get_default_pipeline,
    statement_mapper,
    summary_mapper,
)
from tdnet.models.ck import CK

from tests.helpers import (
    make_consolidated_dim,
    make_current_dim,
    make_dividend_schedule_dim,
    make_forecast_dim,
    make_item,
)

_CTX = MapperContext(entity_id="7203")


# ============================================================
# dividend_mapper
# ============================================================


class TestDividendMapper:
    """配当マッパーのテスト。"""

    def test_dps_no_schedule_returns_dps(self):
        """DividendPerShare (スケジュール軸なし) → CK.DPS。"""
        item = make_item("DividendPerShare", Decimal("50"))
        assert dividend_mapper(item, _CTX) == CK.DPS

    def test_dps_annual_member(self):
        """AnnualMember → CK.DPS。"""
        item = make_item(
            "DividendPerShare",
            Decimal("100"),
            dimensions=(make_dividend_schedule_dim("AnnualMember"),),
        )
        assert dividend_mapper(item, _CTX) == CK.DPS

    @pytest.mark.parametrize("member", [
        "FirstQuarterMember",
        "SecondQuarterMember",
        "ThirdQuarterMember",
        "YearEndMember",
    ])
    def test_dps_quarterly_members_return_interim(self, member: str):
        """四半期/期末メンバー → CK.INTERIM_DPS。"""
        item = make_item(
            "DividendPerShare",
            Decimal("25"),
            dimensions=(make_dividend_schedule_dim(member),),
        )
        assert dividend_mapper(item, _CTX) == CK.INTERIM_DPS

    def test_non_dps_concept_returns_none(self):
        """DividendPerShare 以外は None。"""
        item = make_item("NetSales", Decimal("1000000"))
        assert dividend_mapper(item, _CTX) is None


# ============================================================
# forecast_mapper
# ============================================================


class TestForecastMapper:
    """業績予想マッパーのテスト。"""

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("NetSales", CK.FORECAST_REVENUE),
            ("OperatingIncome", CK.FORECAST_OPERATING_INCOME),
            ("OrdinaryIncome", CK.FORECAST_ORDINARY_INCOME),
            ("ProfitAttributableToOwnersOfParent", CK.FORECAST_NET_INCOME_PARENT),
            ("NetIncomePerShare", CK.FORECAST_EPS),
        ],
    )
    def test_forecast_with_forecast_member(self, concept: str, expected_ck: str):
        """ForecastMember ディメンション付き → FORECAST_* CK。"""
        item = make_item(
            concept,
            Decimal("1000"),
            dimensions=(make_forecast_dim(), make_current_dim()),
        )
        assert forecast_mapper(item, _CTX) == expected_ck

    def test_forecast_without_forecast_member_returns_none(self):
        """ForecastMember なし → None。"""
        item = make_item("NetSales", Decimal("1000"))
        assert forecast_mapper(item, _CTX) is None

    def test_forecast_unknown_concept_returns_none(self):
        """未知の概念 + ForecastMember → None（summary にマップできないため）。"""
        item = make_item(
            "UnknownConceptXYZ",
            Decimal("1000"),
            dimensions=(make_forecast_dim(),),
        )
        assert forecast_mapper(item, _CTX) is None

    def test_forecast_dps(self):
        """DividendPerShare + ForecastMember → FORECAST_DPS。"""
        item = make_item(
            "DividendPerShare",
            Decimal("50"),
            dimensions=(make_forecast_dim(),),
        )
        assert forecast_mapper(item, _CTX) == CK.FORECAST_DPS


# ============================================================
# summary_mapper
# ============================================================


class TestSummaryMapper:
    """サマリーマッパーのテスト。"""

    def test_basic_summary(self):
        """基本的なサマリー科目。"""
        item = make_item("NetSales", Decimal("10000000"))
        assert summary_mapper(item, _CTX) == CK.REVENUE

    def test_summary_skips_forecast_member(self):
        """ForecastMember 付きはスキップ（forecast_mapper に委譲）。"""
        item = make_item(
            "NetSales",
            Decimal("10000000"),
            dimensions=(make_forecast_dim(),),
        )
        assert summary_mapper(item, _CTX) is None

    def test_summary_skips_dps(self):
        """DividendPerShare はスキップ（dividend_mapper に委譲）。"""
        item = make_item("DividendPerShare", Decimal("50"))
        assert summary_mapper(item, _CTX) is None

    def test_summary_unknown_returns_none(self):
        """未知の概念は None。"""
        item = make_item("CompletelyUnknownConcept", Decimal("100"))
        assert summary_mapper(item, _CTX) is None


# ============================================================
# statement_mapper
# ============================================================


class TestStatementMapper:
    """財務諸表本体マッパーのテスト。"""

    def test_jgaap_pl_concept(self):
        """jppfs_cor PL 科目。"""
        item = make_item("CostOfSales", Decimal("5000000"))
        assert statement_mapper(item, _CTX) == CK.COST_OF_SALES

    def test_jgaap_bs_concept(self):
        """jppfs_cor BS 科目。"""
        item = make_item("CashAndDeposits", Decimal("3000000"))
        assert statement_mapper(item, _CTX) == CK.CASH_AND_DEPOSITS

    def test_ifrs_suffix_normalized(self):
        """IFRS サフィックス付き概念が正規化で解決される。"""
        item = make_item("FinanceIncomeIFRS", Decimal("200000"))
        assert statement_mapper(item, _CTX) == CK.FINANCE_INCOME

    def test_reit_exact_match(self):
        """REIT 科目の完全一致。"""
        item = make_item("OperatingRevenuesREIT", Decimal("500000"))
        assert statement_mapper(item, _CTX) == CK.REVENUE

    def test_unknown_returns_none(self):
        """未知の概念。"""
        item = make_item("TotallyFakeConceptXYZ", Decimal("100"))
        assert statement_mapper(item, _CTX) is None


# ============================================================
# dict_mapper
# ============================================================


class TestDictMapper:
    """カスタム辞書マッパーのテスト。"""

    def test_dict_mapper_matches(self):
        """辞書にある概念はマッチする。"""
        mapper = dict_mapper({"CustomConcept": "custom_key"})
        item = make_item("CustomConcept", Decimal("100"))
        assert mapper(item, _CTX) == "custom_key"

    def test_dict_mapper_no_match(self):
        """辞書にない概念は None。"""
        mapper = dict_mapper({"CustomConcept": "custom_key"})
        item = make_item("OtherConcept", Decimal("200"))
        assert mapper(item, _CTX) is None

    def test_dict_mapper_name(self):
        """name パラメータが __name__ に設定される。"""
        mapper = dict_mapper({"A": "a"}, name="my_mapper")
        assert mapper.__name__ == "my_mapper"

    def test_dict_mapper_auto_name(self):
        """name 未指定で自動名前付け。"""
        mapper = dict_mapper({"A": "a", "B": "b"})
        assert "2 entries" in mapper.__name__

    def test_dict_mapper_empty_dict(self):
        """空辞書マッパーは常に None。"""
        mapper = dict_mapper({})
        item = make_item("AnyConcept", Decimal("100"))
        assert mapper(item, _CTX) is None


# ============================================================
# get_default_pipeline
# ============================================================


class TestDefaultPipeline:
    """デフォルトパイプラインのテスト。"""

    def test_pipeline_length(self):
        """4 つのマッパーが含まれる。"""
        pipeline = get_default_pipeline()
        assert len(pipeline) == 4

    def test_pipeline_order(self):
        """dividend → forecast → summary → statement の順。"""
        pipeline = get_default_pipeline()
        assert pipeline[0] is dividend_mapper
        assert pipeline[1] is forecast_mapper
        assert pipeline[2] is summary_mapper
        assert pipeline[3] is statement_mapper

    def test_pipeline_returns_new_list(self):
        """毎回新しいリストが返される。"""
        p1 = get_default_pipeline()
        p2 = get_default_pipeline()
        assert p1 == p2
        assert p1 is not p2
