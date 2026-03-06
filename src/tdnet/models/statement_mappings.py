"""PL/BS/CF 本体の concept → CK マッピング。

決算短信 Attachment 部分で使用される jppfs_cor / IFRS / US-GAAP タクソノミの
concept を CK にマッピングする。

jppfs_cor は EDINET と共通タクソノミのため、
edinet の statement_mappings.py から主要概念を移植。
IFRS / US-GAAP / REIT 固有概念も網羅。
"""

from __future__ import annotations

from tdnet.models.ck import CK

__all__ = [
    "lookup_statement",
    "lookup_statement_exact",
    "lookup_statement_normalized",
]


# ---------------------------------------------------------------------------
# J-GAAP PL（jppfs_cor）
# ---------------------------------------------------------------------------

_JGAAP_PL: dict[str, str] = {
    "NetSales": CK.REVENUE,
    "Revenue": CK.REVENUE,
    "RevenueFromContractsWithCustomers": CK.REVENUE,
    "CostOfSales": CK.COST_OF_SALES,
    "GrossProfit": CK.GROSS_PROFIT,
    "SellingGeneralAndAdministrativeExpenses": CK.SGA_EXPENSES,
    "OperatingIncome": CK.OPERATING_INCOME,
    "NonOperatingIncome": CK.NON_OPERATING_INCOME,
    "NonOperatingExpenses": CK.NON_OPERATING_EXPENSES,
    "InterestIncomeNOI": CK.INTEREST_INCOME_PL,
    "DividendsIncomeNOI": CK.DIVIDEND_INCOME,
    "InterestExpensesNOE": CK.INTEREST_EXPENSE_PL,
    "DepreciationNOE": CK.DEPRECIATION_SGA,
    "OrdinaryIncome": CK.ORDINARY_INCOME,
    "ExtraordinaryIncome": CK.EXTRAORDINARY_INCOME,
    "ExtraordinaryLoss": CK.EXTRAORDINARY_LOSS,
    "IncomeBeforeIncomeTaxes": CK.INCOME_BEFORE_TAX,
    "IncomeTaxes": CK.INCOME_TAXES,
    "IncomeTaxesCurrent": CK.INCOME_TAXES,
    "IncomeTaxesDeferred": CK.INCOME_TAXES_DEFERRED,
    "ProfitLoss": CK.NET_INCOME,
    "ProfitLossAttributableToOwnersOfParent": CK.NET_INCOME_PARENT,
    "ProfitLossAttributableToNonControllingInterests": CK.NET_INCOME_MINORITY,
    # CI
    "ComprehensiveIncome": CK.COMPREHENSIVE_INCOME,
    "ComprehensiveIncomeAttributableToOwnersOfTheParent": CK.COMPREHENSIVE_INCOME_PARENT,
    "ComprehensiveIncomeAttributableToNonControllingInterests": CK.COMPREHENSIVE_INCOME_MINORITY,
    "OtherComprehensiveIncome": CK.OCI_ACCUMULATED,
    # NOI/NOE/EI/EL detail
    "EquityInEarningsOfAffiliatesNOI": CK.EQUITY_METHOD_INCOME,
    "ImpairmentLossEL": CK.IMPAIRMENT_LOSS_PL,
    # SGA detail
    "DepreciationSGA": CK.DEPRECIATION_SGA,
    "ResearchAndDevelopmentExpensesSGA": CK.RD_EXPENSES,
}

# ---------------------------------------------------------------------------
# J-GAAP BS（jppfs_cor）
# ---------------------------------------------------------------------------

