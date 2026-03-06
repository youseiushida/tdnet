"""TDnet サマリー科目（tse-ed-t タクソノミ）の正規化キーマッピング。

tse-ed-t XSD (2014-01-12) に定義された全 138 財務型要素のうち、
CK にマッピング可能な概念を網羅的に登録する。

設計原則:
    - 全 concept が tse-ed-t XSD に実在（validate_against_xsd() で検証可能）
    - J-GAAP / IFRS / US-GAAP + 業種別（銀行・保険・証券）をカバー
    - edinet の summary_mappings.py と同じ lookup_summary() API を提供
"""

from __future__ import annotations

from dataclasses import dataclass

from tdnet.models.ck import CK

__all__ = [
    "SummaryMapping",
    "all_summary_mappings",
    "lookup_summary",
    "validate_against_xsd",
]


@dataclass(frozen=True, slots=True)
class SummaryMapping:
    """TDnet サマリー科目の CK マッピング。"""

    concept: str
    canonical_key: str


# ---------------------------------------------------------------------------
# J-GAAP PL（一般事業会社）
# ---------------------------------------------------------------------------

_JGAAP_PL: tuple[SummaryMapping, ...] = (
    SummaryMapping("NetSales", CK.REVENUE),
    SummaryMapping("Revenue", CK.REVENUE),
    SummaryMapping("Revenue2", CK.REVENUE),
    SummaryMapping("GrossOperatingRevenues", CK.REVENUE),
    SummaryMapping("NetSalesAndOperatingRevenues", CK.REVENUE),
    SummaryMapping("NetSalesOfCompletedConstructionContracts", CK.REVENUE),
    SummaryMapping("OperatingRevenues", CK.REVENUE),
    SummaryMapping("OperatingRevenuesSpecific", CK.REVENUE),
    SummaryMapping("OperatingIncome", CK.OPERATING_INCOME),
    SummaryMapping("OrdinaryIncome", CK.ORDINARY_INCOME),
    SummaryMapping("ProfitAttributableToOwnersOfParent", CK.NET_INCOME_PARENT),
    SummaryMapping("NetIncome", CK.NET_INCOME),
    SummaryMapping("ComprehensiveIncome", CK.COMPREHENSIVE_INCOME),
    SummaryMapping("InvestmentProfitLossOnEquityMethod", CK.EQUITY_METHOD_INCOME),
)

# ---------------------------------------------------------------------------
# J-GAAP BS / CF / KPI
# ---------------------------------------------------------------------------

_JGAAP_BS: tuple[SummaryMapping, ...] = (
    SummaryMapping("TotalAssets", CK.TOTAL_ASSETS),
    SummaryMapping("NetAssets", CK.NET_ASSETS),
    SummaryMapping("OwnersEquity", CK.SHAREHOLDERS_EQUITY),
)

_JGAAP_CF: tuple[SummaryMapping, ...] = (
    SummaryMapping("CashFlowsFromOperatingActivities", CK.OPERATING_CF),
    SummaryMapping("CashFlowsFromInvestingActivities", CK.INVESTING_CF),
    SummaryMapping("CashFlowsFromFinancingActivities", CK.FINANCING_CF),
    SummaryMapping("CashAndEquivalentsEndOfPeriod", CK.CASH_END),
)

_JGAAP_PER_SHARE: tuple[SummaryMapping, ...] = (
    SummaryMapping("NetIncomePerShare", CK.EPS),
    SummaryMapping("DilutedNetIncomePerShare", CK.EPS_DILUTED),
    SummaryMapping("NetAssetsPerShare", CK.BPS),
    SummaryMapping("DividendPerShare", CK.DPS),
    SummaryMapping("CommemorativeDividend", CK.COMMEMORATIVE_DIVIDEND),
    SummaryMapping("ExtraDividend", CK.EXTRA_DIVIDEND),
    SummaryMapping("TotalDividendPaidAnnual", CK.TOTAL_DIVIDEND_PAID),
)

