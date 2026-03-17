"""Parquet 永続化・復元モジュール。

Filing + Statements を Parquet ファイルに永続化し、
高速なロード・横断分析を実現する。

公開 API:
    - ``export_parquet()``: ドメインオブジェクト → Parquet
    - ``import_parquet()``: Parquet → ドメインオブジェクト
    - ``iter_parquet()``: バッチ単位イテレータ
    - ``adump_to_parquet()``: メモリ効率バッチ永続化（非同期）
    - ``adump_to_parquet_thread_pool()``: ThreadPool 版
    - ``adump_to_parquet_process_pool()``: ProcessPool 版
    - ``DumpResult``: ``adump_to_parquet()`` の実行結果
"""

from __future__ import annotations

import asyncio
import gc
import logging
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from ._deserialize import (
    deserialize_calc_linkbase,
    deserialize_filing,
    deserialize_line_item,
    deserialize_statements,
)
from ._schema import SCHEMAS
from ._serialize import (
    is_text_block,
    serialize_calc_edges,
    serialize_def_parents,
    serialize_filing,
    serialize_line_item,
)

if TYPE_CHECKING:
    from tdnet.filing import Filing
    from tdnet.models.statements import Statements

__all__ = [
    "export_parquet",
    "import_parquet",
    "iter_parquet",
    "adump_to_parquet",
    "adump_to_parquet_thread_pool",
    "adump_to_parquet_process_pool",
    "DumpResult",
]

logger = logging.getLogger(__name__)


def _require_pyarrow() -> tuple[Any, Any]:
    """pyarrow のインポートを試み、失敗時は日本語エラーを返す。"""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        return pa, pq
    except ImportError:
        msg = (
            "pyarrow がインストールされていません。"
            "pip install pyarrow でインストールしてください。"
        )
        raise ImportError(msg) from None


# ---------------------------------------------------------------------------
# _ParquetWriters
# ---------------------------------------------------------------------------


class _ParquetWriters:
    """5テーブルの ParquetWriter をまとめて管理する。

    ドキュメント単位で即書き出しするためのユーティリティ。
    """

    _TABLE_NAMES = (
        "filings", "line_items", "text_blocks",
        "calc_edges", "def_parents",
    )

    def __init__(
        self,
        output_dir: Path,
        prefix: str,
        compression: str,
    ) -> None:
        self._output_dir = output_dir
        self._prefix = prefix
        self._compression: str | None = (
            None if compression == "none" else compression
        )
        self._writers: dict[str, Any] = {}
        self._paths: dict[str, Path] = {}
        self._has_rows: set[str] = set()

    def _get_writer(self, name: str) -> Any:
        """テーブル名に対応する ParquetWriter を返す（遅延生成）。"""
        if name not in self._writers:
            _, pq = _require_pyarrow()
            schema_fn = SCHEMAS[name]
            path = self._output_dir / f"{self._prefix}{name}.parquet"
            self._writers[name] = pq.ParquetWriter(
                path, schema_fn(), compression=self._compression,
            )
            self._paths[name] = path
        return self._writers[name]

    def write_rows(self, name: str, rows: list[dict[str, Any]]) -> None:
        """dict 行リストを row group として即書き出しする。

        Args:
            name: テーブル名。
            rows: 書き出す行リスト。空リストの場合は何もしない。
        """
        if not rows:
            return
        pa, _ = _require_pyarrow()
        schema_fn = SCHEMAS[name]
        writer = self._get_writer(name)
        table = pa.Table.from_pylist(rows, schema=schema_fn())
        writer.write_table(table)
        self._has_rows.add(name)

    def close(self) -> dict[str, Path]:
        """全 Writer を閉じ、行が書かれたテーブルのパスを返す。"""
        for writer in self._writers.values():
            writer.close()
        return {
            name: self._paths[name]
            for name in self._has_rows
            if name in self._paths
        }


# ---------------------------------------------------------------------------
# export_parquet
# ---------------------------------------------------------------------------