_JGAAP_BS: dict[str, str] = {
    # CA
    "CashAndDeposits": CK.CASH_AND_DEPOSITS,
    "CashAndCashEquivalents": CK.CASH_AND_EQUIVALENTS,
    "NotesAndAccountsReceivableTrade": CK.TRADE_RECEIVABLES,
    "NotesAndAccountsReceivableTradeAndContractAssets": CK.TRADE_RECEIVABLES,
    "AccountsReceivableTrade": CK.TRADE_RECEIVABLES,
    "AccountsReceivableTradeAndContractAssets": CK.TRADE_RECEIVABLES,
    "ElectronicallyRecordedMonetaryClaimsOperatingCA": CK.TRADE_RECEIVABLES,
    "NotesReceivableTrade": CK.NOTES_RECEIVABLE,
    "Inventories": CK.INVENTORIES,
    "PrepaidExpenses": CK.PREPAID_EXPENSES,
    "ContractAssets": CK.CONTRACT_ASSETS,
    "ContractAssetsNet": CK.CONTRACT_ASSETS,
    "CurrentAssets": CK.CURRENT_ASSETS,
    # NCA - PPE
    "PropertyPlantAndEquipment": CK.PPE,
    "Land": CK.LAND,
    "BuildingsNet": CK.BUILDINGS_NET,
    "ConstructionInProgress": CK.CONSTRUCTION_IN_PROGRESS,
    # NCA - IA
    "IntangibleAssets": CK.INTANGIBLE_ASSETS,
    "Goodwill": CK.GOODWILL,
    # NCA - IOA
    "InvestmentSecurities": CK.INVESTMENT_SECURITIES,
    "InvestmentsAndOtherAssets": CK.INVESTMENTS_AND_OTHER,
    "NoncurrentAssets": CK.NONCURRENT_ASSETS,
    "Assets": CK.TOTAL_ASSETS,
    # CL
    "NotesAndAccountsPayableTrade": CK.TRADE_PAYABLES,
    "AccountsPayableTrade": CK.TRADE_PAYABLES,
    "ElectronicallyRecordedObligationsOperatingCL": CK.TRADE_PAYABLES,
    "ContractLiabilities": CK.CONTRACT_LIABILITIES,
    "AdvancesReceived": CK.CONTRACT_LIABILITIES,
    "ShortTermLoansPayable": CK.SHORT_TERM_LOANS,
    "CurrentPortionOfLongTermLoansPayable": CK.CURRENT_PORTION_OF_LONG_TERM_LOANS,
    "ProvisionForBonuses": CK.PROVISIONS_CL,
    "CurrentLiabilities": CK.CURRENT_LIABILITIES,
    # NCL
    "LongTermLoansPayable": CK.LONG_TERM_LOANS,
    "BondsPayable": CK.BONDS_PAYABLE,
    "ProvisionForRetirementBenefits": CK.RETIREMENT_BENEFIT_LIABILITY,
    "NoncurrentLiabilities": CK.NONCURRENT_LIABILITIES,
    "Liabilities": CK.TOTAL_LIABILITIES,
    # NA
    "CapitalStock": CK.CAPITAL_STOCK,
    "CapitalSurplus": CK.CAPITAL_SURPLUS,
    "RetainedEarnings": CK.RETAINED_EARNINGS,
    "TreasuryStock": CK.TREASURY_STOCK,
    "ShareholdersEquity": CK.SHAREHOLDERS_EQUITY,
    "ValuationAndTranslationAdjustments": CK.OCI_ACCUMULATED,
    "SubscriptionRightsToShares": CK.SUBSCRIPTION_RIGHTS,
    "NonControllingInterests": CK.MINORITY_INTERESTS,
    "NetAssets": CK.NET_ASSETS,
    "LiabilitiesAndNetAssets": CK.LIABILITIES_AND_NET_ASSETS,
    "DeferredTaxAssets": CK.DEFERRED_TAX_ASSETS,
    "DeferredTaxLiabilities": CK.DEFERRED_TAX_LIABILITIES,
}

# ---------------------------------------------------------------------------
# J-GAAP CF（jppfs_cor）
# ---------------------------------------------------------------------------