_JGAAP_RATIOS: tuple[SummaryMapping, ...] = (
    SummaryMapping("CapitalAdequacyRatio", CK.EQUITY_RATIO),
    SummaryMapping("NetIncomeToShareholdersEquityRatio", CK.ROE),
    SummaryMapping("PayoutRatio", CK.PAYOUT_RATIO),
    SummaryMapping("OrdinaryIncomeToTotalAssetsRatio", CK.ROA),
    SummaryMapping("OperatingIncomeToNetSalesRatio", CK.OPERATING_MARGIN),
    SummaryMapping("NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock", CK.TOTAL_SHARES_ISSUED),
    SummaryMapping("NumberOfTreasuryStockAtTheEndOfFiscalYear", CK.TREASURY_STOCK_SHARES),
    SummaryMapping("AverageNumberOfShares", CK.AVERAGE_SHARES),
)

# ---------------------------------------------------------------------------
# 変動率（J-GAAP）
# ---------------------------------------------------------------------------

_JGAAP_CHANGES: tuple[SummaryMapping, ...] = (
    SummaryMapping("ChangeInNetSales", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInRevenue", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInRevenue2", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingRevenues", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingRevenuesSpecific", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInGrossOperatingRevenues", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInNetSalesAndOperatingRevenues", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInNetSalesOfCompletedConstructionContracts", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingIncome", CK.CHANGE_OPERATING_INCOME),
    SummaryMapping("ChangeInOrdinaryIncome", CK.CHANGE_ORDINARY_INCOME),
    SummaryMapping("ChangeInProfitAttributableToOwnersOfParent", CK.CHANGE_NET_INCOME_PARENT),
    SummaryMapping("ChangeInNetIncome", CK.CHANGE_NET_INCOME),
    SummaryMapping("ChangeInComprehensiveIncome", CK.CHANGE_COMPREHENSIVE_INCOME),
)

# ---------------------------------------------------------------------------
# 変動額（J-GAAP）
# ---------------------------------------------------------------------------

