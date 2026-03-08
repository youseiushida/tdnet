"""パイプラインマッパー — concept → canonical key の名寄せロジック。

``extract_values()`` が使用するマッパーの型定義・デフォルト実装・ヘルパーを提供する。

設計原則:
    - マッパーは ``Callable[[LineItem, MapperContext], str | None]`` シグネチャ
    - ``str`` を返すとマッチ（canonical key）、``None`` で次のマッパーへ
    - パイプライン（リスト）の先頭マッパーほど高優先

デフォルトパイプライン::

    [dividend_mapper, forecast_mapper, summary_mapper, statement_mapper,
     definition_mapper(), calc_mapper()]

    1. dividend_mapper: DPS 科目（AnnualDividendPaymentScheduleAxis 対応）
    2. forecast_mapper: 業績予想（ResultForecastAxis=ForecastMember 対応）
    3. summary_mapper: tse-ed-t サマリー科目（経営成績の概況）
    4. statement_mapper: jppfs_cor / IFRS / US-GAAP PL/BS/CF の辞書引き
    5. definition_mapper(): Definition Linkbase の general-special で
       独自科目 → 標準科目に遡上
    6. calc_mapper(): Calculation Linkbase の summation-item で
       独自科目 → 親標準科目に遡上

典型的な使用例::

    from tdnet.mapper import summary_mapper, statement_mapper, dict_mapper

    # デフォルト: 上記 6 マッパーのパイプライン
    # カスタム辞書を最優先に追加
    my_mapper = dict_mapper({"MyRevenue": "revenue"}, name="my_rules")
    pipeline = [my_mapper, summary_mapper, statement_mapper]

    # カスタム lookup を使う例（独自辞書でリンクベース解決）
    my_map = {"NetSales": "売上高", "OperatingIncome": "営業利益"}
    pipeline = [
        dict_mapper(my_map),
        definition_mapper(lookup=my_map.get),
        calc_mapper(lookup=my_map.get),
    ]
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tdnet.models.ck import CK
from tdnet.models.statement_mappings import (
    lookup_statement_exact,
    lookup_statement_normalized,
)
from tdnet.models.summary_mappings import lookup_summary

if TYPE_CHECKING:
    from xbrl_core import CalculationLinkbase, DefinitionTree

    from tdnet.models.types import LineItem

__all__ = [
    "ConceptMapper",
    "MapperContext",
    "build_parent_index",
    "calc_mapper",
    "definition_mapper",
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

    ``extract_values()`` が ``Statements`` から自動構築する。
    ユニットテスト時は直接構築可能。

    Attributes:
        entity_id: 証券コード等のエンティティ識別子。
        has_consolidated: 連結財務諸表の有無。
        definition_parent_index: Definition Linkbase の general-special arcrole
            による逆引きインデックス。``{独自科目local_name: 標準祖先local_name}``。
            ``definition_mapper`` が使用する。空辞書の場合は
            ``definition_mapper`` は常に ``None`` を返す。
        calculation_linkbase: 提出者の Calculation Linkbase。
            ``calc_mapper`` が ``ancestors_of()`` で祖先を辿る。
            ``None`` の場合は ``calc_mapper`` は常に ``None`` を返す。
    """

    entity_id: str = ""
    has_consolidated: bool | None = None
    definition_parent_index: dict[str, str] = field(default_factory=dict)
    calculation_linkbase: CalculationLinkbase | None = None


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
    return [
        dividend_mapper,
        forecast_mapper,
        summary_mapper,
        statement_mapper,
        definition_mapper(),
        calc_mapper(),
    ]


# ---------------------------------------------------------------------------
# リンクベースマッパー共通
# ---------------------------------------------------------------------------

_ARCROLE_GENERAL_SPECIAL = "http://www.xbrl.org/2003/arcrole/general-special"

_FILER_XSD_RE = re.compile(r"jpcrp\d+|tse[a-z]*\d+")
"""提出者別タクソノミの XSD ファイル名パターン。

EDINET 提出者 XSD: ``jpcrp030000-asr-001_E02144-000.xsd``
TDnet 提出者 XSD: 同様のパターン。
標準タクソノミ: ``jppfs_cor_2025-11-01.xsd``, ``jpcrp_cor_...``（不一致）。
"""


def _default_statement_lookup(concept_name: str) -> str | None:
    """組み込み statement_mappings での2段 lookup。"""
    ck = lookup_statement_exact(concept_name)
    if ck is not None:
        return ck
    return lookup_statement_normalized(concept_name)


def _is_standard_href(href: str) -> bool:
    """href が標準タクソノミの XSD を参照しているか判定する。

    Args:
        href: ``DefinitionArc.from_href`` または ``to_href``。
            形式: ``"../jppfs_cor_2025-11-01.xsd#NetSales"`` 等。

    Returns:
        標準タクソノミの XSD を参照している場合 True。
    """
    path_part = href.split("#")[0] if "#" in href else href
    filename = path_part.rsplit("/", 1)[-1] if "/" in path_part else path_part
    return not bool(_FILER_XSD_RE.match(filename))