_JGAAP_CF: dict[str, str] = {
    "DepreciationAndAmortizationOpeCF": CK.DEPRECIATION_CF,
    "ImpairmentLossOpeCF": CK.IMPAIRMENT_LOSS_CF,
    "AmortizationOfGoodwillOpeCF": CK.GOODWILL_AMORTIZATION_CF,
    "IncreaseDecreaseInAllowanceForDoubtfulAccountsOpeCF": CK.ALLOWANCE_DOUBTFUL_CHANGE_CF,
    "InterestAndDividendsIncomeOpeCF": CK.INTEREST_DIVIDEND_INCOME_CF,
    "InterestAndDividendsIncomeReceivedOpeCFInvCF": CK.INTEREST_DIVIDEND_INCOME_CF,
    "InterestExpensesOpeCF": CK.INTEREST_EXPENSE_CF,
    "ForeignExchangeLossesGainsOpeCF": CK.FX_LOSS_GAIN_CF,
    "EquityInEarningsLossesOfAffiliatesOpeCF": CK.EQUITY_METHOD_CF,
    "LossGainOnSalesOfPropertyPlantAndEquipmentOpeCF": CK.PPE_SALE_LOSS_GAIN_CF,
    "LossGainOnSalesOfInvestmentSecuritiesOpeCF": CK.PPE_SALE_LOSS_GAIN_CF,
    "DecreaseIncreaseInNotesAndAccountsReceivableTradeOpeCF": CK.TRADE_RECEIVABLES_CHANGE_CF,
    "DecreaseIncreaseInAccountsReceivableTradeAndContractAssetsOpeCF": CK.TRADE_RECEIVABLES_CHANGE_CF,
    "DecreaseIncreaseInInventoriesOpeCF": CK.INVENTORIES_CHANGE_CF,
    "IncreaseDecreaseInNotesAndAccountsPayableTradeOpeCF": CK.TRADE_PAYABLES_CHANGE_CF,
    "DecreaseIncreaseInAdvancePaymentsOpeCF": CK.OTHER_OPERATING_CF,
    "IncreaseDecreaseInAdvancesReceivedOpeCF": CK.OTHER_OPERATING_CF,
    "BadDebtsExpensesOpeCF": CK.OTHER_OPERATING_CF,
    "OtherNetOpeCF": CK.OTHER_OPERATING_CF,
    "SubtotalOpeCF": CK.SUBTOTAL_OPERATING_CF,
    "IncomeTaxesPaidOpeCF": CK.INCOME_TAXES_PAID_CF,
    "SubsidyIncomeOpeCF": CK.OTHER_OPERATING_CF,
    "NetCashProvidedByUsedInOperatingActivities": CK.OPERATING_CF,
    "PurchaseOfPropertyPlantAndEquipmentInvCF": CK.PURCHASE_PPE_CF,
    "PurchaseOfPropertyPlantAndEquipmentAndIntangibleAssetsInvCF": CK.PURCHASE_PPE_CF,
    "PurchaseOfIntangibleAssetsInvCF": CK.PURCHASE_PPE_CF,
    "ProceedsFromSalesOfPropertyPlantAndEquipmentInvCF": CK.PROCEEDS_PPE_SALE_CF,
    "PurchaseOfInvestmentSecuritiesInvCF": CK.PURCHASE_INVESTMENT_SECURITIES_CF,
    "ProceedsFromSalesOfInvestmentSecuritiesInvCF": CK.PROCEEDS_INVESTMENT_SECURITIES_CF,
    "SubsidiesReceivedInvCF": CK.OTHER_INVESTING_CF,
    "OtherNetInvCF": CK.OTHER_INVESTING_CF,
    "NetCashProvidedByUsedInInvestmentActivities": CK.INVESTING_CF,
    "ProceedsFromLongTermLoansPayableFinCF": CK.PROCEEDS_LONG_TERM_LOANS_CF,
    "RepaymentOfLongTermLoansPayableFinCF": CK.REPAYMENT_LONG_TERM_LOANS_CF,
    "PurchaseOfTreasuryStockFinCF": CK.PURCHASE_TREASURY_STOCK_CF,
    "CashDividendsPaidFinCF": CK.DIVIDENDS_PAID_CF,
    "OtherNetFinCF": CK.OTHER_FINANCING_CF,
    "NetCashProvidedByUsedInFinancingActivities": CK.FINANCING_CF,
    "EffectOfExchangeRateChangeOnCashAndCashEquivalents": CK.FX_EFFECT_ON_CASH,
    "NetIncreaseDecreaseInCashAndCashEquivalents": CK.NET_CHANGE_IN_CASH,
}

