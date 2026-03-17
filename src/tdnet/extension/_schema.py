"""Parquet テーブルの明示的 PyArrow スキーマ定義。

繰り返しの多い文字列カラムに ``pa.dictionary()`` を適用し、
型推論を省略することで書き出し速度とファイルサイズを改善する。
"""

from __future__ import annotations

from typing import Any


def _require_pa() -> Any:
    """pyarrow を遅延 import する。"""
    import pyarrow as pa

    return pa


def filings_schema() -> Any:
    """filings テーブルのスキーマを返す。

    Returns:
        pa.Schema: filings テーブル用の PyArrow スキーマ。
    """
    pa = _require_pa()
    return pa.schema(
        [
            pa.field("doc_id", pa.string()),
            pa.field("pubdate", pa.string()),
            pa.field("company_code", pa.dictionary(pa.int16(), pa.string())),
            pa.field("company_name", pa.string()),
            pa.field("title", pa.string()),
            pa.field("document_url", pa.string()),
            pa.field("xbrl_url", pa.string()),
            pa.field("markets_string", pa.dictionary(pa.int8(), pa.string())),
            pa.field("has_xbrl", pa.bool_()),
        ]
    )


def line_items_schema() -> Any:
    """line_items / text_blocks テーブルのスキーマを返す。

    Returns:
        pa.Schema: line_items テーブル用の PyArrow スキーマ。
    """
    pa = _require_pa()
    return pa.schema(
        [
            pa.field("doc_id", pa.dictionary(pa.int16(), pa.string())),
            pa.field("concept", pa.dictionary(pa.int16(), pa.string())),
            pa.field("namespace_uri", pa.dictionary(pa.int8(), pa.string())),
            pa.field("local_name", pa.dictionary(pa.int16(), pa.string())),
            pa.field("label_ja_text", pa.string()),
            pa.field("label_ja_role", pa.dictionary(pa.int8(), pa.string())),
            pa.field("label_ja_source", pa.dictionary(pa.int8(), pa.string())),
            pa.field("label_en_text", pa.string()),
            pa.field("label_en_role", pa.dictionary(pa.int8(), pa.string())),
            pa.field("label_en_source", pa.dictionary(pa.int8(), pa.string())),
            pa.field("value_numeric", pa.string()),
            pa.field("value_text", pa.string()),
            pa.field("value_type", pa.dictionary(pa.int8(), pa.string())),
            pa.field("unit_ref", pa.dictionary(pa.int8(), pa.string())),
            pa.field("decimals_int", pa.int32()),
            pa.field("decimals_inf", pa.bool_()),
            pa.field("context_id", pa.dictionary(pa.int16(), pa.string())),
            pa.field("period_type", pa.dictionary(pa.int8(), pa.string())),
            pa.field("period_instant", pa.date32()),
            pa.field("period_start", pa.date32()),
            pa.field("period_end", pa.date32()),
            pa.field("entity_id", pa.dictionary(pa.int16(), pa.string())),
            pa.field("dimensions_json", pa.string()),
            pa.field("is_nil", pa.bool_()),
            pa.field("source_line", pa.int32()),
            pa.field("order", pa.int32()),
        ]
    )


def calc_edges_schema() -> Any:
    """calc_edges テーブルのスキーマを返す。

    Returns:
        pa.Schema: calc_edges テーブル用の PyArrow スキーマ。
    """
    pa = _require_pa()
    return pa.schema(
        [
            pa.field("doc_id", pa.dictionary(pa.int16(), pa.string())),
            pa.field("role_uri", pa.dictionary(pa.int8(), pa.string())),
            pa.field("parent", pa.dictionary(pa.int16(), pa.string())),
            pa.field("child", pa.dictionary(pa.int16(), pa.string())),
            pa.field("parent_href", pa.string()),
            pa.field("child_href", pa.string()),
            pa.field("weight", pa.float64()),
            pa.field("order", pa.float64()),
        ]
    )


def def_parents_schema() -> Any:
    """def_parents テーブルのスキーマを返す。

    Returns:
        pa.Schema: def_parents テーブル用の PyArrow スキーマ。
    """
    pa = _require_pa()
    return pa.schema(
        [
            pa.field("doc_id", pa.dictionary(pa.int16(), pa.string())),
            pa.field("child_concept", pa.dictionary(pa.int16(), pa.string())),
            pa.field("parent_standard_concept", pa.dictionary(pa.int16(), pa.string())),
        ]
    )


SCHEMAS: dict[str, Any] = {
    "filings": filings_schema,
    "line_items": line_items_schema,
    "text_blocks": line_items_schema,
    "calc_edges": calc_edges_schema,
    "def_parents": def_parents_schema,
}
