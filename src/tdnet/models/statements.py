"""財務諸表コンテナ。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from xbrl_core.periods import InstantPeriod, DurationPeriod, Period

from tdnet.models.statement_type import StatementType
from tdnet.models.financial_statement import FinancialStatement
from tdnet.models.types import LineItem

if TYPE_CHECKING:
    import pandas as pd
    from xbrl_core import CalculationLinkbase, DefinitionLinkbase, PresentationTree

# TDnet タクソノミの名前空間
_TSE_ED_NS = "http://www.xbrl.tdnet.info/taxonomy/jp/tse/tdnet/ed/t/2014-01-12"

_CURRENT_MEMBER = f"{{{_TSE_ED_NS}}}CurrentMember"
_PREVIOUS_MEMBER = f"{{{_TSE_ED_NS}}}PreviousMember"


def _is_consolidated(item: LineItem) -> bool | None:
    """LineItem が連結かどうか判定する。None = 判定不能。"""
    for dim in item.dimensions:
        axis_local = dim.axis.split("}")[-1] if "}" in dim.axis else dim.axis
        member_local = dim.member.split("}")[-1] if "}" in dim.member else dim.member
        if "ConsolidatedNonconsolidated" in axis_local or "ConsolidatedOrNonConsolidated" in axis_local:
            if "NonConsolidated" in member_local:
                return False
            if "Consolidated" in member_local:
                return True
    return None


def _period_key(item: LineItem) -> str | None:
    """LineItem が当期/前期かを判定する。

    1. ディメンション (CurrentMember/PreviousMember) で判定（四半期短信）。
    2. context_id のプレフィックス (Current*/Prior*) で判定（本決算）。
    """
    # 1. Dimension-based
    for dim in item.dimensions:
        if dim.member == _CURRENT_MEMBER or "CurrentMember" in dim.member:
            return "current"
        if dim.member == _PREVIOUS_MEMBER or "PreviousMember" in dim.member:
            return "prior"
    # 2. Context ID-based fallback
    ctx = item.context_id
    if ctx.startswith("Current"):
        return "current"
    if ctx.startswith("Prior"):
        return "prior"
    return None


def _match_period(
    item: LineItem,
    period: DurationPeriod | InstantPeriod | Literal["current", "prior"] | None,
) -> bool:
    if period is None:
        return True
    if isinstance(period, str):
        pk = _period_key(item)
        if pk is None:
            return True  # Dimension なしの場合はマッチとする
        return pk == period
    return item.period == period


class Statements:
    """財務諸表コンテナ。"""

    def __init__(
        self,
        items: tuple[LineItem, ...],
        *,
        entity_id: str = "",
        warnings: tuple[str, ...] = (),
        definition_linkbase: DefinitionLinkbase | None = None,
        calculation_linkbase: CalculationLinkbase | None = None,
        presentation_linkbase: dict[str, PresentationTree] | None = None,
        definition_parent_index: dict[str, str] | None = None,
    ) -> None:
        self._items = items
        self._entity_id = entity_id
        self._warnings = warnings
        self._definition_linkbase = definition_linkbase
        self._calculation_linkbase = calculation_linkbase
        self._presentation_linkbase = presentation_linkbase
        self._definition_parent_index = definition_parent_index

    def _filter_items(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | InstantPeriod | Literal["current", "prior"] | None = None,
        strict: bool = False,
        namespaces: set[str] | None = None,
    ) -> tuple[LineItem, ...]:
        result: list[LineItem] = []
        for item in self._items:
            cons = _is_consolidated(item)
            if cons is not None and cons != consolidated:
                continue
            if not _match_period(item, period):
                continue
            if namespaces and item.namespace_uri not in namespaces:
                continue
            result.append(item)
        return tuple(result)

    def _detect_period(
        self,
        items: tuple[LineItem, ...],
    ) -> Period | None:
        """items から最も代表的な期間を検出する。"""
        for item in items:
            return item.period
        return None

    def income_statement(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | Literal["current", "prior"] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """損益計算書を組み立てる。"""
        items = self._filter_items(consolidated=consolidated, period=period, strict=strict)
        # PL 科目のフィルタ: DurationPeriod で monetary
        pl_items = tuple(
            item for item in items
            if isinstance(item.period, DurationPeriod)
            and item.unit_ref is not None
            and _is_pl_concept(item)
        )
        return FinancialStatement(
            statement_type=StatementType.INCOME_STATEMENT,
            period=self._detect_period(pl_items),
            items=pl_items if pl_items else items,
            consolidated=consolidated,
            entity_id=self._entity_id,
            warnings_issued=self._warnings,
        )

    def balance_sheet(
        self,
        *,
        consolidated: bool = True,
        period: InstantPeriod | Literal["current", "prior"] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """貸借対照表を組み立てる。"""
        items = self._filter_items(consolidated=consolidated, period=period, strict=strict)
        bs_items = tuple(
            item for item in items
            if isinstance(item.period, InstantPeriod)
            and item.unit_ref is not None
            and _is_bs_concept(item)
        )
        return FinancialStatement(
            statement_type=StatementType.BALANCE_SHEET,
            period=self._detect_period(bs_items),
            items=bs_items if bs_items else items,
            consolidated=consolidated,
            entity_id=self._entity_id,
            warnings_issued=self._warnings,
        )

    def cash_flow_statement(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | Literal["current", "prior"] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """キャッシュフロー計算書を組み立てる。"""
        items = self._filter_items(consolidated=consolidated, period=period, strict=strict)
        cf_items = tuple(
            item for item in items
            if isinstance(item.period, DurationPeriod)
            and _is_cf_concept(item)
        )
        return FinancialStatement(
            statement_type=StatementType.CASH_FLOW_STATEMENT,
            period=self._detect_period(cf_items),
            items=cf_items if cf_items else items,
            consolidated=consolidated,
            entity_id=self._entity_id,
            warnings_issued=self._warnings,
        )

    def equity_statement(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | Literal["current", "prior"] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """株主資本等変動計算書を組み立てる。"""
        items = self._filter_items(consolidated=consolidated, period=period, strict=strict)
        eq_items = tuple(
            item for item in items
            if _is_equity_statement_concept(item)
        )
        return FinancialStatement(
            statement_type=StatementType.STATEMENT_OF_CHANGES_IN_EQUITY,
            period=self._detect_period(eq_items),
            items=eq_items if eq_items else items,
            consolidated=consolidated,
            entity_id=self._entity_id,
            warnings_issued=self._warnings,
        )

    def comprehensive_income(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | Literal["current", "prior"] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """包括利益計算書を組み立てる。"""
        items = self._filter_items(consolidated=consolidated, period=period, strict=strict)
        ci_items = tuple(
            item for item in items
            if _is_ci_concept(item)
        )
        return FinancialStatement(
            statement_type=StatementType.COMPREHENSIVE_INCOME,
            period=self._detect_period(ci_items),
            items=ci_items if ci_items else items,
            consolidated=consolidated,
            entity_id=self._entity_id,
            warnings_issued=self._warnings,
        )

    # --- ユーティリティ ---

    def __getitem__(self, key: str) -> LineItem:
        """全科目から検索。"""
        for item in self._items:
            if item.label_ja.text == key:
                return item
        for item in self._items:
            if item.label_en.text == key:
                return item
        for item in self._items:
            if item.local_name == key:
                return item
        raise KeyError(key)

    def get(self, key: str, default: LineItem | None = None) -> LineItem | None:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return self.get(key) is not None

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[LineItem]:
        return iter(self._items)

    def search(self, keyword: str) -> list[LineItem]:
        """キーワードで部分一致検索。"""
        kw_lower = keyword.lower()
        results: list[LineItem] = []
        for item in self._items:
            if (
                kw_lower in item.label_ja.text.lower()
                or kw_lower in item.label_en.text.lower()
                or kw_lower in item.local_name.lower()
            ):
                results.append(item)
        return results

    def to_dataframe(self) -> pd.DataFrame:
        """全 LineItem を全カラム DataFrame に変換する。

        ``value`` 列は数値（float）のみ。文字列値は ``value_text`` 列に格納される。
        Decimal → float 変換済み（parquet/arrow 互換）。
        """
        import pandas as pd
        from decimal import Decimal

        rows: list[dict[str, object]] = []
        for item in self._items:
            raw = item.value
            if isinstance(raw, Decimal):
                num_val: float | None = float(raw)
                text_val: str | None = None
            elif isinstance(raw, str):
                num_val = None
                text_val = raw
            else:
                num_val = None
                text_val = None
            rows.append({
                "label_ja": item.label_ja.text,
                "label_en": item.label_en.text,
                "value": num_val,
                "value_text": text_val,
                "unit": item.unit_ref,
                "concept": item.concept,
                "context_id": item.context_id,
                "local_name": item.local_name,
                "namespace_uri": item.namespace_uri,
                "decimals": item.decimals,
                "is_nil": item.is_nil,
                "order": item.order,
                "period": str(item.period),
                "dimensions": "; ".join(f"{d.axis}={d.member}" for d in item.dimensions) or "",
            })
        return pd.DataFrame(rows)

    def to_csv(self, path: str | Path, **kwargs: object) -> None:
        self.to_dataframe().to_csv(str(path), index=False, **kwargs)  # type: ignore[arg-type]

    def to_parquet(self, path: str | Path, **kwargs: object) -> None:
        self.to_dataframe().to_parquet(str(path), index=False, **kwargs)  # type: ignore[arg-type]

    def to_excel(self, path: str | Path, **kwargs: object) -> None:
        self.to_dataframe().to_excel(str(path), index=False, **kwargs)  # type: ignore[arg-type]


# ============================================================
# 科目分類ヒューリスティック
# ============================================================

# jppfs の科目名パターンで分類
_PL_KEYWORDS = {
    "NetSales", "Revenue", "CostOfSales", "GrossProfit",
    "SellingGeneralAndAdministrativeExpenses", "OperatingIncome",
    "OperatingRevenue", "NonOperatingIncome", "NonOperatingExpenses",
    "OrdinaryIncome", "ExtraordinaryIncome", "ExtraordinaryLoss",
    "IncomeBeforeIncomeTaxes", "IncomeTaxes", "ProfitLoss",
    "ProfitLossAttributableToOwnersOfParent",
    "ProfitLossAttributableToNonControllingInterests",
    "Profit", "NetIncome", "ProfitAttributableToOwnersOfParent",
}

_BS_KEYWORDS = {
    "Assets", "Liabilities", "NetAssets", "Equity",
    "CurrentAssets", "NoncurrentAssets", "CurrentLiabilities",
    "NoncurrentLiabilities", "CashAndDeposits", "TotalAssets",
    "CapitalStock", "RetainedEarnings", "TreasuryStock",
    "ShareholdersEquity", "Inventories", "TradeReceivables",
    "TradePayables", "Land", "Buildings", "Goodwill",
}

_CF_KEYWORDS = {
    "CashFlow", "OperatingActivities", "InvestingActivities",
    "FinancingActivities", "CashAndCashEquivalents",
    "Depreciation", "Impairment",
}

_CI_KEYWORDS = {
    "ComprehensiveIncome", "OtherComprehensiveIncome",
    "ValuationDifference", "ForeignCurrencyTranslation",
}

_EQUITY_STMT_KEYWORDS = {
    "ChangesInEquity", "StatementOfChanges", "CapitalSurplus",
    "DividendsPaid", "IssuanceOfNewShares",
}


def _concept_matches(item: LineItem, keywords: set[str]) -> bool:
    ln = item.local_name
    for kw in keywords:
        if kw in ln:
            return True
    return False


def _is_pl_concept(item: LineItem) -> bool:
    return _concept_matches(item, _PL_KEYWORDS)


def _is_bs_concept(item: LineItem) -> bool:
    return _concept_matches(item, _BS_KEYWORDS)


def _is_cf_concept(item: LineItem) -> bool:
    return _concept_matches(item, _CF_KEYWORDS)


def _is_ci_concept(item: LineItem) -> bool:
    return _concept_matches(item, _CI_KEYWORDS)


def _is_equity_statement_concept(item: LineItem) -> bool:
    return _concept_matches(item, _EQUITY_STMT_KEYWORDS)
