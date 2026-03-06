"""マッピング辞書のストレステスト: summary_mappings, statement_mappings。"""

from __future__ import annotations

import pytest

from tdnet.models.ck import CK
from tdnet.models.summary_mappings import (
    SummaryMapping,
    all_summary_mappings,
    lookup_summary,
)
from tdnet.models.statement_mappings import (
    lookup_statement,
    lookup_statement_exact,
    lookup_statement_normalized,
)


# ============================================================
# summary_mappings
# ============================================================


class TestSummaryMappings:
    """TDnet サマリー科目マッピングのテスト。"""

    # --- J-GAAP ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("NetSales", CK.REVENUE),
            ("Revenue", CK.REVENUE),
            ("OperatingIncome", CK.OPERATING_INCOME),
            ("OrdinaryIncome", CK.ORDINARY_INCOME),
            ("ProfitAttributableToOwnersOfParent", CK.NET_INCOME_PARENT),
            ("NetIncome", CK.NET_INCOME),
            ("ComprehensiveIncome", CK.COMPREHENSIVE_INCOME),
            ("TotalAssets", CK.TOTAL_ASSETS),
            ("NetAssets", CK.NET_ASSETS),
            ("CashFlowsFromOperatingActivities", CK.OPERATING_CF),
            ("CashFlowsFromInvestingActivities", CK.INVESTING_CF),
            ("CashFlowsFromFinancingActivities", CK.FINANCING_CF),
            ("CashAndEquivalentsEndOfPeriod", CK.CASH_END),
            ("NetIncomePerShare", CK.EPS),
            ("DilutedNetIncomePerShare", CK.EPS_DILUTED),
            ("NetAssetsPerShare", CK.BPS),
            ("DividendPerShare", CK.DPS),
            ("CapitalAdequacyRatio", CK.EQUITY_RATIO),
            ("NetIncomeToShareholdersEquityRatio", CK.ROE),
            ("PayoutRatio", CK.PAYOUT_RATIO),
        ],
    )
    def test_jgaap_summary(self, concept: str, expected_ck: str):
        """J-GAAP サマリー科目が正しく CK にマップされる。"""
        assert lookup_summary(concept) == expected_ck

    # --- IFRS ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("RevenueIFRS", CK.REVENUE),
            ("OperatingIncomeIFRS", CK.OPERATING_INCOME),
            ("ProfitBeforeTaxIFRS", CK.INCOME_BEFORE_TAX),
            ("ProfitIFRS", CK.NET_INCOME),
            ("ProfitAttributableToOwnersOfParentIFRS", CK.NET_INCOME_PARENT),
            ("TotalAssetsIFRS", CK.TOTAL_ASSETS),
            ("BasicEarningsPerShareIFRS", CK.EPS),
            ("CashFlowsFromOperatingActivitiesIFRS", CK.OPERATING_CF),
            ("EquityAttributableToOwnersOfParentToTotalAssetsRatioIFRS", CK.EQUITY_RATIO),
        ],
    )
    def test_ifrs_summary(self, concept: str, expected_ck: str):
        """IFRS サマリー科目が正しくマップされる。"""
        assert lookup_summary(concept) == expected_ck

    # --- US-GAAP ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("RevenuesUS", CK.REVENUE),
            ("NetSalesUS", CK.REVENUE),
            ("OperatingIncomeUS", CK.OPERATING_INCOME),
            ("IncomeBeforeIncomeTaxesUS", CK.INCOME_BEFORE_TAX),
            ("NetIncomeUS", CK.NET_INCOME_PARENT),
            ("TotalAssetsUS", CK.TOTAL_ASSETS),
            ("BasicNetIncomePerShareUS", CK.EPS),
        ],
    )
    def test_usgaap_summary(self, concept: str, expected_ck: str):
        """US-GAAP サマリー科目が正しくマップされる。"""
        assert lookup_summary(concept) == expected_ck

    # --- 変動率 ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("ChangeInNetSales", CK.CHANGE_REVENUE),
            ("ChangeInOperatingIncome", CK.CHANGE_OPERATING_INCOME),
            ("ChangeInOrdinaryIncome", CK.CHANGE_ORDINARY_INCOME),
            ("ChangeInProfitAttributableToOwnersOfParent", CK.CHANGE_NET_INCOME_PARENT),
        ],
    )
    def test_change_rate_summary(self, concept: str, expected_ck: str):
        """変動率サマリーが正しくマップされる。"""
        assert lookup_summary(concept) == expected_ck

    # --- 業種別 ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("OrdinaryRevenuesBK", CK.ORDINARY_REVENUE_BANKING),
            ("OrdinaryRevenuesIN", CK.ORDINARY_REVENUE_INSURANCE),
            ("NetOperatingRevenuesSE", CK.NET_OPERATING_REVENUE_SE),
        ],
    )
    def test_industry_summary(self, concept: str, expected_ck: str):
        """業種別サマリーが正しくマップされる。"""
        assert lookup_summary(concept) == expected_ck

    # --- エイリアス ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("OperatingRevenue", CK.REVENUE),
            ("ProfitLoss", CK.NET_INCOME),
            ("EarningsPerShare", CK.EPS),
            ("EquityRatio", CK.EQUITY_RATIO),
            ("NumberOfEmployees", CK.EMPLOYEES),
        ],
    )
    def test_alias_summary(self, concept: str, expected_ck: str):
        """エイリアスが正しくマップされる。"""
        assert lookup_summary(concept) == expected_ck

    # --- 存在しない概念 ---

    def test_unknown_concept_returns_none(self):
        """未知の概念は None を返す。"""
        assert lookup_summary("CompletelyUnknownConcept") is None

    def test_empty_concept_returns_none(self):
        """空文字は None を返す。"""
        assert lookup_summary("") is None

    # --- all_summary_mappings ---

    def test_all_summary_mappings_not_empty(self):
        """all_summary_mappings() は空でない。"""
        mappings = all_summary_mappings()
        assert len(mappings) > 50

    def test_all_summary_mappings_type(self):
        """全要素が SummaryMapping 型。"""
        for m in all_summary_mappings():
            assert isinstance(m, SummaryMapping)

    def test_all_summary_mappings_ck_valid(self):
        """全マッピングの canonical_key が CK メンバー。"""
        ck_values = frozenset(CK)
        for m in all_summary_mappings():
            assert m.canonical_key in ck_values, f"{m.concept} -> {m.canonical_key}"


