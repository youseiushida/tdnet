"""Parquet 永続化のベンチマーク。

export → import / iter_parquet の速度・メモリを計測する。

使い方:
    uv run python tools/bench_parquet.py
    uv run python tools/bench_parquet.py --docs 500 --items 200
"""

from __future__ import annotations

import argparse
import gc
import shutil
import sys
import time
import tracemalloc
from decimal import Decimal
from pathlib import Path
from tempfile import mkdtemp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from xbrl_core import CalculationArc, CalculationLinkbase, CalculationTree

from tdnet.extension import export_parquet, import_parquet, iter_parquet
from tdnet.filing import Filing
from tdnet.models.statements import Statements
from helpers import make_item, make_consolidated_dim, make_current_dim


def _make_filing(idx: int) -> Filing:
    """ベンチ用 Filing を生成する。"""
    code = f"{idx:05d}"
    return Filing(
        pubdate=f"2025-03-{(idx % 28) + 1:02d} 15:00",
        company_code=code,
        company_name=f"ベンチ企業{idx}",
        title="決算短信",
        document_url=f"https://example.com/tdnet1401202503{(idx % 28) + 1:02d}{code}0.pdf",
        xbrl_url=f"https://example.com/tdnet1401202503{(idx % 28) + 1:02d}{code}0.zip",
        markets_string="東証",
    )


def _make_calc_linkbase() -> CalculationLinkbase:
    """ベンチ用 CalculationLinkbase を生成する。"""
    role = "http://example.com/role/PL"
    arcs = tuple(
        CalculationArc(
            parent="GrossProfit",
            child=f"Child{i}",
            parent_href=f"x.xsd#GrossProfit",
            child_href=f"x.xsd#Child{i}",
            weight=1,
            order=float(i),
            role_uri=role,
        )
        for i in range(5)
    )
    tree = CalculationTree(role_uri=role, arcs=arcs, roots=("GrossProfit",))
    return CalculationLinkbase(source_path=None, trees={role: tree})


def _make_data(
    n_docs: int,
    n_items: int,
    with_text_blocks: bool = True,
    with_calc: bool = True,
) -> list[tuple[Filing, Statements | None]]:
    """ベンチ用データを生成する。"""
    calc = _make_calc_linkbase() if with_calc else None
    dims = (make_consolidated_dim(True), make_current_dim())
    data: list[tuple[Filing, Statements | None]] = []

    for i in range(n_docs):
        filing = _make_filing(i)
        items: list = []
        for j in range(n_items):
            items.append(
                make_item(
                    f"Concept{j}",
                    Decimal(str(j * 1000 + i)),
                    entity_id=filing.company_code,
                    dimensions=dims,
                    label_ja=f"科目{j}",
                    label_en=f"Concept{j}",
                    order=j,
                )
            )
        if with_text_blocks:
            for j in range(3):
                items.append(
                    make_item(
                        f"Notes{j}TextBlock",
                        f"テキスト注記{j}の内容" * 10,
                        entity_id=filing.company_code,
                        unit_ref=None,
                        decimals=None,
                        order=n_items + j,
                    )
                )
        stmts = Statements(
            items=tuple(items),
            entity_id=filing.company_code,
            calculation_linkbase=calc,
        )
        data.append((filing, stmts))

    return data