def export_parquet(
    data: Sequence[tuple[Filing, Statements | None]],
    output_dir: str | Path,
    *,
    prefix: str = "",
    compression: str = "zstd",
) -> dict[str, Path]:
    """Filing + Statements を Parquet ファイルにエクスポートする。

    書類単位で row group を作成するため、``iter_parquet()`` による
    doc_id 単位の効率的な読み込みと互換性がある。

    Args:
        data: ``(Filing, Statements | None)`` ペアのシーケンス。
        output_dir: 出力先ディレクトリ。
        prefix: ファイル名プレフィックス（例: ``"2026-01-01_"``）。
        compression: 圧縮アルゴリズム。デフォルト ``"zstd"``。

    Returns:
        テーブル名 → 出力パスの辞書。
    """
    _require_pyarrow()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    writers = _ParquetWriters(output_dir, prefix, compression)
    try:
        for filing, stmts in data:
            doc_id = filing.doc_id
            writers.write_rows(
                "filings", [serialize_filing(filing, stmts is not None)],
            )

            if stmts is None:
                continue

            # LineItems — TextBlock を分離
            li_rows: list[dict[str, Any]] = []
            tb_rows: list[dict[str, Any]] = []
            for item in stmts:
                row = serialize_line_item(item, doc_id)
                if is_text_block(item.local_name):
                    tb_rows.append(row)
                else:
                    li_rows.append(row)
            writers.write_rows("line_items", li_rows)
            writers.write_rows("text_blocks", tb_rows)

            # CalculationLinkbase
            calc = stmts._calculation_linkbase
            if calc is not None:
                writers.write_rows(
                    "calc_edges",
                    serialize_calc_edges(calc, doc_id),
                )

            # DefinitionLinkbase → parent_index
            defn = stmts._definition_linkbase
            if defn is not None:
                writers.write_rows(
                    "def_parents",
                    serialize_def_parents(defn, doc_id),
                )
    finally:
        result = writers.close()

    return result


# ---------------------------------------------------------------------------
# import_parquet
# ---------------------------------------------------------------------------


def _read_auxiliary_tables(
    input_dir: Path,
    prefix: str,
    doc_filter: list[tuple[str, str, list[str]]] | None,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, dict[str, str]],
]:
    """補助テーブル（calc_edges, def_parents）を一括読み込みする。

    Args:
        input_dir: 入力ディレクトリ。
        prefix: ファイル名プレフィックス。
        doc_filter: doc_id フィルタ。

    Returns:
        ``(calc_rows_by_doc, def_parent_index_by_doc)``。
    """
    _, pq = _require_pyarrow()

    calc_rows_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    calc_path = input_dir / f"{prefix}calc_edges.parquet"
    if calc_path.exists():
        calc_table = pq.read_table(calc_path, filters=doc_filter)
        for row in calc_table.to_pylist():
            calc_rows_by_doc[row["doc_id"]].append(row)

    def_parent_index_by_doc: dict[str, dict[str, str]] = defaultdict(dict)
    def_path = input_dir / f"{prefix}def_parents.parquet"
    if def_path.exists():
        def_table = pq.read_table(def_path, filters=doc_filter)
        for row in def_table.to_pylist():
            def_parent_index_by_doc[row["doc_id"]][
                row["child_concept"]
            ] = row["parent_standard_concept"]

    return dict(calc_rows_by_doc), dict(def_parent_index_by_doc)


def _assemble_statements(
    doc_id: str,
    items: list[Any],
    calc_rows_by_doc: dict[str, list[dict[str, Any]]],
    def_parent_index_by_doc: dict[str, dict[str, str]],
) -> Statements:
    """1 書類分の Statements を組み立てる。

    Args:
        doc_id: 書類 ID。
        items: 復元済み LineItem リスト。
        calc_rows_by_doc: CalculationArc 行マッピング。
        def_parent_index_by_doc: DefinitionParentIndex マッピング。

    Returns:
        復元済み Statements。
    """
    calc_rows = calc_rows_by_doc.get(doc_id)
    calc_lb = deserialize_calc_linkbase(calc_rows) if calc_rows else None
    def_pi = def_parent_index_by_doc.get(doc_id) or None
    entity_id = items[0].entity_id if items else ""

    return deserialize_statements(
        tuple(items),
        entity_id=entity_id,
        calculation_linkbase=calc_lb,
        definition_parent_index=def_pi,
    )