# ============================================================
# statement_mappings
# ============================================================


class TestStatementMappings:
    """PL/BS/CF 本体のマッピングテスト。"""

    # --- J-GAAP PL ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("NetSales", CK.REVENUE),
            ("CostOfSales", CK.COST_OF_SALES),
            ("GrossProfit", CK.GROSS_PROFIT),
            ("SellingGeneralAndAdministrativeExpenses", CK.SGA_EXPENSES),
            ("OperatingIncome", CK.OPERATING_INCOME),
            ("OrdinaryIncome", CK.ORDINARY_INCOME),
            ("IncomeBeforeIncomeTaxes", CK.INCOME_BEFORE_TAX),
            ("ProfitLoss", CK.NET_INCOME),
            ("ProfitLossAttributableToOwnersOfParent", CK.NET_INCOME_PARENT),
        ],
    )
    def test_jgaap_pl(self, concept: str, expected_ck: str):
        assert lookup_statement_exact(concept) == expected_ck

    # --- J-GAAP BS ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("CashAndDeposits", CK.CASH_AND_DEPOSITS),
            ("CurrentAssets", CK.CURRENT_ASSETS),
            ("Assets", CK.TOTAL_ASSETS),
            ("CurrentLiabilities", CK.CURRENT_LIABILITIES),
            ("Liabilities", CK.TOTAL_LIABILITIES),
            ("CapitalStock", CK.CAPITAL_STOCK),
            ("RetainedEarnings", CK.RETAINED_EARNINGS),
            ("NetAssets", CK.NET_ASSETS),
        ],
    )
    def test_jgaap_bs(self, concept: str, expected_ck: str):
        assert lookup_statement_exact(concept) == expected_ck

    # --- J-GAAP CF ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("NetCashProvidedByUsedInOperatingActivities", CK.OPERATING_CF),
            ("NetCashProvidedByUsedInInvestmentActivities", CK.INVESTING_CF),
            ("NetCashProvidedByUsedInFinancingActivities", CK.FINANCING_CF),
            ("DepreciationAndAmortizationOpeCF", CK.DEPRECIATION_CF),
        ],
    )
    def test_jgaap_cf(self, concept: str, expected_ck: str):
        assert lookup_statement_exact(concept) == expected_ck

    # --- IFRS exact ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("FinanceIncome", CK.FINANCE_INCOME),
            ("FinanceCosts", CK.FINANCE_COSTS),
            ("ProfitLossBeforeTax", CK.INCOME_BEFORE_TAX),
            ("Profit", CK.NET_INCOME),
            ("OperatingProfit", CK.OPERATING_INCOME),
        ],
    )
    def test_ifrs_exact(self, concept: str, expected_ck: str):
        assert lookup_statement_exact(concept) == expected_ck

    # --- IFRS normalized (suffix removal) ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("FinanceIncomeIFRS", CK.FINANCE_INCOME),
            ("FinanceCostsIFRS", CK.FINANCE_COSTS),
            ("CostOfSalesIFRS", CK.COST_OF_SALES),
            ("ProfitLossBeforeTaxIFRS", CK.INCOME_BEFORE_TAX),
        ],
    )
    def test_ifrs_suffix_removal(self, concept: str, expected_ck: str):
        """IFRS サフィックスを除去して基底名でマッチする。"""
        assert lookup_statement_normalized(concept) == expected_ck

    # --- REIT suffix removal ---

    @pytest.mark.parametrize(
        "concept, expected_ck",
        [
            ("OperatingRevenuesREIT", CK.REVENUE),
            ("OperatingIncomeREIT", CK.OPERATING_INCOME),
            ("NetIncomeREIT", CK.NET_INCOME),
        ],
    )
    def test_reit_exact(self, concept: str, expected_ck: str):
        """REIT 科目が完全一致でマッチする。"""
        assert lookup_statement_exact(concept) == expected_ck

    # --- lookup_statement (combined) ---

    def test_lookup_statement_prefers_exact(self):
        """lookup_statement は完全一致を優先する。"""
        assert lookup_statement("FinanceIncome") == CK.FINANCE_INCOME

    def test_lookup_statement_falls_back_to_normalized(self):
        """lookup_statement は正規化にフォールバックする。"""
        assert lookup_statement("FinanceIncomeIFRS") == CK.FINANCE_INCOME

    def test_lookup_statement_unknown(self):
        """未知の概念は None。"""
        assert lookup_statement("TotallyUnknownXYZ") is None

    # --- サフィックス除去のエッジケース ---

    def test_suffix_removal_wont_match_suffix_only(self):
        """"IFRS" だけでは base が空でマッチしない。"""
        assert lookup_statement_normalized("IFRS") is None

    def test_suffix_removal_wont_match_nonexistent_base(self):
        """基底名が辞書に無い場合は None。"""
        assert lookup_statement_normalized("CompletelyFakeIFRS") is None