# ---------------------------------------------------------------------------
# jpcrp_cor（セグメント情報）
# ---------------------------------------------------------------------------

_JPCRP: dict[str, str] = {
    "RevenuesFromExternalCustomers": CK.REVENUE,
}


# ---------------------------------------------------------------------------
# IFRS PL/BS/CF（ifrs / jpigp_cor タクソノミ）
# ---------------------------------------------------------------------------

_IFRS_PL: dict[str, str] = {
    # PL — 基底名（サフィックス除去でもマッチ）
    "OtherIncome": CK.OTHER_INCOME_IFRS,
    "OtherExpenses": CK.OTHER_EXPENSES_IFRS,
    "OtherExpense": CK.OTHER_EXPENSES_IFRS,
    "FinanceIncome": CK.FINANCE_INCOME,
    "OtherFinanceIncome": CK.FINANCE_INCOME,
    "FinanceCosts": CK.FINANCE_COSTS,
    "OtherFinanceCosts": CK.FINANCE_COSTS,
    "FinanceRevenue": CK.FINANCE_INCOME,
    "FinanceExpenses": CK.FINANCE_COSTS,
    "OperatingProfit": CK.OPERATING_INCOME,
    "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": CK.EQUITY_METHOD_INCOME_IFRS,
    "ShareOfProfitLossOfInvestmentsAccountedForUsingEquityMethod": CK.EQUITY_METHOD_INCOME_IFRS,
    "ProfitLossBeforeTax": CK.INCOME_BEFORE_TAX,
    "ProfitBeforeIncomeTax": CK.INCOME_BEFORE_TAX,
    "ProfitBeforeTax": CK.INCOME_BEFORE_TAX,
    "IncomeTaxExpense": CK.INCOME_TAXES,
    "ProfitAttributableToOwnersOfParent": CK.NET_INCOME_PARENT,
    "Profit": CK.NET_INCOME,
    "NetIncome": CK.NET_INCOME,
    "TotalAssets": CK.TOTAL_ASSETS,
    "OperatingRevenues": CK.REVENUE,
    "OperatingExpenses": CK.SGA_EXPENSES,
    # CI
    "TotalComprehensiveIncome": CK.COMPREHENSIVE_INCOME,
    "ComprehensiveIncomeAttributableToOwnersOfParent": CK.COMPREHENSIVE_INCOME_PARENT,
    "ComprehensiveIncomeAttributableToNonControllingInterests": CK.COMPREHENSIVE_INCOME_MINORITY,
    # Depreciation / R&D
    "DepreciationAndAmortisation": CK.DEPRECIATION_CF,
    "DepreciationAndAmortisationExpense": CK.DEPRECIATION_CF,
    "ImpairmentLossRecognisedInProfitOrLoss": CK.IMPAIRMENT_LOSS_PL,
    "ResearchAndDevelopmentExpense": CK.RD_EXPENSES,
    # PL — IFRS サフィックス付き明示登録（サフィックス除去で基底名がない概念用）
    "RevenueIFRS": CK.REVENUE,
    "OperatingProfitIFRS": CK.OPERATING_INCOME,
    "ProfitLossAttributableToOwnersOfParentIFRS": CK.NET_INCOME_PARENT,
    "ProfitLossAttributableToNonControllingInterestsIFRS": CK.NET_INCOME_MINORITY,
    "ProfitIFRS": CK.NET_INCOME,
    "ProfitLossIFRS": CK.NET_INCOME,
    "TotalComprehensiveIncomeIFRS": CK.COMPREHENSIVE_INCOME,
}

