"""テスト用共通ヘルパー。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from xbrl_core import DimensionMember
from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.models.types import LabelInfo, LabelSource, LineItem

_TSE_ED_NS = "http://www.xbrl.tdnet.info/taxonomy/jp/tse/tdnet/ed/t/2014-01-12"
_LABEL_ROLE = "http://www.xbrl.org/2003/role/label"


def make_label(text: str, lang: str = "ja") -> LabelInfo:
    """テスト用ラベルを生成する。"""
    return LabelInfo(text=text, role=_LABEL_ROLE, lang=lang, source=LabelSource.STANDARD)


def make_item(
    local_name: str,
    value: Decimal | str | None = None,
    *,
    namespace_uri: str = _TSE_ED_NS,
    context_id: str = "CurrentYearDuration_ConsolidatedMember",
    period: DurationPeriod | InstantPeriod | None = None,
    dimensions: tuple[DimensionMember, ...] = (),
    unit_ref: str | None = "JPY",
    label_ja: str = "",
    label_en: str = "",
    entity_id: str = "7203",
    is_nil: bool = False,
    decimals: int | None = -6,
    order: int = 0,
) -> LineItem:
    """テスト用 LineItem を生成するヘルパー。"""
    if period is None:
        period = DurationPeriod(
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
        )
    return LineItem(
        concept=f"{{{namespace_uri}}}{local_name}",
        namespace_uri=namespace_uri,
        local_name=local_name,
        label_ja=make_label(label_ja or local_name, "ja"),
        label_en=make_label(label_en or local_name, "en"),
        value=value,
        unit_ref=unit_ref,
        decimals=decimals,
        context_id=context_id,
        period=period,
        entity_id=entity_id,
        dimensions=dimensions,
        is_nil=is_nil,
        source_line=None,
        order=order,
    )


def make_consolidated_dim(consolidated: bool = True) -> DimensionMember:
    """連結/個別のディメンションを生成する。"""
    member_name = "ConsolidatedMember" if consolidated else "NonConsolidatedMember"
    return DimensionMember(
        axis=f"{{{_TSE_ED_NS}}}ConsolidatedOrNonConsolidatedAxis",
        member=f"{{{_TSE_ED_NS}}}{member_name}",
    )


def make_current_dim() -> DimensionMember:
    """当期ディメンションを生成する。"""
    return DimensionMember(
        axis=f"{{{_TSE_ED_NS}}}CurrentOrPreviousAxis",
        member=f"{{{_TSE_ED_NS}}}CurrentMember",
    )


def make_prior_dim() -> DimensionMember:
    """前期ディメンションを生成する。"""
    return DimensionMember(
        axis=f"{{{_TSE_ED_NS}}}CurrentOrPreviousAxis",
        member=f"{{{_TSE_ED_NS}}}PreviousMember",
    )


def make_forecast_dim() -> DimensionMember:
    """業績予想ディメンションを生成する。"""
    return DimensionMember(
        axis=f"{{{_TSE_ED_NS}}}ResultForecastAxis",
        member=f"{{{_TSE_ED_NS}}}ForecastMember",
    )


def make_dividend_schedule_dim(member: str = "AnnualMember") -> DimensionMember:
    """配当スケジュールディメンションを生成する。"""
    return DimensionMember(
        axis=f"{{{_TSE_ED_NS}}}AnnualDividendPaymentScheduleAxis",
        member=f"{{{_TSE_ED_NS}}}{member}",
    )


# 共通の期間定数
CURRENT_DURATION = DurationPeriod(start_date=date(2024, 4, 1), end_date=date(2025, 3, 31))
PRIOR_DURATION = DurationPeriod(start_date=date(2023, 4, 1), end_date=date(2024, 3, 31))
CURRENT_INSTANT = InstantPeriod(instant=date(2025, 3, 31))
PRIOR_INSTANT = InstantPeriod(instant=date(2024, 3, 31))