def import_parquet(
    input_dir: str | Path,
    *,
    prefix: str = "",
    include_text_blocks: bool = True,
    doc_ids: Sequence[str] | None = None,
    concepts: Sequence[str] | None = None,
) -> list[tuple[Filing, Statements | None]]:
    """Parquet ファイルから Filing + Statements を復元する。

    Args:
        input_dir: 入力ディレクトリ。
        prefix: ファイル名プレフィックス。
        include_text_blocks: ``True``（デフォルト）なら ``text_blocks.parquet``
            も読み込み ``line_items`` と統合する。
        doc_ids: 読み込む doc_id のリスト。``None`` なら全件読み込み。
        concepts: 読み込む科目の ``local_name`` リスト。``None`` なら全科目。

    Returns:
        ``(Filing, Statements | None)`` ペアのリスト。
    """
    _, pq = _require_pyarrow()
    input_dir = Path(input_dir)

    # フィルタ構築
    doc_filter: list[tuple[str, str, list[str]]] | None = (
        [("doc_id", "in", list(doc_ids))] if doc_ids is not None else None
    )
    li_conditions: list[tuple[str, str, list[str]]] = []
    if doc_ids is not None:
        li_conditions.append(("doc_id", "in", list(doc_ids)))
    if concepts is not None:
        li_conditions.append(("local_name", "in", list(concepts)))
    li_filter = li_conditions or None

    # 1. filings.parquet（必須）
    filings_path = input_dir / f"{prefix}filings.parquet"
    if not filings_path.exists():
        return []

    filings_table = pq.read_table(filings_path, filters=doc_filter)
    filing_rows = filings_table.to_pylist()

    # 2. line_items.parquet（オプション）
    items_by_doc: dict[str, list[Any]] = defaultdict(list)
    li_path = input_dir / f"{prefix}line_items.parquet"
    if li_path.exists():
        li_table = pq.read_table(li_path, filters=li_filter)
        for row in li_table.to_pylist():
            items_by_doc[row["doc_id"]].append(deserialize_line_item(row))

    # 2b. text_blocks.parquet（オプション）
    if include_text_blocks:
        tb_path = input_dir / f"{prefix}text_blocks.parquet"
        if tb_path.exists():
            tb_table = pq.read_table(tb_path, filters=li_filter)
            for row in tb_table.to_pylist():
                items_by_doc[row["doc_id"]].append(
                    deserialize_line_item(row),
                )

    # 3. 補助テーブル
    calc_rows_by_doc, def_parent_index_by_doc = _read_auxiliary_tables(
        input_dir, prefix, doc_filter,
    )

    # 組み立て
    result: list[tuple[Filing, Statements | None]] = []
    for frow in filing_rows:
        filing = deserialize_filing(frow)
        doc_id = frow["doc_id"]

        if not frow.get("has_xbrl", False):
            result.append((filing, None))
            continue

        items = items_by_doc.get(doc_id)
        if items is None:
            result.append((filing, None))
            continue

        stmts = _assemble_statements(
            doc_id, items, calc_rows_by_doc, def_parent_index_by_doc,
        )
        result.append((filing, stmts))

    return result


# ---------------------------------------------------------------------------
# _build_rg_mapping / iter_parquet
# ---------------------------------------------------------------------------


def _build_rg_mapping(pf: Any) -> dict[str, list[int]]:
    """ParquetFile から doc_id → row_group_indices マッピングを構築する。

    1 書類 = 1 row group の不変条件を前提とする。
    row group 統計情報（min/max）から doc_id を取得し、データ I/O ゼロで
    マッピングを構築する。統計が利用できない場合はフォールバック。

    Args:
        pf: ``pq.ParquetFile`` インスタンス。

    Returns:
        ``{doc_id: [row_group_index, ...]}`` マッピング。
    """
    num_rgs = pf.metadata.num_row_groups
    if num_rgs == 0:
        return {}

    doc_id_idx = pf.schema_arrow.get_field_index("doc_id")
    rg_map: dict[str, list[int]] = defaultdict(list)

    # 統計ベース（データ I/O ゼロ）
    for i in range(num_rgs):
        stats = pf.metadata.row_group(i).column(doc_id_idx).statistics
        if stats is None or not stats.has_min_max:
            break
        rg_map[stats.min].append(i)
    else:
        return dict(rg_map)

    # フォールバック: doc_id カラムの先頭行を読む
    rg_map.clear()
    doc_id_col = pf.read(columns=["doc_id"]).column("doc_id")
    offset = 0
    for i in range(num_rgs):
        n = pf.metadata.row_group(i).num_rows
        did = doc_id_col[offset].as_py()
        rg_map[did].append(i)
        offset += n
    return dict(rg_map)