_IFRS_BS: dict[str, str] = {
    "NonCurrentAssets": CK.NONCURRENT_ASSETS,
    "TradeAndOtherReceivables": CK.TRADE_RECEIVABLES,
    "TradeAndOtherCurrentReceivables": CK.TRADE_RECEIVABLES,
    "InvestmentProperty": CK.INVESTMENT_PROPERTY,
    "RightOfUseAssets": CK.RIGHT_OF_USE_ASSETS,
    "InvestmentsAccountedForUsingEquityMethod": CK.EQUITY_METHOD_INVESTMENTS,
    "IntangibleAssetsOtherThanGoodwill": CK.INTANGIBLE_ASSETS,
    "TradeAndOtherPayables": CK.TRADE_PAYABLES,
    "TradeAndOtherCurrentPayables": CK.TRADE_PAYABLES,
    "Equity": CK.NET_ASSETS,
    "TotalEquity": CK.NET_ASSETS,
    "EquityAttributableToOwnersOfParent": CK.EQUITY_PARENT,
    "IssuedCapital": CK.CAPITAL_STOCK,
    "SharePremium": CK.CAPITAL_SURPLUS,
    "TreasuryShares": CK.TREASURY_STOCK,
    "OtherComponentsOfEquity": CK.OCI_ACCUMULATED,
}

_IFRS_CF: dict[str, str] = {
    "CashFlowsFromUsedInOperatingActivities": CK.OPERATING_CF,
    "CashFlowsFromUsedInInvestingActivities": CK.INVESTING_CF,
    "CashFlowsFromUsedInFinancingActivities": CK.FINANCING_CF,
    "IncreaseDecreaseInCashAndCashEquivalents": CK.NET_CHANGE_IN_CASH,
    "CashAndCashEquivalentsAtEndOfPeriod": CK.CASH_END,
}


# ---------------------------------------------------------------------------
# US-GAAP PL/BS/CF
# ---------------------------------------------------------------------------

_USGAAP_PL: dict[str, str] = {
    "Revenues": CK.REVENUE,
    "NetRevenues": CK.REVENUE,
    "SalesRevenueNet": CK.REVENUE,
    "SalesRevenueGoodsNet": CK.REVENUE,
    "SalesRevenueServicesNet": CK.REVENUE,
    "CostOfGoodsSold": CK.COST_OF_SALES,
    "CostOfGoodsAndServicesSold": CK.COST_OF_SALES,
    "CostOfRevenue": CK.COST_OF_SALES,
    "InterestIncome": CK.INTEREST_INCOME_PL,
    "InterestExpense": CK.INTEREST_EXPENSE_PL,
    "InterestIncomeExpenseNet": CK.INTEREST_INCOME_PL,
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxes": CK.INCOME_BEFORE_TAX,
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": CK.INCOME_BEFORE_TAX,
    "IncomeTaxExpenseBenefit": CK.INCOME_TAXES,
    "NetIncomeLoss": CK.NET_INCOME,
    "NetIncomeLossAttributableToParent": CK.NET_INCOME_PARENT,
    "NetIncomeLossAvailableToCommonStockholdersBasic": CK.NET_INCOME_PARENT,
    "NetIncomeLossAttributableToNoncontrollingInterest": CK.NET_INCOME_MINORITY,
    "OtherComprehensiveIncomeLossNetOfTax": CK.OCI_ACCUMULATED,
    "ComprehensiveIncomeNetOfTax": CK.COMPREHENSIVE_INCOME,
    "ComprehensiveIncomeNetOfTaxAttributableToParent": CK.COMPREHENSIVE_INCOME_PARENT,
    "ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest": CK.COMPREHENSIVE_INCOME_MINORITY,
    "OperatingIncomeLoss": CK.OPERATING_INCOME,
    "ResearchAndDevelopmentExpense": CK.RD_EXPENSES,
    "DepreciationDepletionAndAmortization": CK.DEPRECIATION_CF,
    "DepreciationAndAmortization": CK.DEPRECIATION_CF,
    "EarningsPerShareBasic": CK.EPS,
    "EarningsPerShareDiluted": CK.EPS_DILUTED,
}

