"""マッパーパイプラインのストレステスト。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tdnet.mapper import (
    MapperContext,
    build_parent_index,
    calc_mapper,
    definition_mapper,
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
        """6 つのマッパーが含まれる。"""
        pipeline = get_default_pipeline()
        assert len(pipeline) == 6

    def test_pipeline_order(self):
        """dividend → forecast → summary → statement → definition → calc の順。"""
        pipeline = get_default_pipeline()
        assert pipeline[0] is dividend_mapper
        assert pipeline[1] is forecast_mapper
        assert pipeline[2] is summary_mapper
        assert pipeline[3] is statement_mapper
        # definition_mapper() と calc_mapper() はファクトリ生成なので名前で確認
        assert pipeline[4].__name__ == "definition_mapper"
        assert pipeline[5].__name__ == "calc_mapper"

    def test_pipeline_returns_new_list(self):
        """毎回新しいリストが返される。"""
        p1 = get_default_pipeline()
        p2 = get_default_pipeline()
        assert p1 is not p2


# ============================================================
# definition_mapper
# ============================================================


class TestDefinitionMapper:
    """Definition Linkbase マッパーのテスト。"""

    def test_no_index_returns_none(self):
        """definition_parent_index が空なら常に None。"""
        mapper = definition_mapper()
        item = make_item("CustomRevenue", Decimal("1000"))
        assert mapper(item, _CTX) is None

    def test_resolves_via_parent_index(self):
        """逆引きインデックスで祖先の CK を返す。"""
        mapper = definition_mapper()
        ctx = MapperContext(
            entity_id="7203",
            definition_parent_index={"CustomRevenue": "NetSales"},
        )
        item = make_item("CustomRevenue", Decimal("1000"))
        # NetSales → CK.REVENUE（statement_mappings 経由）
        assert mapper(item, ctx) == CK.REVENUE

    def test_ancestor_not_in_dictionary_returns_none(self):
        """祖先が辞書にない場合は None。"""
        mapper = definition_mapper()
        ctx = MapperContext(
            entity_id="7203",
            definition_parent_index={"CustomConcept": "TotallyUnknownAncestor"},
        )
        item = make_item("CustomConcept", Decimal("100"))
        assert mapper(item, ctx) is None

    def test_custom_lookup(self):
        """カスタム lookup 関数を注入できる。"""
        my_lookup = {"NetSales": "MY_REVENUE"}
        mapper = definition_mapper(lookup=my_lookup.get)
        ctx = MapperContext(
            entity_id="7203",
            definition_parent_index={"CustomRevenue": "NetSales"},
        )
        item = make_item("CustomRevenue", Decimal("1000"))
        assert mapper(item, ctx) == "MY_REVENUE"

    def test_custom_lookup_miss_returns_none(self):
        """カスタム lookup にない祖先は None。"""
        my_lookup = {"OperatingIncome": "MY_OP_INCOME"}
        mapper = definition_mapper(lookup=my_lookup.get)
        ctx = MapperContext(
            entity_id="7203",
            definition_parent_index={"CustomRevenue": "NetSales"},
        )
        item = make_item("CustomRevenue", Decimal("1000"))
        assert mapper(item, ctx) is None

    def test_standard_concept_not_in_index_returns_none(self):
        """逆引きインデックスにない概念は None。"""
        mapper = definition_mapper()
        ctx = MapperContext(
            entity_id="7203",
            definition_parent_index={"CustomRevenue": "NetSales"},
        )
        item = make_item("OperatingIncome", Decimal("500"))
        assert mapper(item, ctx) is None


# ============================================================
# calc_mapper
# ============================================================


class TestCalcMapper:
    """Calculation Linkbase マッパーのテスト。"""

    def test_no_linkbase_returns_none(self):
        """calculation_linkbase が None なら常に None。"""
        mapper = calc_mapper()
        item = make_item("CustomExpense", Decimal("1000"))
        assert mapper(item, _CTX) is None

    def test_custom_lookup(self):
        """カスタム lookup 関数を注入できる。"""
        my_lookup = {"OperatingIncome": "MY_OP_INCOME"}
        mapper = calc_mapper(lookup=my_lookup.get)
        # calculation_linkbase が None なので None
        item = make_item("SomeChild", Decimal("100"))
        assert mapper(item, _CTX) is None

    def test_mapper_name(self):
        """生成されたマッパーの名前が正しい。"""
        mapper = calc_mapper()
        assert mapper.__name__ == "calc_mapper"


# ============================================================
# build_parent_index
# ============================================================


class TestBuildParentIndex:
    """build_parent_index のテスト。"""

    def test_none_returns_empty(self):
        """None を渡すと空辞書。"""
        assert build_parent_index(None) == {}
