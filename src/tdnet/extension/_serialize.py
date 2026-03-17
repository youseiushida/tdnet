"""ドメインオブジェクト → dict 行（Parquet 行）への変換。"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xbrl_core import CalculationLinkbase
    from xbrl_core.linkbase.definition import DefinitionTree

    from tdnet.filing import Filing
    from tdnet.models.types import LineItem

_TEXTBLOCK_SUFFIX = "TextBlock"


def is_text_block(local_name: str) -> bool:
    """TextBlock 系の Fact かどうかを判定する。

    Args:
        local_name: 概念のローカル名。

    Returns:
        ``True`` なら TextBlock。
    """
    return local_name.endswith(_TEXTBLOCK_SUFFIX)


def serialize_filing(
    filing: Filing,
    has_xbrl: bool,
) -> dict[str, Any]:
    """Filing 1 件を行辞書に変換する。

    Args:
        filing: 変換対象の Filing。
        has_xbrl: XBRL パースに成功したかどうか。

    Returns:
        filings.parquet 用の行辞書。
    """
    return {
        "doc_id": filing.doc_id,
        "pubdate": filing.pubdate,
        "company_code": filing.company_code,
        "company_name": filing.company_name,
        "title": filing.title,
        "document_url": filing.document_url,
        "xbrl_url": filing.xbrl_url,
        "markets_string": filing.markets_string,
        "has_xbrl": has_xbrl,
    }


def serialize_line_item(
    item: LineItem,
    doc_id: str,
) -> dict[str, Any]:
    """LineItem 1 件を行辞書に変換する。

    Args:
        item: 変換対象の LineItem。
        doc_id: 対応する Filing の doc_id。

    Returns:
        line_items.parquet / text_blocks.parquet 用の行辞書。
    """
    from xbrl_core.periods import InstantPeriod

    # value 型判別
    if isinstance(item.value, Decimal):
        value_numeric = str(item.value)
        value_text = None
        value_type = "decimal"
    elif isinstance(item.value, str):
        value_numeric = None
        value_text = item.value
        value_type = "str"
    else:
        value_numeric = None
        value_text = None
        value_type = "none"

    # decimals
    if item.decimals == "INF":
        decimals_int = None
        decimals_inf = True
    elif item.decimals is not None:
        decimals_int = item.decimals
        decimals_inf = False
    else:
        decimals_int = None
        decimals_inf = False

    # period
    period = item.period
    if isinstance(period, InstantPeriod):
        period_type = "instant"
        period_instant = period.instant
        period_start = None
        period_end = None
    else:
        period_type = "duration"
        period_instant = None
        period_start = period.start_date
        period_end = period.end_date

    # dimensions
    if item.dimensions:
        dims = [{"axis": d.axis, "member": d.member} for d in item.dimensions]
        dimensions_json = json.dumps(dims, ensure_ascii=False)
    else:
        dimensions_json = None

    return {
        "doc_id": doc_id,
        "concept": item.concept,
        "namespace_uri": item.namespace_uri,
        "local_name": item.local_name,
        "label_ja_text": item.label_ja.text,
        "label_ja_role": item.label_ja.role,
        "label_ja_source": item.label_ja.source.value,
        "label_en_text": item.label_en.text,
        "label_en_role": item.label_en.role,
        "label_en_source": item.label_en.source.value,
        "value_numeric": value_numeric,
        "value_text": value_text,
        "value_type": value_type,
        "unit_ref": item.unit_ref,
        "decimals_int": decimals_int,
        "decimals_inf": decimals_inf,
        "context_id": item.context_id,
        "period_type": period_type,
        "period_instant": period_instant,
        "period_start": period_start,
        "period_end": period_end,
        "entity_id": item.entity_id,
        "dimensions_json": dimensions_json,
        "is_nil": item.is_nil,
        "source_line": item.source_line,
        "order": item.order,
    }


def serialize_calc_edges(
    calc_linkbase: CalculationLinkbase,
    doc_id: str,
) -> list[dict[str, Any]]:
    """CalculationLinkbase を dict 行リストに変換する。

    Args:
        calc_linkbase: CalculationLinkbase オブジェクト。
        doc_id: 対応する Filing の doc_id。

    Returns:
        calc_edges.parquet 用の辞書リスト。
    """
    rows: list[dict[str, Any]] = []
    for tree in calc_linkbase.trees.values():
        for arc in tree.arcs:
            rows.append(
                {
                    "doc_id": doc_id,
                    "role_uri": arc.role_uri,
                    "parent": arc.parent,
                    "child": arc.child,
                    "parent_href": arc.parent_href,
                    "child_href": arc.child_href,
                    "weight": arc.weight,
                    "order": arc.order,
                }
            )
    return rows


def serialize_def_parents(
    definition_linkbase: dict[str, DefinitionTree] | None,
    doc_id: str,
) -> list[dict[str, Any]]:
    """DefinitionLinkbase → parent_index → dict 行リストに変換する。

    Args:
        definition_linkbase: Definition Linkbase の dict。
        doc_id: 対応する Filing の doc_id。

    Returns:
        def_parents.parquet 用の辞書リスト。
    """
    from tdnet.mapper import build_parent_index

    parent_index = build_parent_index(definition_linkbase)
    rows: list[dict[str, Any]] = []
    for child_concept, parent_concept in parent_index.items():
        rows.append(
            {
                "doc_id": doc_id,
                "child_concept": child_concept,
                "parent_standard_concept": parent_concept,
            }
        )
    return rows
