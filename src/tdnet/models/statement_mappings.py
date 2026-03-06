"""PL/BS/CF 本体の concept → CK マッピング。

決算短信 Attachment 部分で使用される jppfs_cor タクソノミの
concept を CK にマッピングする。

jppfs_cor は EDINET と共通タクソノミのため、
edinet の statement_mappings.py から主要概念を移植。
サンプル 4 社の全 177 概念を確認の上、マッピング可能な概念を網羅。
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
    # NOI/NOE/EI/EL detail — total と衝突するため除外。
    # 個別の明細科目は LineItem.local_name で直接取得可能。
    "EquityInEarningsOfAffiliatesNOI": CK.EQUITY_METHOD_INCOME,
    "ImpairmentLossEL": CK.IMPAIRMENT_LOSS_PL,
    # SGA detail — 独自 CK を持つもののみマッピング。
    "DepreciationSGA": CK.DEPRECIATION_SGA,
    "ResearchAndDevelopmentExpensesSGA": CK.RD_EXPENSES,
    # OCI detail — total の OtherComprehensiveIncome と衝突するため除外。
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
    # 棚卸資産 detail (Merchandise, WorkInProcess 等) — total と衝突するため除外。
    "PrepaidExpenses": CK.PREPAID_EXPENSES,
    "ContractAssets": CK.CONTRACT_ASSETS,
    "ContractAssetsNet": CK.CONTRACT_ASSETS,
    "CurrentAssets": CK.CURRENT_ASSETS,
    # NCA - PPE
    "PropertyPlantAndEquipment": CK.PPE,
    "Land": CK.LAND,
    "BuildingsNet": CK.BUILDINGS_NET,
    "ConstructionInProgress": CK.CONSTRUCTION_IN_PROGRESS,
    # PPE detail (Buildings, MachineryAndEquipmentNet 等) — total と衝突するため除外。
    # NCA - IA
    "IntangibleAssets": CK.INTANGIBLE_ASSETS,
    "Goodwill": CK.GOODWILL,
    # IA detail (Software, SoftwareInProgress) — total と衝突するため除外。
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
    # CL detail (IncomeTaxesPayable 等) — total と衝突するため除外。
    # NCL
    "LongTermLoansPayable": CK.LONG_TERM_LOANS,
    "BondsPayable": CK.BONDS_PAYABLE,
    "ProvisionForRetirementBenefits": CK.RETIREMENT_BENEFIT_LIABILITY,
    "NoncurrentLiabilities": CK.NONCURRENT_LIABILITIES,
    # NCL detail (AssetRetirementObligationsNCL 等) — total と衝突するため除外。
    "Liabilities": CK.TOTAL_LIABILITIES,
    # NA
    "CapitalStock": CK.CAPITAL_STOCK,
    "CapitalSurplus": CK.CAPITAL_SURPLUS,
    "RetainedEarnings": CK.RETAINED_EARNINGS,
    "TreasuryStock": CK.TREASURY_STOCK,
    "ShareholdersEquity": CK.SHAREHOLDERS_EQUITY,
    "ValuationAndTranslationAdjustments": CK.OCI_ACCUMULATED,
    # OCI BS detail (ValuationDifference..., ForeignCurrency...) — total と衝突するため除外。
    "SubscriptionRightsToShares": CK.SUBSCRIPTION_RIGHTS,
    "NonControllingInterests": CK.MINORITY_INTERESTS,
    "NetAssets": CK.NET_ASSETS,
    "LiabilitiesAndNetAssets": CK.LIABILITIES_AND_NET_ASSETS,
    "DeferredTaxAssets": CK.DEFERRED_TAX_ASSETS,
    "DeferredTaxLiabilities": CK.DEFERRED_TAX_LIABILITIES,
    # SS — detail 項目は BS total と衝突するためマッピングしない。
    # DividendsFromSurplus 等は LineItem.local_name で直接取得可能。
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
# 統合インデックス
# ---------------------------------------------------------------------------

_CONCEPT_INDEX: dict[str, str] = {
    **_JGAAP_PL, **_JGAAP_BS, **_JGAAP_CF, **_JPCRP,
}


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def lookup_statement_exact(concept: str) -> str | None:
    """辞書完全一致のみで CK を返す。"""
    return _CONCEPT_INDEX.get(concept)


def lookup_statement_normalized(concept: str) -> str | None:
    """正規化フォールバック。現状 TDnet Attachment には不要。"""
    return None


def lookup_statement(concept: str) -> str | None:
    """PL/BS/CF の concept から CK を返す。"""
    return lookup_statement_exact(concept)
