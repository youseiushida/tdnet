"""dict 行（Parquet 行）→ ドメインオブジェクトへの復元。"""

from __future__ import annotations

import datetime
import json
import math
from collections import defaultdict
from decimal import Decimal
from typing import Any

from xbrl_core import (
    CalculationArc,
    CalculationLinkbase,
    CalculationTree,
    DimensionMember,
)
from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.filing import Filing
from tdnet.models.statements import Statements
from tdnet.models.types import LabelInfo, LabelSource, LineItem


def _safe_int(val: Any) -> int | None:
    """None/NaN を考慮して int に変換する。"""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return int(val)


def _parse_date(val: Any) -> datetime.date | None:
    """date 型またはその文字列表現を datetime.date に変換する。"""
    if val is None:
        return None
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, str):
        return datetime.date.fromisoformat(val)
    return None


def _parse_dimensions(dims_json: str | None) -> tuple[DimensionMember, ...]:
    """JSON 文字列から DimensionMember タプルを復元する。"""
    if not dims_json:
        return ()
    dims = json.loads(dims_json)
    return tuple(DimensionMember(axis=d["axis"], member=d["member"]) for d in dims)


def _parse_period(
    row: dict[str, Any],
) -> InstantPeriod | DurationPeriod:
    """行データから Period を復元する。"""
    if row["period_type"] == "instant":
        return InstantPeriod(instant=_parse_date(row["period_instant"]))
    return DurationPeriod(
        start_date=_parse_date(row["period_start"]),
        end_date=_parse_date(row["period_end"]),
    )


def deserialize_filing(row: dict[str, Any]) -> Filing:
    """dict 行から Filing を復元する。

    Args:
        row: Parquet 行の辞書。

    Returns:
        Filing オブジェクト。
    """
    return Filing(
        pubdate=row["pubdate"],
        company_code=row["company_code"],
        company_name=row["company_name"],
        title=row["title"],
        document_url=row["document_url"],
        xbrl_url=row["xbrl_url"],
        markets_string=row["markets_string"],
    )


def deserialize_line_item(row: dict[str, Any]) -> LineItem:
    """dict 行から LineItem を復元する。

    Args:
        row: Parquet 行の辞書。

    Returns:
        LineItem オブジェクト。
    """
    # value
    vtype = row["value_type"]
    if vtype == "decimal":
        value: Decimal | str | None = Decimal(row["value_numeric"])
    elif vtype == "str":
        value = row["value_text"]
    else:
        value = None

    # decimals
    if row.get("decimals_inf"):
        decimals: int | str | None = "INF"
    elif row.get("decimals_int") is not None:
        decimals = int(row["decimals_int"])
    else:
        decimals = None

    return LineItem(
        concept=row["concept"],
        namespace_uri=row["namespace_uri"],
        local_name=row["local_name"],
        label_ja=LabelInfo(
            text=row["label_ja_text"],
            role=row["label_ja_role"],
            lang="ja",
            source=LabelSource(row["label_ja_source"]),
        ),
        label_en=LabelInfo(
            text=row["label_en_text"],
            role=row["label_en_role"],
            lang="en",
            source=LabelSource(row["label_en_source"]),
        ),
        value=value,
        unit_ref=row.get("unit_ref"),
        decimals=decimals,
        context_id=row["context_id"],
        period=_parse_period(row),
        entity_id=row["entity_id"],
        dimensions=_parse_dimensions(row.get("dimensions_json")),
        is_nil=bool(row.get("is_nil", False)),
        source_line=_safe_int(row.get("source_line")),
        order=int(row["order"]),
    )


def deserialize_calc_linkbase(
    rows: list[dict[str, Any]],
) -> CalculationLinkbase:
    """dict 行リストから CalculationLinkbase を復元する。

    Args:
        rows: calc_edges.parquet の辞書リスト（1 つの doc_id 分）。

    Returns:
        CalculationLinkbase オブジェクト。
    """
    by_role: dict[str, list[CalculationArc]] = defaultdict(list)
    for row in rows:
        arc = CalculationArc(
            parent=row["parent"],
            child=row["child"],
            parent_href=row["parent_href"],
            child_href=row["child_href"],
            weight=int(row["weight"]),
            order=float(row["order"]),
            role_uri=row["role_uri"],
        )
        by_role[arc.role_uri].append(arc)

    trees: dict[str, CalculationTree] = {}
    for role_uri, arcs in by_role.items():
        children = {a.child for a in arcs}
        parents = {a.parent for a in arcs}
        roots = tuple(p for p in parents if p not in children)
        trees[role_uri] = CalculationTree(
            role_uri=role_uri,
            arcs=tuple(arcs),
            roots=roots,
        )

    return CalculationLinkbase(source_path=None, trees=trees)


def deserialize_statements(
    items: tuple[LineItem, ...],
    *,
    entity_id: str = "",
    calculation_linkbase: CalculationLinkbase | None = None,
    definition_parent_index: dict[str, str] | None = None,
) -> Statements:
    """復元済みパーツから Statements を直接構築する。

    Args:
        items: 復元済み LineItem タプル。
        entity_id: エンティティ ID。
        calculation_linkbase: 復元済み CalculationLinkbase。
        definition_parent_index: 復元済みの definition parent index。

    Returns:
        Statements オブジェクト。
    """
    return Statements(
        items=items,
        entity_id=entity_id,
        calculation_linkbase=calculation_linkbase,
        definition_parent_index=definition_parent_index,
    )