def _find_standard_ancestor(
    concept: str,
    child_to_parents: dict[str, list[tuple[str, str]]],
    *,
    _visited: set[str] | None = None,
) -> str | None:
    """general-special 関係を辿り、標準タクソノミの最も近い祖先を返す。

    Args:
        concept: 起点の concept ローカル名。
        child_to_parents: 全体の逆引きマップ。
            各エントリは ``(parent_concept, parent_href)`` のタプルリスト。
        _visited: 循環検出用の内部引数。

    Returns:
        標準タクソノミに属する最も近い祖先のローカル名。
        見つからない場合は None。
    """
    if _visited is None:
        _visited = set()
    _visited.add(concept)

    parents = child_to_parents.get(concept, [])
    for parent_concept, parent_href in parents:
        if parent_concept in _visited:
            continue

        if _is_standard_href(parent_href):
            return parent_concept

        result = _find_standard_ancestor(
            parent_concept,
            child_to_parents,
            _visited=_visited,
        )
        if result is not None:
            return result

    return None


def build_parent_index(
    definition_linkbase: dict[str, DefinitionTree] | None,
) -> dict[str, str]:
    """Definition Linkbase の general-special arcrole から逆引きインデックスを構築する。

    general-special arc は from_concept（general/親）→ to_concept（special/子）の
    方向で定義される。これを逆引きし、to_concept → 最も近い標準タクソノミ親概念の
    マッピングを返す。

    Args:
        definition_linkbase: ``parse_definition_linkbase()`` の戻り値。
            None の場合は空辞書を返す。

    Returns:
        ``{独自科目local_name: 標準祖先local_name}`` の辞書。
    """
    if definition_linkbase is None:
        return {}

    child_to_parents: dict[str, list[tuple[str, str]]] = {}
    for tree in definition_linkbase.values():
        for arc in tree.arcs:
            if arc.arcrole == _ARCROLE_GENERAL_SPECIAL:
                child_to_parents.setdefault(arc.to_concept, []).append(
                    (arc.from_concept, arc.from_href),
                )

    result: dict[str, str] = {}
    for child in child_to_parents:
        ancestor = _find_standard_ancestor(child, child_to_parents)
        if ancestor is not None:
            result[child] = ancestor

    return result


def definition_mapper(
    lookup: Callable[[str], str | None] | None = None,
) -> ConceptMapper:
    """Definition Linkbase の general-special で標準概念に遡上し CK を返すマッパーを生成する。

    提出者独自の科目名を Definition Linkbase の general-special arcrole を
    辿り、最も近い標準タクソノミの祖先概念を見つけて CK に変換する。

    事前に ``build_parent_index()`` で構築した逆引きインデックスを使用するため、
    マッパー呼び出し時のコストは O(1) の辞書参照 + lookup のみ。

    Args:
        lookup: 祖先 concept 名 → canonical key の名寄せ関数。
            ``None`` の場合は組み込み statement_mappings を使用する。

    Returns:
        ``ConceptMapper`` として使える callable。
    """
    _lookup = lookup or _default_statement_lookup

    def _mapper(item: LineItem, ctx: MapperContext) -> str | None:
        if not ctx.definition_parent_index:
            return None
        ancestor = ctx.definition_parent_index.get(item.local_name)
        if ancestor is None:
            return None
        return _lookup(ancestor)

    _mapper.__name__ = "definition_mapper"
    _mapper.__qualname__ = "definition_mapper"
    return _mapper


def calc_mapper(
    lookup: Callable[[str], str | None] | None = None,
) -> ConceptMapper:
    """Calculation Linkbase の summation-item で親標準概念に遡上し CK を返すマッパーを生成する。

    提出者独自の科目名を Calculation Linkbase の親子関係（summation-item
    arcrole）を辿り、祖先に標準概念が見つかれば CK に変換する。

    全 role_uri を走査し、最初に CK が見つかった時点で返す。

    Args:
        lookup: 祖先 concept 名 → canonical key の名寄せ関数。
            ``None`` の場合は組み込み statement_mappings を使用する。

    Returns:
        ``ConceptMapper`` として使える callable。
    """
    _lookup = lookup or _default_statement_lookup

    def _mapper(item: LineItem, ctx: MapperContext) -> str | None:
        if ctx.calculation_linkbase is None:
            return None
        for role_uri in ctx.calculation_linkbase.role_uris:
            ancestors = ctx.calculation_linkbase.ancestors_of(
                item.local_name, role_uri=role_uri,
            )
            for ancestor in ancestors:
                ck = _lookup(ancestor)
                if ck is not None:
                    return ck
        return None

    _mapper.__name__ = "calc_mapper"
    _mapper.__qualname__ = "calc_mapper"
    return _mapper