_USGAAP_BS: dict[str, str] = {
    "CashAndCashEquivalentsAtCarryingValue": CK.CASH_AND_EQUIVALENTS,
    "AccountsReceivableNetCurrent": CK.TRADE_RECEIVABLES,
    "AccountsReceivableNet": CK.TRADE_RECEIVABLES,
    "InventoryNet": CK.INVENTORIES,
    "PropertyPlantAndEquipmentNet": CK.PPE,
    "IntangibleAssetsNetExcludingGoodwill": CK.INTANGIBLE_ASSETS,
    "AssetsCurrent": CK.CURRENT_ASSETS,
    "AssetsNoncurrent": CK.NONCURRENT_ASSETS,
    "LiabilitiesCurrent": CK.CURRENT_LIABILITIES,
    "LiabilitiesNoncurrent": CK.NONCURRENT_LIABILITIES,
    "StockholdersEquity": CK.SHAREHOLDERS_EQUITY,
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": CK.NET_ASSETS,
    "MinorityInterest": CK.MINORITY_INTERESTS,
    "CommonStockValue": CK.CAPITAL_STOCK,
    "AdditionalPaidInCapital": CK.CAPITAL_SURPLUS,
    "AccumulatedOtherComprehensiveIncomeLossNetOfTax": CK.OCI_ACCUMULATED,
    "TreasuryStockValue": CK.TREASURY_STOCK,
}

_USGAAP_CF: dict[str, str] = {
    "NetCashProvidedByUsedInOperatingActivities": CK.OPERATING_CF,
    "NetCashProvidedByUsedInInvestingActivities": CK.INVESTING_CF,
    "NetCashProvidedByUsedInFinancingActivities": CK.FINANCING_CF,
    "EffectOfExchangeRateOnCashAndCashEquivalents": CK.FX_EFFECT_ON_CASH,
    "CashAndCashEquivalentsPeriodIncreaseDecrease": CK.NET_CHANGE_IN_CASH,
    "PaymentsToAcquirePropertyPlantAndEquipment": CK.PURCHASE_PPE_CF,
    "ProceedsFromSaleOfPropertyPlantAndEquipment": CK.PROCEEDS_PPE_SALE_CF,
    "PaymentsOfDividends": CK.DIVIDENDS_PAID_CF,
}


# ---------------------------------------------------------------------------
# 銀行（jppfs_bk / jpcrp_bk タクソノミ）
# ---------------------------------------------------------------------------

_BANKING: dict[str, str] = {
    # BS
    "LoansAndBillsDiscounted": CK.LOANS_AND_BILLS_DISCOUNTED,
    "LoansAndBillsDiscountedBK": CK.LOANS_AND_BILLS_DISCOUNTED,
    "Securities": CK.SECURITIES_BANKING,
    "SecuritiesBK": CK.SECURITIES_BANKING,
    "SecuritiesFinBu": CK.SECURITIES_BANKING,
    "Deposits": CK.DEPOSITS,
    "DepositsBK": CK.DEPOSITS,
    # PL
    "OrdinaryRevenues": CK.ORDINARY_REVENUE_BANKING,
    "OrdinaryRevenuesBK": CK.ORDINARY_REVENUE_BANKING,
    "OrdinaryExpenses": CK.SGA_EXPENSES,
    # Ratios
    "ConsolidatedCapitalAdequacyRatioBIS": CK.CAPITAL_ADEQUACY_RATIO_BIS,
    "CapitalAdequacyRatioBIS": CK.CAPITAL_ADEQUACY_RATIO_BIS,
    "ConsolidatedCapitalAdequacyRatioBISBK": CK.CAPITAL_ADEQUACY_RATIO_BIS,
    "ConsolidatedCapitalAdequacyRatioBIS1stBK": CK.CAPITAL_ADEQUACY_RATIO_INTERNATIONAL,
    "NonConsolidatedCapitalAdequacyRatioBISBK": CK.CAPITAL_ADEQUACY_RATIO_BIS,
    "ConsolidatedCapitalAdequacyRatioDomesticBK": CK.CAPITAL_ADEQUACY_RATIO_DOMESTIC,
    "NonConsolidatedCapitalAdequacyRatioDomesticBK": CK.CAPITAL_ADEQUACY_RATIO_DOMESTIC,
}

# ---------------------------------------------------------------------------
# 保険（jppfs_in / jpcrp_in タクソノミ）
# ---------------------------------------------------------------------------

