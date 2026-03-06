"""パイプラインマッパー — concept → canonical key の名寄せロジック。

``extract_values()`` が使用するマッパーの型定義・デフォルト実装・ヘルパーを提供する。

設計原則:
    - マッパーは ``Callable[[LineItem, MapperContext], str | None]`` シグネチャ
    - ``str`` を返すとマッチ（canonical key）、``None`` で次のマッパーへ
    - パイプライン（リスト）の先頭マッパーほど高優先

デフォルトパイプライン::

    [dividend_mapper, forecast_mapper, summary_mapper, statement_mapper]

    1. dividend_mapper: DPS 科目（AnnualDividendPaymentScheduleAxis 対応）
    2. forecast_mapper: 業績予想（ResultForecastAxis=ForecastMember 対応）
    3. summary_mapper: tse-ed-t サマリー科目（経営成績の概況）
    4. statement_mapper: jppfs_cor / IFRS / US-GAAP PL/BS/CF の辞書引き
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tdnet.models.ck import CK
from tdnet.models.statement_mappings import (
    lookup_statement_exact,
    lookup_statement_normalized,
)
from tdnet.models.summary_mappings import lookup_summary

if TYPE_CHECKING:
    from tdnet.models.types import LineItem

__all__ = [
    "ConceptMapper",
    "MapperContext",
    "dict_mapper",
    "dividend_mapper",
    "forecast_mapper",
    "statement_mapper",
    "summary_mapper",
]

ConceptMapper = Callable[["LineItem", "MapperContext"], str | None]
"""concept → canonical key マッパーの型。

Args:
    item: 走査中の LineItem。
    ctx: マッパーコンテキスト。

Returns:
    マッチした canonical key（``str``）。マッチしない場合は ``None``。
"""


@dataclass(frozen=True, slots=True)
class MapperContext:
    """マッパーに渡されるコンテキスト情報。

    Attributes:
        entity_id: 証券コード等のエンティティ識別子。
        has_consolidated: 連結財務諸表の有無。
    """

    entity_id: str = ""
    has_consolidated: bool | None = None


# ---------------------------------------------------------------------------
# ディメンション検出ヘルパー
# ---------------------------------------------------------------------------

def _has_forecast_member(item: LineItem) -> bool:
    """ResultForecastAxis = ForecastMember を持つか判定。"""
    for dim in item.dimensions:
        axis_local = dim.axis.split("}")[-1] if "}" in dim.axis else dim.axis
        member_local = dim.member.split("}")[-1] if "}" in dim.member else dim.member
        if "ResultForecast" in axis_local and member_local == "ForecastMember":
            return True
    return False


def _get_dividend_schedule_member(item: LineItem) -> str | None:
    """AnnualDividendPaymentScheduleAxis のメンバーを返す。"""
    for dim in item.dimensions:
        axis_local = dim.axis.split("}")[-1] if "}" in dim.axis else dim.axis
        if "AnnualDividendPaymentSchedule" in axis_local:
            member_local = dim.member.split("}")[-1] if "}" in dim.member else dim.member
            return member_local
    return None


# ---------------------------------------------------------------------------
# Forecast: 実績 CK → 予想 CK マッピング
# ---------------------------------------------------------------------------

_RESULT_TO_FORECAST: dict[str, str] = {
    CK.REVENUE: CK.FORECAST_REVENUE,
    CK.OPERATING_INCOME: CK.FORECAST_OPERATING_INCOME,
    CK.ORDINARY_INCOME: CK.FORECAST_ORDINARY_INCOME,
    CK.NET_INCOME_PARENT: CK.FORECAST_NET_INCOME_PARENT,
    CK.NET_INCOME: CK.FORECAST_NET_INCOME_PARENT,
    CK.EPS: CK.FORECAST_EPS,
    CK.DPS: CK.FORECAST_DPS,
    CK.INCOME_BEFORE_TAX: CK.FORECAST_ORDINARY_INCOME,
    # 業種別
    CK.ORDINARY_REVENUE_BANKING: CK.FORECAST_REVENUE,
    CK.ORDINARY_REVENUE_INSURANCE: CK.FORECAST_REVENUE,
    CK.NET_OPERATING_REVENUE_SE: CK.FORECAST_REVENUE,
    CK.OPERATING_REVENUE_SE: CK.FORECAST_REVENUE,
}

# DPS 関連の概念名
_DPS_CONCEPTS = frozenset({
    "DividendPerShare",
})


# ---------------------------------------------------------------------------
# マッパー関数
# ---------------------------------------------------------------------------


def dividend_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """配当科目を AnnualDividendPaymentScheduleAxis 対応で名寄せするマッパー。

    - AnnualMember → CK.DPS（年間配当）
    - FirstQuarter/SecondQuarter/ThirdQuarter/YearEndMember → CK.INTERIM_DPS
    - Schedule axis なしの DividendPerShare → CK.DPS（フォールバック）
    """
    if item.local_name not in _DPS_CONCEPTS:
        return None

    member = _get_dividend_schedule_member(item)
    if member is None:
        return CK.DPS
    if member == "AnnualMember":
        return CK.DPS
    if member in ("FirstQuarterMember", "SecondQuarterMember",
                   "ThirdQuarterMember", "YearEndMember"):
        return CK.INTERIM_DPS
    return CK.DPS


def forecast_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """業績予想（ForecastMember ディメンション付き）を FORECAST_* CK に名寄せ。

    ResultForecastAxis = ForecastMember を持つアイテムのみ処理。
    基礎概念の CK を取得し、FORECAST_* CK に変換する。
    """
    if not _has_forecast_member(item):
        return None

    base_ck = lookup_summary(item.local_name)
    if base_ck is None:
        return None

    return _RESULT_TO_FORECAST.get(base_ck)


def summary_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """tse-ed-t サマリー科目（経営成績の概況）から名寄せするマッパー。

    ForecastMember ディメンション付きアイテムはスキップ（forecast_mapper に委譲）。
    DividendPerShare は dividend_mapper に委譲。
    """
    if _has_forecast_member(item):
        return None
    if item.local_name in _DPS_CONCEPTS:
        return None
    return lookup_summary(item.local_name)


def statement_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """財務諸表本体（PL/BS/CF）から名寄せするマッパー。

    jppfs_cor / IFRS / US-GAAP タクソノミの科目を対象とする。
    summary_mapper で取得できなかった項目を補完する。
    """
    ck = lookup_statement_exact(item.local_name)
    if ck is not None:
        return ck
    return lookup_statement_normalized(item.local_name)


def dict_mapper(
    mapping: dict[str, str],
    *,
    name: str | None = None,
) -> ConceptMapper:
    """辞書ベースのマッパーを生成する。

    Args:
        mapping: ``{concept_local_name: canonical_key}`` の辞書。
        name: マッパー名。未指定の場合は自動生成。

    Returns:
        ``ConceptMapper`` として使える callable。
    """

    def _mapper(item: LineItem, ctx: MapperContext) -> str | None:
        return mapping.get(item.local_name)

    _mapper.__name__ = name or f"dict_mapper({len(mapping)} entries)"
    _mapper.__qualname__ = _mapper.__name__
    return _mapper


def get_default_pipeline() -> list[ConceptMapper]:
    """デフォルトのマッパーパイプラインを返す。"""
    return [dividend_mapper, forecast_mapper, summary_mapper, statement_mapper]
