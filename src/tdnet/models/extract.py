"""正規化キーによる財務数値の抽出ユーティリティ。

パイプラインマッパーで Statements を 1 パス走査し、
canonical key で値を取り出す。

デフォルトパイプライン ``[dividend_mapper, forecast_mapper, summary_mapper, statement_mapper]``
で tse-ed-t サマリー科目 + jppfs_cor PL/BS/CF 本体を名寄せする。

使用例::

    from tdnet.models.extract import extract_values, extracted_to_dict
    from tdnet.models.ck import CK

    result = extract_values(stmts, [CK.REVENUE, CK.OPERATING_INCOME],
                            period="current", consolidated=True)
    row = extracted_to_dict(result)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from tdnet.models.types import LineItem

from tdnet.mapper import (
    ConceptMapper,
    MapperContext,
    get_default_pipeline,
)
from tdnet.models.ck import CK

if TYPE_CHECKING:
    from tdnet.models.statements import Statements

__all__ = ["ExtractedValue", "extract_values", "extracted_to_dict"]

_CK_MEMBERS: frozenset[str] = frozenset(CK)

# DPS・配当関連 CK は常に NonConsolidatedMember のため
# consolidated=True でもフィルタしない
_ALWAYS_NONCONSOLIDATED_CKS: frozenset[str] = frozenset({
    CK.DPS,
    CK.INTERIM_DPS,
    CK.FORECAST_DPS,
    CK.COMMEMORATIVE_DIVIDEND,
    CK.EXTRA_DIVIDEND,
    CK.TOTAL_DIVIDEND_PAID,
    CK.PAYOUT_RATIO,
    CK.DIVIDENDS_FROM_SURPLUS,
})


@dataclass(frozen=True, slots=True)
class ExtractedValue:
    """正規化キーで抽出された財務数値。

    Attributes:
        canonical_key: 正規化キー。
        value: 抽出された値。
        item: 元の LineItem。
        mapper_name: 値を採用したマッパー関数の名前。
    """

    canonical_key: str
    value: Decimal | str | None
    item: LineItem
    mapper_name: str | None


# ---------------------------------------------------------------------------
# 内部ヘルパー
# ---------------------------------------------------------------------------


def _period_end_date(period_obj: object) -> object | None:
    """Period オブジェクトから終了日を取得する。"""
    if hasattr(period_obj, "end_date"):
        return period_obj.end_date  # DurationPeriod
    if hasattr(period_obj, "instant"):
        return period_obj.instant  # InstantPeriod
    return None


def _detect_current_period_end(items: tuple[LineItem, ...]) -> object | None:
    """当期の期間終了日を検出する。

    1. CurrentMember ディメンション付きアイテムがあればその終了日を返す。
    2. なければ、monetary アイテムの期間終了日の最頻値を返す。
    """
    from tdnet.models.statements import _period_key

    for item in items:
        if _period_key(item) == "current":
            end = _period_end_date(item.period)
            if end is not None:
                return end

    # Fallback: monetary アイテムの期間終了日の最頻値
    from collections import Counter
    end_counts: Counter[object] = Counter()
    for item in items:
        if item.unit_ref is not None:
            end = _period_end_date(item.period)
            if end is not None:
                end_counts[end] += 1
    if end_counts:
        return end_counts.most_common(1)[0][0]
    return None


def _filter_period(
    item: LineItem,
    *,
    period: Literal["current", "prior"] | None,
    current_period_end: object | None = None,
) -> bool:
    """期間フィルタのみ適用。通過すれば True。"""
    from tdnet.models.statements import _period_key

    if period is None:
        return True

    pk = _period_key(item)
    if pk is not None and pk != period:
        return False
    # Dimension がない場合は XBRL 期間の実日付で判定
    if pk is None and current_period_end is not None:
        item_end = _period_end_date(item.period)
        if item_end is not None:
            is_current = (item_end == current_period_end)
            if period == "current" and not is_current:
                return False
            if period == "prior" and is_current:
                return False

    return True


def _filter_consolidated(
    item: LineItem,
    *,
    consolidated: bool | None,
    ck: str | None = None,
) -> bool:
    """連結フィルタ。CK が _ALWAYS_NONCONSOLIDATED_CKS に含まれる場合はスキップ。"""
    from tdnet.models.statements import _is_consolidated

    if consolidated is None:
        return True

    # DPS 等は常に NonConsolidatedMember → consolidated フィルタ不適用
    if ck is not None and ck in _ALWAYS_NONCONSOLIDATED_CKS:
        return True

    cons = _is_consolidated(item)
    if cons is not None and cons != consolidated:
        return False

    return True


def _item_should_replace(
    existing_item: LineItem,
    new_item: LineItem,
    existing_idx: int,
    new_idx: int,
    period: Literal["current", "prior"] | None,
) -> bool:
    """新しいアイテムが既存アイテムを置き換えるべきか判定。"""
    from tdnet.models.statements import _period_key

    # パイプライン上位マッパーを優先
    if new_idx < existing_idx:
        return True
    if new_idx > existing_idx:
        return False

    # 同一マッパー: period=None なら current を優先
    if period is None:
        existing_pk = _period_key(existing_item)
        new_pk = _period_key(new_item)
        if existing_pk != new_pk:
            if new_pk == "current":
                return True
            if existing_pk == "current":
                return False

    # 非 None 値を優先
    if new_item.value is not None and existing_item.value is None:
        return True

    return False


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def extract_values(
    source: Statements,
    keys: Sequence[str] | None = None,
    *,
    period: Literal["current", "prior"] | None = None,
    consolidated: bool | None = None,
    mapper: ConceptMapper | Sequence[ConceptMapper] | None = None,
) -> dict[str, ExtractedValue | None]:
    """正規化キーで財務データから値を抽出する。

    Statements を渡すと _items 全体をパイプラインマッパーで
    1 パス走査する。

    Args:
        source: 抽出対象の Statements。
        keys: 抽出する正規化キーのシーケンス。
            None の場合は全マッピング可能科目を抽出する。
        period: 期間フィルタ。"current" で当期、"prior" で前期。
        consolidated: 連結フィルタ。True で連結、False で個別。
        mapper: マッパーまたはマッパーのシーケンス。
            None の場合は [dividend_mapper, forecast_mapper, summary_mapper, statement_mapper]。

    Returns:
        {canonical_key: ExtractedValue | None} の辞書。
    """
    from tdnet.models.statements import Statements as _Statements

    if not isinstance(source, _Statements):
        raise TypeError(
            f"Statements を渡してください（got {type(source).__name__}）"
        )

    # マッパーパイプライン解決
    if mapper is None:
        pipeline: list[ConceptMapper] = get_default_pipeline()
    elif callable(mapper) and not isinstance(mapper, Sequence):
        pipeline = [mapper]
    else:
        pipeline = list(mapper)

    # MapperContext 構築
    ctx = MapperContext(
        entity_id=source._entity_id,
    )

    # キーフィルタ
    target_keys: set[str] | None = (
        {str(k) for k in keys} if keys is not None else None
    )

    # 当期の終了日を検出（dimension なしアイテムの期間判定用）
    current_end = (
        _detect_current_period_end(source._items) if period is not None else None
    )

    # 1 パスマッパーループ
    # ck_to_item: {canonical_key: (LineItem, pipeline_position, mapper_name)}
    ck_to_item: dict[str, tuple[LineItem, int, str | None]] = {}

    for item in source:
        # 期間フィルタ（マッピング前に適用）
        if not _filter_period(
            item,
            period=period,
            current_period_end=current_end,
        ):
            continue

        for idx, mapper_fn in enumerate(pipeline):
            ck = mapper_fn(item, ctx)
            if ck is None:
                continue
            if target_keys is not None and ck not in target_keys:
                continue

            # 連結フィルタ（CK-aware: DPS 等は NonConsolidated を許容）
            if not _filter_consolidated(
                item, consolidated=consolidated, ck=ck,
            ):
                break

            name = getattr(mapper_fn, "__name__", None)
            existing = ck_to_item.get(ck)
            if existing is None:
                ck_to_item[ck] = (item, idx, name)
            elif _item_should_replace(
                existing[0], item, existing[1], idx, period,
            ):
                ck_to_item[ck] = (item, idx, name)
            break  # 1 item に対して最初にマッチしたマッパーを採用

    # 結果構築
    if keys is None:
        return {
            ck: ExtractedValue(
                canonical_key=ck, value=item.value, item=item,
                mapper_name=name,
            )
            for ck, (item, _idx, name) in ck_to_item.items()
        }

    result: dict[str, ExtractedValue | None] = {}
    for key in keys:
        key_str = str(key)
        entry = ck_to_item.get(key_str)
        if entry is not None:
            item, _idx, name = entry
            result[key_str] = ExtractedValue(
                canonical_key=key_str, value=item.value, item=item,
                mapper_name=name,
            )
        else:
            result[key_str] = None
    return result


def extracted_to_dict(
    *extracted_dicts: dict[str, ExtractedValue | None],
) -> dict[str, Decimal | str | None]:
    """extract_values() の結果を {key: value} 辞書に変換する。

    複数の辞書を渡すとマージされる。
    """
    result: dict[str, Decimal | str | None] = {}
    for extracted in extracted_dicts:
        for k, ev in extracted.items():
            if ev is not None:
                result[k] = ev.value
            elif k not in result:
                result[k] = None
    return result