_INSURANCE: dict[str, str] = {
    # PL
    "OrdinaryRevenuesIN": CK.ORDINARY_REVENUE_INSURANCE,
    "NetPremiumsWritten": CK.NET_PREMIUMS_WRITTEN,
    "NetPremiumsWrittenIN": CK.NET_PREMIUMS_WRITTEN,
    "InterestAndDividendIncome": CK.INTEREST_DIVIDEND_INCOME_INS,
    "InterestAndDividendIncomeIN": CK.INTEREST_DIVIDEND_INCOME_INS,
    "InvestmentIncomeIN": CK.INVESTMENT_YIELD_INCOME,
    "InvestmentYieldIncomeIN": CK.INVESTMENT_YIELD_INCOME,
    "InvestmentYieldRealizedGainsAndLossesIN": CK.INVESTMENT_YIELD_REALIZED,
    # Ratios
    "LossRatioIN": CK.NET_LOSS_RATIO,
    "NetLossRatio": CK.NET_LOSS_RATIO,
    "ExpenseRatioIN": CK.NET_OPERATING_EXPENSE_RATIO,
    "NetOperatingExpenseRatio": CK.NET_OPERATING_EXPENSE_RATIO,
}

# ---------------------------------------------------------------------------
# REIT（jppfs_cor / 投資法人タクソノミ）
# ---------------------------------------------------------------------------

_REIT: dict[str, str] = {
    # PL/BS — REIT サフィックス付き（サフィックス除去でも基底名がマッチ）
    "OperatingRevenuesREIT": CK.REVENUE,
    "OperatingExpensesREIT": CK.SGA_EXPENSES,
    "OperatingIncomeREIT": CK.OPERATING_INCOME,
    "OrdinaryIncomeREIT": CK.ORDINARY_INCOME,
    "NetIncomeREIT": CK.NET_INCOME,
    "TotalAssetsREIT": CK.TOTAL_ASSETS,
    "NetAssetsREIT": CK.NET_ASSETS,
    # Per-unit（REIT 固有概念名 — サフィックス除去では拾えない）
    "DistributionPerUnit": CK.DPS,
    "DistributionsPerUnitExcludingDistributionsInExcessOfProfitREIT": CK.DPS,
    "DistributionsInExcessOfProfitPerUnitREIT": CK.EXTRA_DIVIDEND,
    "TotalDistributionsPerUnitREIT": CK.TOTAL_DIVIDEND_PAID,
    "NetIncomePerUnitREIT": CK.EPS,
    "NetAssetsPerUnitREIT": CK.BPS,
    # 一般
    "RentalRevenue": CK.REVENUE,
    "OperatingRevenue": CK.REVENUE,
    "OperatingRevenue1": CK.REVENUE,
}


# ---------------------------------------------------------------------------
# 統合インデックス
# ---------------------------------------------------------------------------

_CONCEPT_INDEX: dict[str, str] = {
    **_JGAAP_PL, **_JGAAP_BS, **_JGAAP_CF, **_JPCRP,
    **_IFRS_PL, **_IFRS_BS, **_IFRS_CF,
    **_USGAAP_PL, **_USGAAP_BS, **_USGAAP_CF,
    **_BANKING, **_INSURANCE,
    **_REIT,
}


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def lookup_statement_exact(concept: str) -> str | None:
    """辞書完全一致のみで CK を返す。"""
    return _CONCEPT_INDEX.get(concept)


def lookup_statement_normalized(concept: str) -> str | None:
    """正規化フォールバック: IFRS / REIT サフィックスを除去して再検索。

    TDnet の IFRS 添付財務諸表では概念名に ``IFRS`` サフィックスが付く
    (例: ``FinanceIncomeIFRS``, ``CostOfSalesIFRS``)。
    サフィックスを除去して基底辞書を再検索する。
    """
    for suffix in ("IFRS", "REIT"):
        if concept.endswith(suffix) and len(concept) > len(suffix):
            base = concept[:-len(suffix)]
            result = _CONCEPT_INDEX.get(base)
            if result is not None:
                return result
    return None


def lookup_statement(concept: str) -> str | None:
    """PL/BS/CF の concept から CK を返す。完全一致 → サフィックス除去の順。"""
    result = lookup_statement_exact(concept)
    if result is not None:
        return result
    return lookup_statement_normalized(concept)
