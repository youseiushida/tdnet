"""edinet 互換の公開型定義。

xbrl_core の内部型を仕様書準拠のインターフェースに変換する。
- LabelSource.EXTENSION → LabelSource.FILER
- LineItem.labels タプル → LineItem.label_ja / label_en フィールド
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from xbrl_core import DimensionMember
from xbrl_core.periods import InstantPeriod, DurationPeriod, Period


class LabelSource(enum.Enum):
    """ラベルの情報源。"""

    STANDARD = "standard"
    FILER = "filer"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class LabelInfo:
    """解決されたラベル情報。"""

    text: str
    role: str
    lang: str
    source: LabelSource


@dataclass(frozen=True, slots=True, kw_only=True)
class LineItem:
    """型付き・ラベル付きの XBRL Fact。

    edinet と同一のフィールド構成。
    """

    concept: str
    namespace_uri: str
    local_name: str
    label_ja: LabelInfo
    label_en: LabelInfo
    value: Decimal | str | None
    unit_ref: str | None
    decimals: int | Literal["INF"] | None
    context_id: str
    period: Period
    entity_id: str
    dimensions: tuple[DimensionMember, ...]
    is_nil: bool
    source_line: int | None
    order: int


# ---------------------------------------------------------------------------
# xbrl_core → tdnet 変換
# ---------------------------------------------------------------------------

_LABEL_ROLE = "http://www.xbrl.org/2003/role/label"

_FALLBACK_JA = LabelInfo(text="", role=_LABEL_ROLE, lang="ja", source=LabelSource.FALLBACK)
_FALLBACK_EN = LabelInfo(text="", role=_LABEL_ROLE, lang="en", source=LabelSource.FALLBACK)

_SOURCE_MAP = {
    "STANDARD": LabelSource.STANDARD,
    "EXTENSION": LabelSource.FILER,
    "FALLBACK": LabelSource.FALLBACK,
}


def _convert_label(xc_label: object) -> LabelInfo:
    """xbrl_core の LabelInfo → tdnet LabelInfo。"""
    src = _SOURCE_MAP.get(xc_label.source.name, LabelSource.FALLBACK)  # type: ignore[union-attr]
    return LabelInfo(
        text=xc_label.text,  # type: ignore[union-attr]
        role=xc_label.role,  # type: ignore[union-attr]
        lang=xc_label.lang,  # type: ignore[union-attr]
        source=src,
    )


def convert_line_item(xc_item: object) -> LineItem:
    """xbrl_core の LineItem → tdnet LineItem。"""
    label_ja = _FALLBACK_JA
    label_en = _FALLBACK_EN
    for lab in xc_item.labels:  # type: ignore[union-attr]
        if lab.lang == "ja":
            label_ja = _convert_label(lab)
        elif lab.lang == "en":
            label_en = _convert_label(lab)

    # FALLBACK のとき local_name をテキストに設定
    if label_ja.source is LabelSource.FALLBACK:
        label_ja = LabelInfo(
            text=xc_item.local_name,  # type: ignore[union-attr]
            role=_LABEL_ROLE,
            lang="ja",
            source=LabelSource.FALLBACK,
        )
    if label_en.source is LabelSource.FALLBACK:
        label_en = LabelInfo(
            text=xc_item.local_name,  # type: ignore[union-attr]
            role=_LABEL_ROLE,
            lang="en",
            source=LabelSource.FALLBACK,
        )

    return LineItem(
        concept=xc_item.concept,  # type: ignore[union-attr]
        namespace_uri=xc_item.namespace_uri,  # type: ignore[union-attr]
        local_name=xc_item.local_name,  # type: ignore[union-attr]
        label_ja=label_ja,
        label_en=label_en,
        value=xc_item.value,  # type: ignore[union-attr]
        unit_ref=xc_item.unit_ref,  # type: ignore[union-attr]
        decimals=xc_item.decimals,  # type: ignore[union-attr]
        context_id=xc_item.context_id,  # type: ignore[union-attr]
        period=xc_item.period,  # type: ignore[union-attr]
        entity_id=xc_item.entity_id,  # type: ignore[union-attr]
        dimensions=xc_item.dimensions,  # type: ignore[union-attr]
        is_nil=xc_item.is_nil,  # type: ignore[union-attr]
        source_line=xc_item.source_line,  # type: ignore[union-attr]
        order=xc_item.order,  # type: ignore[union-attr]
    )