def _fmt(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    return f"{seconds:.2f}s"


def _fmt_mb(b: float) -> str:
    return f"{b / (1024 * 1024):.1f}MB"


def _run_bench(n_docs: int, n_items: int) -> None:
    tmp = mkdtemp(prefix="bench_parquet_")
    tmp_path = Path(tmp)

    try:
        print(f"\n{'=' * 60}")
        print(f"ベンチマーク: {n_docs} 書類 × {n_items} items/doc")
        print(f"  (TextBlock 3/doc, calc_edges 5arcs/doc)")
        total_rows = n_docs * (n_items + 3)
        print(f"  合計行数: {total_rows:,}")
        print(f"{'=' * 60}")

        # --- データ生成 ---
        gc.collect()
        t0 = time.perf_counter()
        data = _make_data(n_docs, n_items)
        t_gen = time.perf_counter() - t0
        print(f"\nデータ生成: {_fmt(t_gen)}")

        # --- export_parquet ---
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        paths = export_parquet(data, tmp_path)
        t_export = time.perf_counter() - t0
        _, peak_export = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        total_size = sum(p.stat().st_size for p in paths.values())
        print(f"\nexport_parquet:")
        print(f"  時間: {_fmt(t_export)}")
        print(f"  メモリ peak: {_fmt_mb(peak_export)}")
        print(f"  ファイル数: {len(paths)}")
        print(f"  合計サイズ: {_fmt_mb(total_size)}")
        for name, p in sorted(paths.items()):
            sz = p.stat().st_size
            print(f"    {name}: {_fmt_mb(sz)}")

        # --- import_parquet ---
        del data
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        result = import_parquet(tmp_path)
        t_import = time.perf_counter() - t0
        _, peak_import = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        n_restored = sum(1 for _, s in result if s is not None)
        n_items_total = sum(len(s) for _, s in result if s is not None)
        print(f"\nimport_parquet:")
        print(f"  時間: {_fmt(t_import)}")
        print(f"  メモリ peak: {_fmt_mb(peak_import)}")
        print(f"  復元書類: {n_restored}")
        print(f"  復元アイテム: {n_items_total:,}")

        # --- import_parquet (doc_ids フィルタ) ---
        if n_docs >= 10:
            target_ids = [result[i][0].doc_id for i in range(0, n_docs, n_docs // 10)]
            del result
            gc.collect()
            tracemalloc.start()
            t0 = time.perf_counter()
            filtered = import_parquet(tmp_path, doc_ids=target_ids)
            t_filtered = time.perf_counter() - t0
            _, peak_filtered = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(f"\nimport_parquet (doc_ids={len(target_ids)}):")
            print(f"  時間: {_fmt(t_filtered)}")
            print(f"  メモリ peak: {_fmt_mb(peak_filtered)}")
            print(f"  復元書類: {len(filtered)}")
            del filtered
        else:
            del result

        # --- iter_parquet ---
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        count = 0
        item_count = 0
        for filing, stmts in iter_parquet(tmp_path, batch_size=50, include_text_blocks=True):
            count += 1
            if stmts is not None:
                item_count += len(stmts)
        t_iter = time.perf_counter() - t0
        _, peak_iter = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"\niter_parquet (batch_size=50):")
        print(f"  時間: {_fmt(t_iter)}")
        print(f"  メモリ peak: {_fmt_mb(peak_iter)}")
        print(f"  yield 回数: {count}")
        print(f"  アイテム数: {item_count:,}")

        # --- iter_parquet (exclude text_blocks) ---
        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()
        count2 = 0
        item_count2 = 0
        for filing, stmts in iter_parquet(tmp_path, batch_size=50, include_text_blocks=False):
            count2 += 1
            if stmts is not None:
                item_count2 += len(stmts)
        t_iter2 = time.perf_counter() - t0
        _, peak_iter2 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"\niter_parquet (exclude text_blocks):")
        print(f"  時間: {_fmt(t_iter2)}")
        print(f"  メモリ peak: {_fmt_mb(peak_iter2)}")
        print(f"  アイテム数: {item_count2:,} (TextBlock除外: -{item_count - item_count2:,})")

        # --- row group 検証 ---
        import pyarrow.parquet as pq
        meta = pq.read_metadata(tmp_path / "filings.parquet")
        li_meta = pq.read_metadata(tmp_path / "line_items.parquet")
        print(f"\nrow group 検証:")
        print(f"  filings: {meta.num_row_groups} RGs ({meta.num_rows} rows)")
        print(f"  line_items: {li_meta.num_row_groups} RGs ({li_meta.num_rows} rows)")
        print(f"  1doc=1RG: {'OK' if meta.num_row_groups == n_docs else 'NG'}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parquet ベンチマーク")
    parser.add_argument("--docs", type=int, default=100, help="書類数 (default: 100)")
    parser.add_argument("--items", type=int, default=100, help="1書類あたりの LineItem 数 (default: 100)")
    args = parser.parse_args()

    _run_bench(args.docs, args.items)

    # 小規模も回す
    if args.docs >= 50:
        _run_bench(10, 50)


if __name__ == "__main__":
    main()