_JGAAP_AMOUNT_CHANGES: tuple[SummaryMapping, ...] = (
    SummaryMapping("AmountChangeNetSales", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOperatingIncome", CK.AMOUNT_CHANGE_OPERATING_INCOME),
    SummaryMapping("AmountChangeOrdinaryIncome", CK.AMOUNT_CHANGE_ORDINARY_INCOME),
    SummaryMapping("AmountChangeProfitAttributableToOwnersOfParent", CK.AMOUNT_CHANGE_NET_INCOME_PARENT),
    SummaryMapping("AmountChangeNetIncome", CK.AMOUNT_CHANGE_NET_INCOME),
    SummaryMapping("AmountChangeGrossOperatingRevenues", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeNetSalesAndOperatingRevenues", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeNetSalesOfCompletedConstructionContracts", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOperatingRevenues", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeRevenue", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeRevenue2", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOperatingRevenuesSpecific", CK.AMOUNT_CHANGE_REVENUE),
)

# ---------------------------------------------------------------------------
# IFRS サマリー
# ---------------------------------------------------------------------------

_IFRS: tuple[SummaryMapping, ...] = (
    # PL (XSD に実在する名前のみ)
    SummaryMapping("NetSalesIFRS", CK.REVENUE),
    SummaryMapping("RevenueIFRS", CK.REVENUE),
    SummaryMapping("OperatingIncomeIFRS", CK.OPERATING_INCOME),
    SummaryMapping("OperatingRevenuesIFRS", CK.REVENUE),
    SummaryMapping("SalesIFRS", CK.REVENUE),
    SummaryMapping("ProfitBeforeTaxIFRS", CK.INCOME_BEFORE_TAX),
    SummaryMapping("ProfitIFRS", CK.NET_INCOME),
    SummaryMapping("ProfitAttributableToOwnersOfParentIFRS", CK.NET_INCOME_PARENT),
    SummaryMapping("TotalComprehensiveIncomeIFRS", CK.COMPREHENSIVE_INCOME),
    # BS
    SummaryMapping("TotalAssetsIFRS", CK.TOTAL_ASSETS),
    SummaryMapping("TotalEquityIFRS", CK.NET_ASSETS),
    SummaryMapping("EquityAttributableToOwnersOfParentIFRS", CK.EQUITY_PARENT),
    # Per share
    SummaryMapping("BasicEarningsPerShareIFRS", CK.EPS),
    SummaryMapping("DilutedEarningsPerShareIFRS", CK.EPS_DILUTED),
    SummaryMapping("EquityAttributableToOwnersOfParentPerShareIFRS", CK.BPS),
    # CF
    SummaryMapping("CashFlowsFromOperatingActivitiesIFRS", CK.OPERATING_CF),
    SummaryMapping("CashFlowsFromInvestingActivitiesIFRS", CK.INVESTING_CF),
    SummaryMapping("CashFlowsFromFinancingActivitiesIFRS", CK.FINANCING_CF),
    SummaryMapping("CashAndCashEquivalentsAtEndOfPeriodIFRS", CK.CASH_END),
    # Equity method
    SummaryMapping("InvestmentsAccountedForUsingEquityMethodIFRS", CK.EQUITY_METHOD_INVESTMENTS),
    # IFRS changes / amount changes
    SummaryMapping("AmountChangeNetSalesIFRS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOperatingIncomeIFRS", CK.AMOUNT_CHANGE_OPERATING_INCOME),
    SummaryMapping("AmountChangeOperatingRevenuesIFRS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeProfitAttributableToOwnersOfParentIFRS", CK.AMOUNT_CHANGE_NET_INCOME_PARENT),
    SummaryMapping("AmountChangeProfitBeforeTaxIFRS", CK.AMOUNT_CHANGE_ORDINARY_INCOME),
    SummaryMapping("AmountChangeProfitIFRS", CK.AMOUNT_CHANGE_NET_INCOME),
    SummaryMapping("AmountChangeRevenueIFRS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeSalesIFRS", CK.AMOUNT_CHANGE_REVENUE),
    # IFRS ratios
    SummaryMapping("OperatingIncomeToRevenueRatioIFRS", CK.OPERATING_MARGIN),
    SummaryMapping("OperatingIncomeToOperatingRevenuesRatioIFRS", CK.OPERATING_MARGIN),
    SummaryMapping("ProfitBeforeTaxToRevenueRatioIFRS", CK.PRETAX_MARGIN),
    SummaryMapping("ProfitBeforeTaxToOperatingRevenuesRatioIFRS", CK.PRETAX_MARGIN),
    SummaryMapping("ProfitToRevenueRatioIFRS", CK.NET_INCOME_MARGIN),
    SummaryMapping("ProfitToOperatingRevenuesRatioIFRS", CK.NET_INCOME_MARGIN),
    SummaryMapping("ProfitToEquityAttributableToOwnersOfParentRatioIFRS", CK.ROE),
    SummaryMapping("ProfitBeforeTaxToTotalAssetsRatioIFRS", CK.ROA),
    SummaryMapping("ProfitToTotalAssetsRatioIFRS", CK.ROA),
    SummaryMapping("EquityAttributableToOwnersOfParentToTotalAssetsRatioIFRS", CK.EQUITY_RATIO),
    SummaryMapping("PayoutRatioIFRS", CK.PAYOUT_RATIO),
    SummaryMapping("RatioOfTotalAmountOfDividendsToEquityAttributableToOwnerOfParentConsolidatedIFRS", CK.DIVIDEND_TO_EQUITY_RATIO),
    SummaryMapping("OperatingIncomeToOrdinaryRevenuesRatioBKIFRS", CK.OPERATING_MARGIN),
    SummaryMapping("ProfitBeforeTaxToOrdinaryRevenuesRatioBKIFRS", CK.PRETAX_MARGIN),
    SummaryMapping("ProfitToOrdinaryRevenuesRatioBKIFRS", CK.NET_INCOME_MARGIN),
    # IFRS change rates
    SummaryMapping("ChangeInRevenueIFRS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInNetSalesIFRS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInSalesIFRS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingRevenuesIFRS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingIncomeIFRS", CK.CHANGE_OPERATING_INCOME),
    SummaryMapping("ChangeInProfitAttributableToOwnersOfParentIFRS", CK.CHANGE_NET_INCOME_PARENT),
    SummaryMapping("ChangeInProfitBeforeTaxIFRS", CK.CHANGE_ORDINARY_INCOME),
    SummaryMapping("ChangeInProfitIFRS", CK.CHANGE_NET_INCOME),
    SummaryMapping("ChangesInTotalComprehensiveIncomeIFRS", CK.CHANGE_COMPREHENSIVE_INCOME),
)

# ---------------------------------------------------------------------------
# US-GAAP サマリー
# ---------------------------------------------------------------------------

_USGAAP: tuple[SummaryMapping, ...] = (
    # PL
    SummaryMapping("GrossRevenuesUS", CK.REVENUE),
    SummaryMapping("NetSalesUS", CK.REVENUE),
    SummaryMapping("NetSalesAndOperatingRevenuesUS", CK.REVENUE),
    SummaryMapping("OperatingRevenuesUS", CK.REVENUE),
    SummaryMapping("OperatingRevenuesSpecificUS", CK.REVENUE),
    SummaryMapping("RevenuesUS", CK.REVENUE),
    SummaryMapping("TotalRevenuesUS", CK.REVENUE),
    SummaryMapping("TotalRevenuesAfterDeductingFinancialExpenseUS", CK.REVENUE),
    SummaryMapping("OperatingIncomeUS", CK.OPERATING_INCOME),
    SummaryMapping("IncomeBeforeIncomeTaxesUS", CK.INCOME_BEFORE_TAX),
    SummaryMapping("IncomeFromContinuingOperationsBeforeIncomeTaxesUS", CK.INCOME_BEFORE_TAX),
    SummaryMapping("IncomeFromDiscontinuingOperationsBeforeIncomeTaxesUS", CK.INCOME_BEFORE_TAX),
    SummaryMapping("IncomeBeforeMinorityInterestUS", CK.NET_INCOME),
    SummaryMapping("NetIncomeUS", CK.NET_INCOME_PARENT),
    SummaryMapping("ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterestUS", CK.COMPREHENSIVE_INCOME),
    SummaryMapping("ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterest1US", CK.COMPREHENSIVE_INCOME),
    SummaryMapping("ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterest2US", CK.COMPREHENSIVE_INCOME),
    SummaryMapping("ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterest3US", CK.COMPREHENSIVE_INCOME),
    SummaryMapping("ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterest4US", CK.COMPREHENSIVE_INCOME),
    SummaryMapping("ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterest5US", CK.COMPREHENSIVE_INCOME),
    SummaryMapping("ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterest6US", CK.COMPREHENSIVE_INCOME),
    SummaryMapping("InvestmentProfitLossOnEquityMethodUS", CK.EQUITY_METHOD_INCOME),
    # BS
    SummaryMapping("TotalAssetsUS", CK.TOTAL_ASSETS),
    SummaryMapping("NetAssetsUS", CK.NET_ASSETS),
    SummaryMapping("ShareholdersEquityUS", CK.SHAREHOLDERS_EQUITY),
    # Per share
    SummaryMapping("BasicNetIncomePerShareUS", CK.EPS),
    SummaryMapping("NetIncomePerShareUS", CK.EPS),
    SummaryMapping("DilutedNetIncomePerShareUS", CK.EPS_DILUTED),
    SummaryMapping("DilutedNetIncomePerShare2US", CK.EPS_DILUTED),
    SummaryMapping("NetAssetsPerShareUS", CK.BPS),
    SummaryMapping("ShareholdersEquityPerShareUS", CK.BPS),
    # CF
    SummaryMapping("CashFlowsFromOperatingActivitiesUS", CK.OPERATING_CF),
    SummaryMapping("CashFlowsFromOperatingActivitiesContinuingOperationsUS", CK.OPERATING_CF),
    SummaryMapping("CashFlowsFromInvestingActivitiesUS", CK.INVESTING_CF),
    SummaryMapping("CashFlowsFromInvestingActivitiesContinuingOperationsUS", CK.INVESTING_CF),
    SummaryMapping("CashFlowsFromFinancingActivitiesUS", CK.FINANCING_CF),
    SummaryMapping("CashFlowsFromFinancingActivitiesContinuingOperationsUS", CK.FINANCING_CF),
    SummaryMapping("CashAndEquivalentsEndOfPeriodUS", CK.CASH_END),
    SummaryMapping("CashAndEquivalentsEndOfPeriod1US", CK.CASH_END),
    # US-GAAP changes
    SummaryMapping("AmountChangeGrossRevenuesUS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeIncomeBeforeIncomeTaxesUS", CK.AMOUNT_CHANGE_ORDINARY_INCOME),
    SummaryMapping("AmountChangeIncomeBeforeMinorityInterestUS", CK.AMOUNT_CHANGE_NET_INCOME),
    SummaryMapping("AmountChangeIncomeFromContinuingOperationsBeforeIncomeTaxesUS", CK.AMOUNT_CHANGE_ORDINARY_INCOME),
    SummaryMapping("AmountChangeIncomeFromDiscontinuingOperationsBeforeIncomeTaxesUS", CK.AMOUNT_CHANGE_ORDINARY_INCOME),
    SummaryMapping("AmountChangeNetIncomeUS", CK.AMOUNT_CHANGE_NET_INCOME_PARENT),
    SummaryMapping("AmountChangeNetSalesUS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeNetSalesAndOperatingRevenuesUS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOperatingIncomeUS", CK.AMOUNT_CHANGE_OPERATING_INCOME),
    SummaryMapping("AmountChangeOperatingRevenuesUS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOperatingRevenuesSpecificUS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeRevenuesUS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeTotalRevenuesUS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeTotalRevenuesAfterDeductingFinancialExpenseUS", CK.AMOUNT_CHANGE_REVENUE),
    # US-GAAP change rates
    SummaryMapping("ChangeInNetSalesUS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInNetSalesAndOperatingRevenuesUS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingRevenuesUS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingRevenuesSpecificUS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInRevenuesUS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInTotalRevenuesUS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInGrossRevenuesUS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInTotalRevenuesAfterDeductingFinancialExpenseUS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingIncomeUS", CK.CHANGE_OPERATING_INCOME),
    SummaryMapping("ChangeInIncomeBeforeIncomeTaxesUS", CK.CHANGE_INCOME_BEFORE_TAX),
    SummaryMapping("ChangeInIncomeFromContinuingOperationsBeforeIncomeTaxesUS", CK.CHANGE_INCOME_BEFORE_TAX),
    SummaryMapping("ChangeInIncomeFromDiscontinuingOperationsBeforeIncomeTaxesUS", CK.CHANGE_INCOME_BEFORE_TAX),
    SummaryMapping("ChangeInIncomeBeforeMinorityInterestUS", CK.CHANGE_NET_INCOME),
    SummaryMapping("ChangeInNetIncomeUS", CK.CHANGE_NET_INCOME_PARENT),
    # US-GAAP ratios
    SummaryMapping("NetIncomeToShareholdersEquityRatioUS", CK.ROE),
    SummaryMapping("NetIncomeToShareholdersEquityRatioUS2", CK.ROE),
    SummaryMapping("IncomeBeforeMinorityInterestToConsolidatedEquityRatioUS", CK.ROE),
    SummaryMapping("IncomeBeforeIncomeTaxesToTotalAssetsRatioUS", CK.ROA),
    SummaryMapping("ShareholdersEquityRatioUS", CK.EQUITY_RATIO),
    SummaryMapping("CapitalAdequacyRatioUS", CK.EQUITY_RATIO),
    SummaryMapping("PayoutRatioUS", CK.PAYOUT_RATIO),
    SummaryMapping("RatioOfTotalAmountOfDividendsToNetAssets", CK.DIVIDEND_TO_EQUITY_RATIO),
    SummaryMapping("RatioOfTotalAmountOfDividendsToNetAssetsUS", CK.DIVIDEND_TO_EQUITY_RATIO),
    SummaryMapping("RatioOfTotalAmountOfDividendsToShareholdersEquityUS", CK.DIVIDEND_TO_EQUITY_RATIO),
)

# ---------------------------------------------------------------------------
# 業種別（銀行・保険・証券）
# ---------------------------------------------------------------------------

_INDUSTRY: tuple[SummaryMapping, ...] = (
    # Banking
    SummaryMapping("OrdinaryRevenuesBK", CK.ORDINARY_REVENUE_BANKING),
    SummaryMapping("DepositsBK", CK.DEPOSITS),
    SummaryMapping("OrdinaryRevenuesBKIFRS", CK.ORDINARY_REVENUE_BANKING),
    # Insurance
    SummaryMapping("OrdinaryRevenuesIN", CK.ORDINARY_REVENUE_INSURANCE),
    SummaryMapping("NetPremiumsWrittenIN", CK.NET_PREMIUMS_WRITTEN),
    # Securities
    SummaryMapping("NetOperatingRevenuesSE", CK.NET_OPERATING_REVENUE_SE),
    SummaryMapping("OperatingRevenuesSE", CK.OPERATING_REVENUE_SE),
    # Banking/Insurance/Securities amount changes
    SummaryMapping("AmountChangeOrdinaryRevenuesBK", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOrdinaryRevenuesBKIFRS", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOrdinaryRevenuesIN", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeNetPremiumsWrittenIN", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeNetOperatingRevenuesSE", CK.AMOUNT_CHANGE_REVENUE),
    SummaryMapping("AmountChangeOperatingRevenuesSE", CK.AMOUNT_CHANGE_REVENUE),
    # Banking/Insurance/Securities change rates
    SummaryMapping("ChangeInOrdinaryRevenuesBK", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOrdinaryRevenuesBKIFRS", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOrdinaryRevenuesIN", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInNetPremiumsWrittenIN", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInNetOperatingRevenuesSE", CK.CHANGE_REVENUE),
    SummaryMapping("ChangeInOperatingRevenuesSE", CK.CHANGE_REVENUE),
    # Insurance ratios
    SummaryMapping("LossRatioIN", CK.NET_LOSS_RATIO),
    SummaryMapping("ExpenseRatioIN", CK.NET_OPERATING_EXPENSE_RATIO),
    # Securities
    SummaryMapping("CapitalAdequacyRatioSecuritiesExchangeAct523SE", CK.CAPITAL_ADEQUACY_SE),
    SummaryMapping("NetOperatingIncomeToOperatingRevenuesRatioSE", CK.OPERATING_MARGIN),
    # Banking capital adequacy
    SummaryMapping("ConsolidatedCapitalAdequacyRatioBISBK", CK.CAPITAL_ADEQUACY_RATIO_BIS),
    SummaryMapping("ConsolidatedCapitalAdequacyRatioBIS1stBK", CK.CAPITAL_ADEQUACY_RATIO_INTERNATIONAL),
    SummaryMapping("ConsolidatedCapitalAdequacyRatioDomesticBK", CK.CAPITAL_ADEQUACY_RATIO_DOMESTIC),
    SummaryMapping("ConsolidatedCapitalAdequacyRatioDomestic2ndBK", CK.CAPITAL_ADEQUACY_RATIO_DOMESTIC_2),
    SummaryMapping("ConsolidatedCapitalAdequacyRatioBISBKIFRS", CK.CAPITAL_ADEQUACY_RATIO_BIS),
    SummaryMapping("ConsolidatedCapitalAdequacyRatioBIS1stBKIFRS", CK.CAPITAL_ADEQUACY_RATIO_INTERNATIONAL),
    SummaryMapping("ConsolidatedCapitalAdequacyRatioDomesticBKIFRS", CK.CAPITAL_ADEQUACY_RATIO_DOMESTIC),
    SummaryMapping("ConsolidatedCapitalAdequacyRatioDomestic2ndBKIFRS", CK.CAPITAL_ADEQUACY_RATIO_DOMESTIC_2),
    SummaryMapping("NonConsolidatedCapitalAdequacyRatioBISBK", CK.CAPITAL_ADEQUACY_RATIO_BIS),
    SummaryMapping("NonConsolidatedCapitalAdequacyRatioDomesticBK", CK.CAPITAL_ADEQUACY_RATIO_DOMESTIC),
)

# ---------------------------------------------------------------------------
# メタデータ・子会社数
# ---------------------------------------------------------------------------

_METADATA: tuple[SummaryMapping, ...] = (
    SummaryMapping("QuarterlyPeriod", CK.QUARTERLY_PERIOD),
    SummaryMapping("NumberOfSubsidiariesNewlyConsolidated", CK.SUBSIDIARIES_NEWLY_CONSOLIDATED),
    SummaryMapping("NumberOfSubsidiariesExcludedFromConsolidation", CK.SUBSIDIARIES_EXCLUDED),
    SummaryMapping("NumberOfSubsidiariesNewlyConsolidatedUS", CK.SUBSIDIARIES_NEWLY_CONSOLIDATED),
    SummaryMapping("NumberOfSubsidiariesExcludedFromConsolidationUS", CK.SUBSIDIARIES_EXCLUDED),
    SummaryMapping("NumberOfSubsidiariesNewlyConsolidatedIFRS", CK.SUBSIDIARIES_NEWLY_CONSOLIDATED),
    SummaryMapping("NumberOfSubsidiariesExcludedFromConsolidationIFRS", CK.SUBSIDIARIES_EXCLUDED),
)


# ---------------------------------------------------------------------------
# 統合レジストリとインデックス
# ---------------------------------------------------------------------------

_ALL_MAPPINGS: tuple[SummaryMapping, ...] = (
    *_JGAAP_PL,
    *_JGAAP_BS,
    *_JGAAP_CF,
    *_JGAAP_PER_SHARE,
    *_JGAAP_RATIOS,
    *_JGAAP_CHANGES,
    *_JGAAP_AMOUNT_CHANGES,
    *_IFRS,
    *_USGAAP,
    *_INDUSTRY,
    *_METADATA,
)

_CONCEPT_INDEX: dict[str, SummaryMapping] = {
    m.concept: m for m in _ALL_MAPPINGS
}

# ---------------------------------------------------------------------------
# エイリアス（XSD に実在しないが実データで使われる名前）
# XSD 検証からは除外される。
# ---------------------------------------------------------------------------

_ALIASES: dict[str, str] = {
    # jppfs_cor 名前空間で出現する同名概念をフォールバック
    "OperatingRevenue": CK.REVENUE,
    "OperatingRevenue1": CK.REVENUE,
    "OperatingProfit": CK.OPERATING_INCOME,
    "IncomeBeforeIncomeTaxes": CK.INCOME_BEFORE_TAX,
    "ProfitLoss": CK.NET_INCOME,
    "CashAndCashEquivalents": CK.CASH_AND_EQUIVALENTS,
    "CashAndCashEquivalentsAtEndOfPeriod": CK.CASH_END,
    "EarningsPerShare": CK.EPS,
    "DilutedEarningsPerShare": CK.EPS_DILUTED,
    "BookValuePerShare": CK.BPS,
    "EquityRatio": CK.EQUITY_RATIO,
    "EquityToAssetRatio": CK.EQUITY_RATIO,
    "ReturnOnEquity": CK.ROE,
    "RateOfReturnOnEquity": CK.ROE,
    "PriceEarningsRatio": CK.PER,
    "NumberOfEmployees": CK.EMPLOYEES,
    "TotalNumberOfIssuedShares": CK.TOTAL_SHARES_ISSUED,
    # IFRS KeyFinancialData 短縮名（一部の企業で使用）
    "Revenue1IFRSKeyFinancialData": CK.REVENUE,
    "RevenueIFRSKeyFinancialData": CK.REVENUE,
    "ProfitLossBeforeTaxIFRSKeyFinancialData": CK.INCOME_BEFORE_TAX,
    "ProfitLossIFRSKeyFinancialData": CK.NET_INCOME,
    "ProfitLossAttributableToOwnersOfParentIFRSKeyFinancialData": CK.NET_INCOME_PARENT,
    "ComprehensiveIncomeIFRSKeyFinancialData": CK.COMPREHENSIVE_INCOME,
    "TotalAssetsIFRSKeyFinancialData": CK.TOTAL_ASSETS,
    "EquityAttributableToOwnersOfParentIFRSKeyFinancialData": CK.EQUITY_PARENT,
    "BasicEarningsPerShareIFRSKeyFinancialData": CK.EPS,
    "DilutedEarningsPerShareIFRSKeyFinancialData": CK.EPS_DILUTED,
    "RatioOfOwnersEquityToGrossAssetsIFRSKeyFinancialData": CK.EQUITY_RATIO,
    "RateOfReturnOnEquityIFRSKeyFinancialData": CK.ROE,
    "PriceEarningsRatioIFRSKeyFinancialData": CK.PER,
    "CashFlowsFromOperatingActivitiesIFRSKeyFinancialData": CK.OPERATING_CF,
    "CashFlowsFromInvestingActivitiesIFRSKeyFinancialData": CK.INVESTING_CF,
    "CashFlowsFromFinancingActivitiesIFRSKeyFinancialData": CK.FINANCING_CF,
    "CashAndCashEquivalentsIFRSKeyFinancialData": CK.CASH_END,
    # US-GAAP aliases
    "ShareholdersEquityIncludingPortionAttributableToNoncontrollingInterest1US": CK.NET_ASSETS,
    "ShareholdersEquityIncludingPortionAttributableToNoncontrollingInterest2US": CK.NET_ASSETS,
}

# エイリアスを統合インデックスに追加（XSD登録分が優先）
for _alias, _ck in _ALIASES.items():
    if _alias not in _CONCEPT_INDEX:
        _CONCEPT_INDEX[_alias] = SummaryMapping(_alias, _ck)


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def lookup_summary(concept: str) -> str | None:
    """TDnet サマリー concept から CK を返す。"""
    m = _CONCEPT_INDEX.get(concept)
    return m.canonical_key if m is not None else None


def all_summary_mappings() -> tuple[SummaryMapping, ...]:
    """XSD に実在する全 SummaryMapping を返す。"""
    return _ALL_MAPPINGS


def validate_against_xsd(xsd_path: str | None = None) -> list[str]:
    """マッピングの全 concept が XSD に実在するか検証する。

    エイリアス（_ALIASES）は検証対象外。

    Args:
        xsd_path: tse-ed-t XSD のパス。None の場合はバンドルを検索。

    Returns:
        XSD に存在しない concept 名のリスト（空なら全OK）。
    """
    from lxml import etree

    from tdnet.xbrl.taxonomy import bundled_xsd_path

    if xsd_path is None:
        bundled = bundled_xsd_path()
        if bundled is not None:
            xsd_path = str(bundled)
        else:
            raise FileNotFoundError(
                "tse-ed-t XSD not found. Specify xsd_path or install tdnet with bundled taxonomy."
            )

    tree = etree.parse(xsd_path)
    ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
    xsd_elements = set(tree.xpath("//xs:element/@name", namespaces=ns))

    missing = []
    for m in _ALL_MAPPINGS:  # エイリアスは除外
        if m.concept not in xsd_elements:
            missing.append(m.concept)
    return missing