class _LazyAuxiliaryTables:
    """補助テーブルを ParquetFile として保持し、バッチ単位で read_row_groups する。

    ``iter_parquet()`` 用。全件を展開せず、バッチごとに該当分だけ I/O する。
    """

    def __init__(
        self,
        input_dir: Path,
        prefix: str,
    ) -> None:
        _, pq = _require_pyarrow()
        self._calc_pf, self._calc_rg = self._open(
            input_dir / f"{prefix}calc_edges.parquet", pq,
        )
        self._def_pf, self._def_rg = self._open(
            input_dir / f"{prefix}def_parents.parquet", pq,
        )

    @staticmethod
    def _open(
        path: Path, pq: Any,
    ) -> tuple[Any | None, dict[str, list[int]]]:
        """Parquet ファイルを開き RG マッピングを構築する。"""
        if not path.exists():
            return None, {}
        pf = pq.ParquetFile(path)
        rg = _build_rg_mapping(pf)
        return pf, rg

    @staticmethod
    def _collect_rg_indices(
        rg_map: dict[str, list[int]],
        doc_ids: list[str],
    ) -> list[int]:
        """doc_id リストから RG インデックスを収集する。"""
        indices: list[int] = []
        for did in doc_ids:
            indices.extend(rg_map.get(did, []))
        indices.sort()
        return indices

    def filter_batch(
        self,
        doc_ids: list[str],
    ) -> tuple[
        dict[str, list[dict[str, Any]]],
        dict[str, dict[str, str]],
    ]:
        """バッチ内の doc_id に対応する補助データを返す。

        Args:
            doc_ids: バッチ内の doc_id リスト。

        Returns:
            ``(calc_rows_by_doc, def_parent_index_by_doc)``。
        """
        # calc_edges
        calc_rows_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        if self._calc_pf is not None:
            rg_indices = self._collect_rg_indices(self._calc_rg, doc_ids)
            if rg_indices:
                for row in self._calc_pf.read_row_groups(
                    rg_indices,
                ).to_pylist():
                    calc_rows_by_doc[row["doc_id"]].append(row)

        # def_parents
        def_parent_index_by_doc: dict[str, dict[str, str]] = defaultdict(dict)
        if self._def_pf is not None:
            rg_indices = self._collect_rg_indices(self._def_rg, doc_ids)
            if rg_indices:
                for row in self._def_pf.read_row_groups(
                    rg_indices,
                ).to_pylist():
                    def_parent_index_by_doc[row["doc_id"]][
                        row["child_concept"]
                    ] = row["parent_standard_concept"]

        return dict(calc_rows_by_doc), dict(def_parent_index_by_doc)


def _read_row_groups_filtered(
    pf: Any,
    rg_map: dict[str, list[int]],
    batch_doc_ids: list[str],
    concepts_arr: Any | None,
) -> dict[str, list[Any]]:
    """バッチ内の doc_id に対応する row group を読み込み分類する。"""
    rg_indices: list[int] = []
    for did in batch_doc_ids:
        rg_indices.extend(rg_map.get(did, []))
    if not rg_indices:
        return {}

    rg_indices.sort()
    table = pf.read_row_groups(rg_indices)

    if concepts_arr is not None:
        import pyarrow.compute as pc

        mask = pc.is_in(
            table.column("local_name"), value_set=concepts_arr,
        )
        table = table.filter(mask)

    items_by_doc: dict[str, list[Any]] = defaultdict(list)
    for row in table.to_pylist():
        items_by_doc[row["doc_id"]].append(deserialize_line_item(row))
    return items_by_doc


