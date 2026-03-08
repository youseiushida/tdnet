from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from tdnet.mapper import ConceptMapper
from tdnet.models.statements import Statements
from tdnet.models.types import LineItem
from typing import Literal

__all__ = ['ExtractedValue', 'extract_values', 'extracted_to_dict']

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

def extract_values(source: Statements, keys: Sequence[str] | None = None, *, period: Literal['current', 'prior'] | None = None, consolidated: bool | None = None, mapper: ConceptMapper | Sequence[ConceptMapper] | None = None) -> dict[str, ExtractedValue | None]:
    '''正規化キーで財務データから値を抽出する。

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
    '''
def extracted_to_dict(*extracted_dicts: dict[str, ExtractedValue | None]) -> dict[str, Decimal | str | None]:
    """extract_values() の結果を {key: value} 辞書に変換する。

    複数の辞書を渡すとマージされる。
    """
