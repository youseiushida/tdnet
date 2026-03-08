import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from xbrl_core import DimensionMember as DimensionMember
from xbrl_core.periods import DurationPeriod as DurationPeriod, InstantPeriod as InstantPeriod, Period as Period

class LabelSource(enum.Enum):
    """ラベルの情報源。"""
    STANDARD = 'standard'
    FILER = 'filer'
    FALLBACK = 'fallback'

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
    decimals: int | Literal['INF'] | None
    context_id: str
    period: Period
    entity_id: str
    dimensions: tuple[DimensionMember, ...]
    is_nil: bool
    source_line: int | None
    order: int

def convert_line_item(xc_item: object) -> LineItem:
    """xbrl_core の LineItem → tdnet LineItem。"""
