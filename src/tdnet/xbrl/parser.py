"""TDnet XBRL ZIP の解析。"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

from xbrl_core import (
    CalculationLinkbase,
    DefinitionLinkbase,
    PresentationTree,
    ParsedXBRL,
    RawLabel,
    build_line_items,
    merge_ixbrl_results,
    parse_calculation_linkbase,
    parse_definition_linkbase,
    parse_ixbrl_facts,
    parse_label_linkbase,
    parse_presentation_linkbase,
    structure_contexts,
)

from tdnet.models.statements import Statements
from tdnet.models.types import convert_line_item
from tdnet.xbrl.taxonomy import TdnetLabelResolver

logger = logging.getLogger(__name__)

# リンクベースファイルの末尾パターン → 種別キー
_LINKBASE_SUFFIXES: dict[str, str] = {
    "_lab.xml": "lab",
    "-lab.xml": "lab",
    "_lab-en.xml": "lab-en",
    "-lab-en.xml": "lab-en",
    "_def.xml": "def",
    "-def.xml": "def",
    "_cal.xml": "cal",
    "-cal.xml": "cal",
    "_pre.xml": "pre",
    "-pre.xml": "pre",
}


def parse_zip(
    zip_data: bytes,
    *,
    taxonomy_path: str | Path | None = None,
    entity_id: str = "",
) -> Statements:
    """XBRL ZIP を解析して Statements を返す。

    ZIP 内のリンクベース（lab/def/cal/pre）を自動抽出し、
    filer ラベルの注入および definition/calculation/presentation
    リンクベースの解析を行う。

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

    linkbases = _extract_linkbases_from_zip(zip_data)

    # filer ラベルをパース
    filer_labels = _parse_filer_labels(linkbases)

    # iXBRL パース（filer ラベル注入済み）
    stmts = parse_ixbrl_files(
        ixbrl_files,
        taxonomy_path=taxonomy_path,
        entity_id=entity_id,
        filer_labels=filer_labels,
    )

    # リンクベースをパース
    def_lb = _parse_def_linkbase(linkbases)
    cal_lb = _parse_cal_linkbase(linkbases)
    pre_lb = _parse_pre_linkbase(linkbases)

    if def_lb is not None or cal_lb is not None or pre_lb is not None:
        return Statements(
            items=stmts._items,
            entity_id=stmts._entity_id,
            warnings=stmts._warnings,
            definition_linkbase=def_lb,
            calculation_linkbase=cal_lb,
            presentation_linkbase=pre_lb,
        )

    return stmts


def parse_ixbrl_files(
    files: dict[str, bytes],
    *,
    taxonomy_path: str | Path | None = None,
    entity_id: str = "",
    filer_labels: tuple[RawLabel, ...] | None = None,
) -> Statements:
    """複数の iXBRL ファイルを解析して Statements を返す。

    Args:
        files: ファイル名をキー、iXBRL bytes を値とする辞書。
        taxonomy_path: タクソノミのパス。
        entity_id: エンティティ ID。
        filer_labels: ZIP 内ラベルリンクベースからパースした filer ラベル。

    Returns:
        Statements コンテナ。
    """
    resolver = TdnetLabelResolver(taxonomy_path)

    # filer ラベルを注入（build_line_items 前に実行）
    if filer_labels:
        resolver.inject_filer_labels(filer_labels)

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


def _extract_linkbases_from_zip(zip_data: bytes) -> dict[str, bytes]:
    """ZIP 内のリンクベースファイルを抽出する。

    末尾パターンでファイル種別を判定し、種別キーをキーとする辞書を返す。
    同一種別で複数ファイルがある場合は後勝ち。

    Returns:
        ``{"lab": bytes, "lab-en": bytes, "def": bytes, ...}`` 形式の辞書。
    """
    result: dict[str, bytes] = {}

    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                lower = info.filename.lower()
                for suffix, key in _LINKBASE_SUFFIXES.items():
                    if lower.endswith(suffix):
                        result[key] = zf.read(info.filename)
                        break
    except zipfile.BadZipFile:
        pass

    return result


def _parse_filer_labels(linkbases: dict[str, bytes]) -> tuple[RawLabel, ...] | None:
    """リンクベース辞書から filer ラベルをパースする。

    Args:
        linkbases: ``_extract_linkbases_from_zip()`` の戻り値。

    Returns:
        パースされた RawLabel のタプル。ラベルファイルがなければ ``None``。
    """
    all_labels: list[RawLabel] = []

    for key in ("lab", "lab-en"):
        if key not in linkbases:
            continue
        try:
            labels = parse_label_linkbase(
                linkbases[key], source_path=f"zip:{key}"
            )
            all_labels.extend(labels)
        except Exception:
            logger.warning("Failed to parse filer label linkbase: %s", key)

    return tuple(all_labels) if all_labels else None


def _parse_def_linkbase(
    linkbases: dict[str, bytes],
) -> DefinitionLinkbase | None:
    """リンクベース辞書から Definition Linkbase をパースする。"""
    if "def" not in linkbases:
        return None
    try:
        return parse_definition_linkbase(
            linkbases["def"], source_path="zip:def"
        )
    except Exception:
        logger.warning("Failed to parse definition linkbase")
        return None


def _parse_cal_linkbase(
    linkbases: dict[str, bytes],
) -> CalculationLinkbase | None:
    """リンクベース辞書から Calculation Linkbase をパースする。"""
    if "cal" not in linkbases:
        return None
    try:
        return parse_calculation_linkbase(
            linkbases["cal"], source_path="zip:cal"
        )
    except Exception:
        logger.warning("Failed to parse calculation linkbase")
        return None


def _parse_pre_linkbase(
    linkbases: dict[str, bytes],
) -> dict[str, PresentationTree] | None:
    """リンクベース辞書から Presentation Linkbase をパースする。"""
    if "pre" not in linkbases:
        return None
    try:
        return parse_presentation_linkbase(
            linkbases["pre"], source_path="zip:pre"
        )
    except Exception:
        logger.warning("Failed to parse presentation linkbase")
        return None