def iter_parquet(
    input_dir: str | Path,
    *,
    prefix: str = "",
    include_text_blocks: bool = False,
    batch_size: int = 100,
    doc_ids: Sequence[str] | None = None,
    concepts: Sequence[str] | None = None,
) -> Iterator[tuple[Filing, Statements | None]]:
    """Parquet ファイルから Filing + Statements をイテレータで返す。

    ``import_parquet()`` と異なり、line_items / text_blocks を
    バッチ単位で読み込むため、メモリ使用量が件数に依存しない。

    Args:
        input_dir: 入力ディレクトリ。
        prefix: ファイル名プレフィックス。
        include_text_blocks: ``True`` なら ``text_blocks.parquet``
            も読み込む。デフォルト ``False``。
        batch_size: 一度に読み込む書類数。デフォルト ``100``。
        doc_ids: 読み込む doc_id のリスト。``None`` なら全件。
        concepts: 読み込む科目の ``local_name`` リスト。``None`` なら全科目。

    Yields:
        ``(Filing, Statements | None)`` ペア。
    """
    pa, pq = _require_pyarrow()
    input_dir = Path(input_dir)

    # フィルタ構築
    doc_filter: list[tuple[str, str, list[str]]] | None = (
        [("doc_id", "in", list(doc_ids))] if doc_ids is not None else None
    )

    # 1. filings.parquet（必須）
    filings_path = input_dir / f"{prefix}filings.parquet"
    if not filings_path.exists():
        return

    filings_table = pq.read_table(filings_path, filters=doc_filter)
    filing_rows = filings_table.to_pylist()

    # 2. 補助テーブル（ParquetFile として保持）
    aux = _LazyAuxiliaryTables(input_dir, prefix)

    # 3. line_items / text_blocks — ParquetFile を1回だけ開く
    li_path = input_dir / f"{prefix}line_items.parquet"
    tb_path = input_dir / f"{prefix}text_blocks.parquet"
    has_li = li_path.exists()
    has_tb = include_text_blocks and tb_path.exists()

    li_pf = pq.ParquetFile(li_path) if has_li else None
    tb_pf = pq.ParquetFile(tb_path) if has_tb else None
    li_rg_map = _build_rg_mapping(li_pf) if li_pf is not None else {}
    tb_rg_map = _build_rg_mapping(tb_pf) if tb_pf is not None else {}

    concepts_arr = pa.array(list(concepts)) if concepts is not None else None

    for batch_start in range(0, len(filing_rows), batch_size):
        batch_frows = filing_rows[batch_start: batch_start + batch_size]
        batch_doc_ids = [r["doc_id"] for r in batch_frows]

        calc_rows_by_doc, def_parent_index_by_doc = aux.filter_batch(
            batch_doc_ids,
        )

        items_by_doc: dict[str, list[Any]] = defaultdict(list)

        if li_pf is not None:
            for did, items in _read_row_groups_filtered(
                li_pf, li_rg_map, batch_doc_ids, concepts_arr,
            ).items():
                items_by_doc[did].extend(items)

        if tb_pf is not None:
            for did, items in _read_row_groups_filtered(
                tb_pf, tb_rg_map, batch_doc_ids, concepts_arr,
            ).items():
                items_by_doc[did].extend(items)

        for frow in batch_frows:
            filing = deserialize_filing(frow)
            doc_id = frow["doc_id"]

            if not frow.get("has_xbrl", False):
                yield (filing, None)
                continue

            items = items_by_doc.get(doc_id)
            if items is None:
                yield (filing, None)
                continue

            stmts = _assemble_statements(
                doc_id, items, calc_rows_by_doc, def_parent_index_by_doc,
            )
            yield (filing, stmts)


# ---------------------------------------------------------------------------
# DumpResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DumpResult:
    """``adump_to_parquet()`` の実行結果。

    Attributes:
        paths: テーブル名 → 出力パスの辞書。
        total_filings: 書類一覧の総件数。
        xbrl_count: XBRL フラグが True の書類数。
        xbrl_ok: XBRL パースに成功した書類数。
        errors: XBRL パースエラー件数。
    """

    paths: dict[str, Path]
    total_filings: int
    xbrl_count: int
    xbrl_ok: int
    errors: int


# ---------------------------------------------------------------------------
# adump_to_parquet
# ---------------------------------------------------------------------------


