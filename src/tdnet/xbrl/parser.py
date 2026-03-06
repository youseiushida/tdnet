"""TDnet XBRL ZIP の解析。"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

from xbrl_core import (
    ParsedXBRL,
    build_line_items,
    merge_ixbrl_results,
    parse_ixbrl_facts,
    structure_contexts,
)

from tdnet.models.statements import Statements
from tdnet.models.types import convert_line_item
from tdnet.xbrl.taxonomy import TdnetLabelResolver

logger = logging.getLogger(__name__)


def parse_zip(
    zip_data: bytes,
    *,
    taxonomy_path: str | Path | None = None,
    entity_id: str = "",
) -> Statements:
    """XBRL ZIP を解析して Statements を返す。

    Args:
        zip_data: ZIP ファイルのバイト列。
        taxonomy_path: タクソノミのパス。None の場合はバンドルを使用。
        entity_id: エンティティ ID。

    Returns:
        Statements コンテナ。
    """
    ixbrl_files = _extract_ixbrl_from_zip(zip_data)
    if not ixbrl_files:
        return Statements(items=(), entity_id=entity_id)

    return parse_ixbrl_files(
        ixbrl_files,
        taxonomy_path=taxonomy_path,
        entity_id=entity_id,
    )


def parse_ixbrl_files(
    files: dict[str, bytes],
    *,
    taxonomy_path: str | Path | None = None,
    entity_id: str = "",
) -> Statements:
    """複数の iXBRL ファイルを解析して Statements を返す。

    Args:
        files: ファイル名をキー、iXBRL bytes を値とする辞書。
        taxonomy_path: タクソノミのパス。
        entity_id: エンティティ ID。

    Returns:
        Statements コンテナ。
    """
    resolver = TdnetLabelResolver(taxonomy_path)
    warnings: list[str] = []

    parsed_results: list[ParsedXBRL] = []
    for name, data in sorted(files.items()):
        try:
            parsed = parse_ixbrl_facts(data, source_path=name, strict=False)
            parsed_results.append(parsed)
        except Exception as exc:
            warnings.append(f"Failed to parse {name}: {exc}")
            logger.warning("Failed to parse %s: %s", name, exc)

    if not parsed_results:
        return Statements(items=(), entity_id=entity_id, warnings=tuple(warnings))

    merged = merge_ixbrl_results(parsed_results)
    ctx_map = structure_contexts(merged.contexts)

    xc_items = build_line_items(
        merged.facts,
        ctx_map,
        resolver=resolver,
        langs=("ja", "en"),
    )

    # xbrl_core LineItem → tdnet LineItem に変換
    items = tuple(convert_line_item(it) for it in xc_items)

    # entity_id の自動検出
    if not entity_id and items:
        entity_id = items[0].entity_id

    return Statements(
        items=items,
        entity_id=entity_id,
        warnings=tuple(warnings),
    )


def _extract_ixbrl_from_zip(zip_data: bytes) -> dict[str, bytes]:
    """ZIP からiXBRL ファイルを抽出する。

    TDnet の ZIP は 2 種類の構造:
    - 0812 (決算短信): XBRLData/Summary/ + XBRLData/Attachment/
    - 0912 (修正系): フラット

    iXBRL ファイルは ``-ixbrl.htm`` で終わる。
    """
    result: dict[str, bytes] = {}

    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                lower = name.lower()
                if lower.endswith("-ixbrl.htm") or lower.endswith("-ixbrl.html"):
                    result[name] = zf.read(name)
    except zipfile.BadZipFile as exc:
        logger.warning("Bad ZIP file: %s", exc)

    return result
