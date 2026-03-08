"""DataFrame → Filing + Statements 復元。"""

from __future__ import annotations

import json
import math
from datetime import date
from decimal import Decimal

import pandas as pd
from xbrl_core import DimensionMember
from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.filing import Filing
from tdnet.models.statements import Statements
from tdnet.models.types import LabelInfo, LabelSource, LineItem


def _restore_label(
    text: str,
    role: str,
    source_str: str,
    lang: str,
) -> LabelInfo:
    """カラム値から LabelInfo を復元する。

    Args:
        text: ラベルテキスト。
        role: ラベルロール URI。
        source_str: LabelSource の文字列値。
        lang: 言語コード。

    Returns:
        復元された LabelInfo。
    """
    return LabelInfo(
        text=text,
        role=role,
        lang=lang,
        source=LabelSource(source_str),
    )


def _restore_value(
    numeric: object,
    text: object,
) -> Decimal | str | None:
    """value_numeric / value_text から元の value を復元する。

    Args:
        numeric: float64 値 (NaN なら無効)。
        text: 文字列値。

    Returns:
        復元された値。
    """
    if text is not None and not (isinstance(text, float) and math.isnan(text)):
        return str(text)
    if numeric is not None and not (isinstance(numeric, float) and math.isnan(numeric)):
        return Decimal(str(numeric))
    return None


def _restore_decimals(
    decimals_int: object,
    decimals_is_inf: bool,
) -> int | str | None:
    """decimals_int / decimals_is_inf から元の decimals を復元する。

    Args:
        decimals_int: 整数値 (NaN なら無効)。
        decimals_is_inf: True なら "INF"。

    Returns:
        復元された decimals 値。
    """
    if decimals_is_inf:
        return "INF"
    if decimals_int is not None and not (
        isinstance(decimals_int, float) and math.isnan(decimals_int)
    ):
        return int(decimals_int)
    return None


def _restore_period(
    period_type: str,
    period_instant: object,
    period_start: object,
    period_end: object,
) -> InstantPeriod | DurationPeriod:
    """期間カラムから Period を復元する。

    Args:
        period_type: "instant" or "duration"。
        period_instant: InstantPeriod の日付。
        period_start: DurationPeriod の開始日。
        period_end: DurationPeriod の終了日。

    Returns:
        復元された Period。
    """
    if period_type == "instant":
        instant = _to_date(period_instant)
        return InstantPeriod(instant=instant)
    start = _to_date(period_start)
    end = _to_date(period_end)
    return DurationPeriod(start_date=start, end_date=end)


def _to_date(val: object) -> date:
    """各種日付型を date に変換する。"""
    if isinstance(val, date):
        return val
    if hasattr(val, "date"):
        return val.date()  # type: ignore[union-attr]
    return date.fromisoformat(str(val))


def _restore_dimensions(dims_json: str) -> tuple[DimensionMember, ...]:
    """JSON 文字列から dimensions を復元する。

    Args:
        dims_json: JSON 配列文字列。

    Returns:
        復元された DimensionMember のタプル。
    """
    items = json.loads(dims_json)
    return tuple(DimensionMember(axis=d["axis"], member=d["member"]) for d in items)


def _restore_line_item(row: pd.Series) -> LineItem:  # type: ignore[type-arg]
    """DataFrame の1行から LineItem を復元する。

    Args:
        row: line_items DataFrame の行。

    Returns:
        復元された LineItem。
    """
    source_line_raw = row["source_line"]
    source_line: int | None = None
    if source_line_raw is not None and not (
        isinstance(source_line_raw, float) and math.isnan(source_line_raw)
    ):
        source_line = int(source_line_raw)

    return LineItem(
        concept=row["concept"],
        namespace_uri=row["namespace_uri"],
        local_name=row["local_name"],
        label_ja=_restore_label(
            row["label_ja_text"], row["label_ja_role"],
            row["label_ja_source"], "ja",
        ),
        label_en=_restore_label(
            row["label_en_text"], row["label_en_role"],
            row["label_en_source"], "en",
        ),
        value=_restore_value(row["value_numeric"], row["value_text"]),
        unit_ref=row["unit_ref"] if not _is_nan(row["unit_ref"]) else None,
        decimals=_restore_decimals(row["decimals_int"], row["decimals_is_inf"]),
        context_id=row["context_id"],
        period=_restore_period(
            row["period_type"],
            row["period_instant"],
            row["period_start"],
            row["period_end"],
        ),
        entity_id=row["entity_id"],
        dimensions=_restore_dimensions(row["dimensions"]),
        is_nil=bool(row["is_nil"]),
        source_line=source_line,
        order=int(row["order"]),
    )


def _is_nan(val: object) -> bool:
    """NaN 判定。"""
    return isinstance(val, float) and math.isnan(val)


def _restore_filings_and_statements(
    filings_df: pd.DataFrame,
    items_df: pd.DataFrame,
) -> list[tuple[Filing, Statements | None]]:
    """filings / line_items DataFrame から Filing + Statements を復元する。

    Args:
        filings_df: filings.parquet の DataFrame。
        items_df: line_items.parquet の DataFrame。

    Returns:
        (Filing, Statements | None) のリスト。
    """
    # _seq ごとに line_items をグループ化
    items_by_seq: dict[int, list[LineItem]] = {}
    for _, row in items_df.iterrows():
        seq = int(row["_seq"])
        items_by_seq.setdefault(seq, []).append(_restore_line_item(row))

    result: list[tuple[Filing, Statements | None]] = []
    for _, frow in filings_df.iterrows():
        seq = int(frow["_seq"])
        filing = Filing(
            pubdate=frow["pubdate"],
            company_code=frow["company_code"],
            company_name=frow["company_name"],
            title=frow["title"],
            document_url=frow["document_url"],
            xbrl_url=frow["xbrl_url"],
            markets_string=frow["markets_string"],
        )

        if not frow["has_statements"]:
            result.append((filing, None))
            continue

        line_items = items_by_seq.get(seq, [])
        # entity_id は line_items の先頭から取得
        entity_id = line_items[0].entity_id if line_items else ""
        stmts = Statements(
            items=tuple(line_items),
            entity_id=entity_id,
        )
        result.append((filing, stmts))

    return result