async def adump_to_parquet(
    target_date: str | None = None,
    *,
    code: str | int | None = None,
    has_xbrl: bool = True,
    limit: int = 300,
    source: str = "yanoshin",
    start: str | None = None,
    end: str | None = None,
    output_dir: str | Path = ".",
    prefix: str = "",
    compression: str = "zstd",
    concurrency: int = 8,
    taxonomy_path: str | Path | None = None,
) -> DumpResult:
    """メモリ効率的な非同期バッチ Parquet 永続化。

    ``documents()`` で書類一覧を取得し、XBRL をドキュメント単位で
    ダウンロード → パース → Parquet 書き出し → 即解放する。

    Args:
        target_date: 日付文字列 (``YYYYMMDD`` or ``YYYY-MM-DD``)。
        code: 証券コードで絞り込み。
        has_xbrl: ``True`` で XBRL 付きのみ。
        limit: 最大取得件数。
        source: データソース。
        start: 範囲指定の開始日。
        end: 範囲指定の終了日。
        output_dir: 出力先ディレクトリ。
        prefix: ファイル名プレフィックス。
        compression: 圧縮アルゴリズム。デフォルト ``"zstd"``。
        concurrency: 同時パース並行数。デフォルト ``8``。
        taxonomy_path: TDnet タクソノミのパス。

    Returns:
        ``DumpResult``: パス・カウントを含む実行結果。
    """
    _require_pyarrow()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 書類一覧を取得
    if start is not None and end is not None:
        from tdnet.api import list_by_range
        from tdnet.filing import Filing as _Filing

        raw_items = list_by_range(start, end, has_xbrl=has_xbrl, limit=10000)
        filings = [_Filing.from_yanoshin(item) for item in raw_items]
    else:
        from tdnet import documents

        filings = documents(
            target_date,
            code=code,
            has_xbrl=has_xbrl,
            limit=limit,
            source=source,
        )

    total_filings = len(filings)

    xbrl_filings = [f for f in filings if f.has_xbrl]
    non_xbrl_filings = [f for f in filings if not f.has_xbrl]
    xbrl_count = len(xbrl_filings)

    # 2. Writer を準備
    writers = _ParquetWriters(output_path, prefix, compression)

    try:
        # 3. non-XBRL → 即書き出し
        if non_xbrl_filings:
            writers.write_rows(
                "filings",
                [serialize_filing(f, False) for f in non_xbrl_filings],
            )

        # 4. XBRL をドキュメント単位で処理
        sem = asyncio.Semaphore(concurrency)
        xbrl_ok = 0
        errors = 0
        processed = 0

        async def _process_xbrl(filing: Filing) -> None:
            nonlocal xbrl_ok, errors, processed
            async with sem:
                doc_id = filing.doc_id
                stmts = None
                try:
                    stmts = await filing.axbrl(taxonomy_path=taxonomy_path)
                except Exception:
                    logger.warning(
                        "XBRL パース失敗: %s", filing.doc_id, exc_info=True,
                    )
                    errors += 1

            writers.write_rows(
                "filings", [serialize_filing(filing, stmts is not None)],
            )

            if stmts is not None:
                li_rows: list[dict[str, Any]] = []
                tb_rows: list[dict[str, Any]] = []
                for item in stmts:
                    row = serialize_line_item(item, doc_id)
                    if is_text_block(item.local_name):
                        tb_rows.append(row)
                    else:
                        li_rows.append(row)
                writers.write_rows("line_items", li_rows)
                writers.write_rows("text_blocks", tb_rows)

                calc = stmts._calculation_linkbase
                if calc is not None:
                    writers.write_rows(
                        "calc_edges",
                        serialize_calc_edges(calc, doc_id),
                    )

                defn = stmts._definition_linkbase
                if defn is not None:
                    writers.write_rows(
                        "def_parents",
                        serialize_def_parents(defn, doc_id),
                    )

                del stmts
                xbrl_ok += 1

            processed += 1
            if processed % 20 == 0:
                gc.collect()

        await asyncio.gather(*[_process_xbrl(f) for f in xbrl_filings])

    finally:
        result_paths = writers.close()

    return DumpResult(
        paths=result_paths,
        total_filings=total_filings,
        xbrl_count=xbrl_count,
        xbrl_ok=xbrl_ok,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# adump_to_parquet_thread_pool
# ---------------------------------------------------------------------------


async def adump_to_parquet_thread_pool(
    target_date: str | None = None,
    *,
    code: str | int | None = None,
    has_xbrl: bool = True,
    limit: int = 300,
    source: str = "yanoshin",
    start: str | None = None,
    end: str | None = None,
    output_dir: str | Path = ".",
    prefix: str = "",
    compression: str = "zstd",
    concurrency: int = 8,
    max_workers: int = 4,
    taxonomy_path: str | Path | None = None,
) -> DumpResult:
    """ThreadPoolExecutor で XBRL パースをオフロードするバッチ Parquet 永続化。

    DL はイベントループ上、パースは ThreadPool、書き出しはメインスレッド。

    Args:
        target_date: 日付文字列。
        code: 証券コードで絞り込み。
        has_xbrl: XBRL 付きのみ。
        limit: 最大取得件数。
        source: データソース。
        start: 範囲指定の開始日。
        end: 範囲指定の終了日。
        output_dir: 出力先ディレクトリ。
        prefix: ファイル名プレフィックス。
        compression: 圧縮アルゴリズム。
        concurrency: 同時ダウンロード並行数。
        max_workers: ThreadPoolExecutor のワーカー数。
        taxonomy_path: TDnet タクソノミのパス。

    Returns:
        ``DumpResult``。
    """
    from concurrent.futures import ThreadPoolExecutor

    _require_pyarrow()

    from tdnet.xbrl.parser import parse_zip

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 書類一覧を取得
    if start is not None and end is not None:
        from tdnet.api import list_by_range
        from tdnet.filing import Filing as _Filing

        raw_items = list_by_range(start, end, has_xbrl=has_xbrl, limit=10000)
        filings = [_Filing.from_yanoshin(item) for item in raw_items]
    else:
        from tdnet import documents

        filings = documents(
            target_date,
            code=code,
            has_xbrl=has_xbrl,
            limit=limit,
            source=source,
        )

    total_filings = len(filings)
    xbrl_filings = [f for f in filings if f.has_xbrl]
    non_xbrl_filings = [f for f in filings if not f.has_xbrl]
    xbrl_count = len(xbrl_filings)

    writers = _ParquetWriters(output_path, prefix, compression)
    loop = asyncio.get_running_loop()

    try:
        if non_xbrl_filings:
            writers.write_rows(
                "filings",
                [serialize_filing(f, False) for f in non_xbrl_filings],
            )

        sem = asyncio.Semaphore(concurrency)
        xbrl_ok = 0
        errors = 0
        processed = 0

        async def _process_xbrl(
            filing: Filing, pool: ThreadPoolExecutor,
        ) -> None:
            nonlocal xbrl_ok, errors, processed
            doc_id = filing.doc_id
            stmts = None

            try:
                async with sem:
                    dl_result = await filing.afetch_xbrl()
                    xbrl_data = dl_result.data

                from tdnet._config import get_config
                tp = taxonomy_path
                if tp is None:
                    tp = get_config().taxonomy_path

                stmts = await loop.run_in_executor(
                    pool,
                    lambda: parse_zip(
                        xbrl_data,
                        taxonomy_path=tp,
                        entity_id=filing.company_code,
                    ),
                )
            except Exception:
                logger.warning(
                    "XBRL パース失敗: %s", filing.doc_id, exc_info=True,
                )
                errors += 1

            writers.write_rows(
                "filings", [serialize_filing(filing, stmts is not None)],
            )

            if stmts is not None:
                li_rows: list[dict[str, Any]] = []
                tb_rows: list[dict[str, Any]] = []
                for item in stmts:
                    row = serialize_line_item(item, doc_id)
                    if is_text_block(item.local_name):
                        tb_rows.append(row)
                    else:
                        li_rows.append(row)
                writers.write_rows("line_items", li_rows)
                writers.write_rows("text_blocks", tb_rows)

                calc = stmts._calculation_linkbase
                if calc is not None:
                    writers.write_rows(
                        "calc_edges",
                        serialize_calc_edges(calc, doc_id),
                    )

                defn = stmts._definition_linkbase
                if defn is not None:
                    writers.write_rows(
                        "def_parents",
                        serialize_def_parents(defn, doc_id),
                    )

                del stmts
                xbrl_ok += 1

            processed += 1
            if processed % 20 == 0:
                gc.collect()

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            await asyncio.gather(
                *[_process_xbrl(f, pool) for f in xbrl_filings],
            )

    finally:
        result_paths = writers.close()

    return DumpResult(
        paths=result_paths,
        total_filings=total_filings,
        xbrl_count=xbrl_count,
        xbrl_ok=xbrl_ok,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# adump_to_parquet_process_pool
# ---------------------------------------------------------------------------


def _worker_parse_and_serialize(
    xbrl_data: bytes,
    company_code: str,
    doc_id: str,
    taxonomy_path: str | Path | None,
) -> dict[str, Any]:
    """ワーカープロセス内でパース→シリアライズを完結させる。

    Returns:
        ``{"li_rows": [...], "tb_rows": [...],
          "calc_rows": [...], "def_rows": [...]}``
    """
    from tdnet.xbrl.parser import parse_zip
    from tdnet._config import get_config

    tp = taxonomy_path
    if tp is None:
        tp = get_config().taxonomy_path

    stmts = parse_zip(
        xbrl_data,
        taxonomy_path=tp,
        entity_id=company_code,
    )

    li_rows: list[dict[str, Any]] = []
    tb_rows: list[dict[str, Any]] = []
    for item in stmts:
        row = serialize_line_item(item, doc_id)
        if is_text_block(item.local_name):
            tb_rows.append(row)
        else:
            li_rows.append(row)

    calc_rows: list[dict[str, Any]] = []
    calc = stmts._calculation_linkbase
    if calc is not None:
        calc_rows = serialize_calc_edges(calc, doc_id)

    def_rows: list[dict[str, Any]] = []
    defn = stmts._definition_linkbase
    if defn is not None:
        def_rows = serialize_def_parents(defn, doc_id)

    return {
        "li_rows": li_rows,
        "tb_rows": tb_rows,
        "calc_rows": calc_rows,
        "def_rows": def_rows,
    }


async def adump_to_parquet_process_pool(
    target_date: str | None = None,
    *,
    code: str | int | None = None,
    has_xbrl: bool = True,
    limit: int = 300,
    source: str = "yanoshin",
    start: str | None = None,
    end: str | None = None,
    output_dir: str | Path = ".",
    prefix: str = "",
    compression: str = "zstd",
    concurrency: int = 8,
    max_workers: int = 4,
    taxonomy_path: str | Path | None = None,
) -> DumpResult:
    """ProcessPoolExecutor で GIL 回避するバッチ Parquet 永続化。

    DL はイベントループ上、パース+シリアライズはワーカープロセス、
    Parquet 書き出しはメインプロセスで行う。

    Args:
        target_date: 日付文字列。
        code: 証券コードで絞り込み。
        has_xbrl: XBRL 付きのみ。
        limit: 最大取得件数。
        source: データソース。
        start: 範囲指定の開始日。
        end: 範囲指定の終了日。
        output_dir: 出力先ディレクトリ。
        prefix: ファイル名プレフィックス。
        compression: 圧縮アルゴリズム。
        concurrency: 同時ダウンロード並行数。
        max_workers: ProcessPoolExecutor のワーカー数。
        taxonomy_path: TDnet タクソノミのパス。

    Returns:
        ``DumpResult``。
    """
    from concurrent.futures import ProcessPoolExecutor

    _require_pyarrow()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 書類一覧を取得
    if start is not None and end is not None:
        from tdnet.api import list_by_range
        from tdnet.filing import Filing as _Filing

        raw_items = list_by_range(start, end, has_xbrl=has_xbrl, limit=10000)
        filings = [_Filing.from_yanoshin(item) for item in raw_items]
    else:
        from tdnet import documents

        filings = documents(
            target_date,
            code=code,
            has_xbrl=has_xbrl,
            limit=limit,
            source=source,
        )

    total_filings = len(filings)
    xbrl_filings = [f for f in filings if f.has_xbrl]
    non_xbrl_filings = [f for f in filings if not f.has_xbrl]
    xbrl_count = len(xbrl_filings)

    writers = _ParquetWriters(output_path, prefix, compression)
    loop = asyncio.get_running_loop()

    try:
        if non_xbrl_filings:
            writers.write_rows(
                "filings",
                [serialize_filing(f, False) for f in non_xbrl_filings],
            )

        dl_sem = asyncio.Semaphore(concurrency)
        parse_sem = asyncio.Semaphore(max_workers * 2)
        xbrl_ok = 0
        errors = 0
        processed = 0

        async def _process_xbrl(
            filing: Filing, pool: ProcessPoolExecutor,
        ) -> None:
            nonlocal xbrl_ok, errors, processed
            doc_id = filing.doc_id

            try:
                # parse_sem を外側に → DL 開始前にゲート → メモリ滞留を制限
                async with parse_sem:
                    async with dl_sem:
                        dl_result = await filing.afetch_xbrl()
                        xbrl_data = dl_result.data

                    # パース + シリアライズ（ProcessPool へオフロード）
                    result = await loop.run_in_executor(
                        pool,
                        _worker_parse_and_serialize,
                        xbrl_data,
                        filing.company_code,
                        doc_id,
                        taxonomy_path,
                    )

                writers.write_rows(
                    "filings", [serialize_filing(filing, True)],
                )
                writers.write_rows("line_items", result["li_rows"])
                writers.write_rows("text_blocks", result["tb_rows"])
                writers.write_rows("calc_edges", result["calc_rows"])
                writers.write_rows("def_parents", result["def_rows"])
                del result
                xbrl_ok += 1

            except Exception:
                logger.warning(
                    "XBRL パース失敗: %s", filing.doc_id, exc_info=True,
                )
                writers.write_rows(
                    "filings", [serialize_filing(filing, False)],
                )
                errors += 1

            processed += 1
            if processed % 20 == 0:
                gc.collect()

        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            await asyncio.gather(
                *[_process_xbrl(f, pool) for f in xbrl_filings],
            )

    finally:
        result_paths = writers.close()

    return DumpResult(
        paths=result_paths,
        total_filings=total_filings,
        xbrl_count=xbrl_count,
        xbrl_ok=xbrl_ok,
        errors=errors,
    )
