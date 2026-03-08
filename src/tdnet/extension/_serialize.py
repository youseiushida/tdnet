"""Filing + Statements → DataFrame 変換。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tdnet.filing import Filing
    from tdnet.models.statements import Statements
    from tdnet.models.types import LineItem


def _serialize_period(item: LineItem) -> dict[str, object]:
    """LineItem の period を Parquet 用のカラムに変換する。"""
    from xbrl_core.periods import InstantPeriod, DurationPeriod

    period = item.period
    if isinstance(period, InstantPeriod):
        return {
            "period_type": "instant",
            "period_instant": period.instant,
            "period_start": None,
            "period_end": None,
        }
    if isinstance(period, DurationPeriod):
        return {
            "period_type": "duration",
            "period_instant": None,
            "period_start": period.start_date,
            "period_end": period.end_date,
        }
    return {
        "period_type": "unknown",
        "period_instant": None,
        "period_start": None,
        "period_end": None,
    }


def _serialize_dimensions(item: LineItem) -> str:
    """dimensions を JSON 文字列に変換する。"""
    if not item.dimensions:
        return "[]"
    return json.dumps(
        [{"axis": d.axis, "member": d.member} for d in item.dimensions],
        ensure_ascii=False,
    )


def _serialize_value(item: LineItem) -> dict[str, object]:
    """value を numeric / text カラムに分離する。"""
    if isinstance(item.value, Decimal):
        return {"value_numeric": float(item.value), "value_text": None}
    if isinstance(item.value, str):
        return {"value_numeric": None, "value_text": item.value}
    return {"value_numeric": None, "value_text": None}


def _serialize_decimals(item: LineItem) -> dict[str, object]:
    """decimals を int / is_inf カラムに分離する。"""
    if item.decimals == "INF":
        return {"decimals_int": None, "decimals_is_inf": True}
    if isinstance(item.decimals, int):
        return {"decimals_int": item.decimals, "decimals_is_inf": False}
    return {"decimals_int": None, "decimals_is_inf": False}


def _filing_rows(
    data: Sequence[tuple[Filing, Statements | None]],
) -> list[dict[str, object]]:
    """Filing のリストを行辞書のリストに変換する。

    Args:
        data: (Filing, Statements | None) のシーケンス。

    Returns:
        filings.parquet 用の行辞書リスト。
    """
    rows: list[dict[str, object]] = []
    for seq, (filing, stmts) in enumerate(data):
        rows.append({
            "_seq": seq,
            "doc_id": filing.doc_id,
            "pubdate": filing.pubdate,
            "company_code": filing.company_code,
            "company_name": filing.company_name,
            "title": filing.title,
            "document_url": filing.document_url,
            "xbrl_url": filing.xbrl_url,
            "markets_string": filing.markets_string,
            "has_statements": stmts is not None,
        })
    return rows


def _line_item_rows(
    data: Sequence[tuple[Filing, Statements | None]],
) -> list[dict[str, object]]:
    """全 LineItem を行辞書のリストに変換する。

    Args:
        data: (Filing, Statements | None) のシーケンス。

    Returns:
        line_items.parquet 用の行辞書リスト。
    """
    rows: list[dict[str, object]] = []
    for seq, (_filing, stmts) in enumerate(data):
        if stmts is None:
            continue
        for item in stmts:
            row: dict[str, object] = {
                "_seq": seq,
                "concept": item.concept,
                "namespace_uri": item.namespace_uri,
                "local_name": item.local_name,
                "label_ja_text": item.label_ja.text,
                "label_ja_role": item.label_ja.role,
                "label_ja_source": item.label_ja.source.value,
                "label_en_text": item.label_en.text,
                "label_en_role": item.label_en.role,
                "label_en_source": item.label_en.source.value,
                "unit_ref": item.unit_ref,
                "context_id": item.context_id,
                "entity_id": item.entity_id,
                "dimensions": _serialize_dimensions(item),
                "is_nil": item.is_nil,
                "source_line": item.source_line,
                "order": item.order,
            }
            row.update(_serialize_value(item))
            row.update(_serialize_decimals(item))
            row.update(_serialize_period(item))
            rows.append(row)
    return rows
