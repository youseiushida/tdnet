"""パイプラインマッパー — concept → canonical key の名寄せロジック。

``extract_values()`` が使用するマッパーの型定義・デフォルト実装・ヘルパーを提供する。

設計原則:
    - マッパーは ``Callable[[LineItem, MapperContext], str | None]`` シグネチャ
    - ``str`` を返すとマッチ（canonical key）、``None`` で次のマッパーへ
    - パイプライン（リスト）の先頭マッパーほど高優先

デフォルトパイプライン::

    [summary_mapper, statement_mapper]

    1. summary_mapper: tse-ed-t サマリー科目（経営指標）
    2. statement_mapper: jppfs_cor PL/BS/CF の辞書引き
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tdnet.models.statement_mappings import (
    lookup_statement_exact,
    lookup_statement_normalized,
)
from tdnet.models.summary_mappings import lookup_summary

if TYPE_CHECKING:
    from tdnet.models.types import LineItem

__all__ = [
    "ConceptMapper",
    "MapperContext",
    "dict_mapper",
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

    TDnet 版は edinet と比べてシンプル。
    DEI 相当の情報はあるが、Definition/Calculation Linkbase は
    TDnet の iXBRL では通常提供されない。

    Attributes:
        entity_id: 証券コード等のエンティティ識別子。
        has_consolidated: 連結財務諸表の有無。
    """

    entity_id: str = ""
    has_consolidated: bool | None = None


def summary_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """tse-ed-t サマリー科目（経営成績の概況）から名寄せするマッパー。

    TDnet 決算短信の Summary 部分に含まれる科目を対象とする。
    """
    return lookup_summary(item.local_name)


def statement_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """財務諸表本体（PL/BS/CF）から名寄せするマッパー。

    jppfs_cor タクソノミの科目を対象とする。
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
    return [summary_mapper, statement_mapper]
