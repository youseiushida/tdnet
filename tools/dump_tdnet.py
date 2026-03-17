"""TDnet 決算短信等を Parquet にダンプするスクリプト。

対象: 決算短信、業績予想の修正、配当予想の修正（全 XBRL 書類を一括ダンプ）。

やのしん API は日単位なので、日ごとにループして Filing を収集し、
_ParquetWriters でストリーミング書き出しする。

使い方:
    uv run python tools/dump_tdnet.py \
        --start 2025-03-01 --end 2025-03-31

    # ProcessPool でパースを高速化
    uv run python tools/dump_tdnet.py \
        --start 2025-03-01 --end 2025-03-31 \
        --process-pool --max-workers 4
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import logging
import sys
import time
import tracemalloc
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)


def _fmt_mb(b: float) -> str:
    """バイト数を MB 文字列にフォーマットする。"""
    return f"{b / (1024 * 1024):.1f} MB"


def _fmt_time(s: float) -> str:
    """秒数を見やすい文字列にフォーマットする。"""
    if s < 60:
        return f"{s:.1f}s"
    m, sec = divmod(s, 60)
    return f"{int(m)}m{sec:.0f}s"


def _measure_files(directory: Path, prefix: str) -> dict[str, float]:
    """Parquet ファイルのサイズ (MB) を計測する。"""
    sizes: dict[str, float] = {}
    total = 0.0
    for p in sorted(directory.glob(f"{prefix}*.parquet")):
        size_mb = p.stat().st_size / (1024 * 1024)
        sizes[p.name] = size_mb
        total += size_mb
    sizes["__total__"] = total
    return sizes


def _collect_filings(
    start: str,
    end: str,
    *,
    has_xbrl: bool = True,
) -> list[Any]:
    """日単位ループで Filing リストを構築する。

    やのしん API は日単位のため、start〜end を 1 日ずつ叩いて結合する。
    API エラーの日はスキップして続行する。
    """
    from tdnet.api import list_by_date
    from tdnet.filing import Filing
    from tdnet.exceptions import TdnetError

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    all_filings: list[Filing] = []
    current = start_date
    days_total = (end_date - start_date).days + 1
    days_done = 0

    while current <= end_date:
        date_str = current.strftime("%Y%m%d")
        try:
            items = list_by_date(date_str, has_xbrl=has_xbrl, limit=1000)
            day_filings = [Filing.from_yanoshin(item) for item in items]
            all_filings.extend(day_filings)
            if day_filings:
                print(f"  {current.isoformat()}: {len(day_filings)} 件")
        except TdnetError as exc:
            logger.warning("  %s: スキップ (%s)", current.isoformat(), exc)
        except Exception as exc:
            logger.warning("  %s: 予期しないエラー (%s)", current.isoformat(), exc)

        days_done += 1
        if days_done % 30 == 0:
            print(f"  ... {days_done}/{days_total} 日完了 ({len(all_filings)} 件)")

        current += timedelta(days=1)

    return all_filings


async def _run_dump(
    *,
    start: str,
    end: str,
    output_dir: Path,
    prefix: str,
    concurrency: int,
    taxonomy_path: str | None,
    use_process_pool: bool,
    max_workers: int,
) -> dict[str, Any]:
    """ダンプを実行し計測結果を返す。"""
    from tdnet.extension._schema import SCHEMAS
    from tdnet.extension._serialize import (
        is_text_block,
        serialize_calc_edges,
        serialize_def_parents,
        serialize_filing,
        serialize_line_item,
    )
    from tdnet.extension import _ParquetWriters, DumpResult

    mode_label = f"process-pool(workers={max_workers})" if use_process_pool else "async"

    print(f"\n{'─' * 60}")
    print(f"TDnet ダンプ ({mode_label})")
    print(f"  prefix={prefix}, 期間={start}〜{end}")
    print(f"{'─' * 60}")

    # 1. 日単位で Filing 収集
    print("\n[1/3] Filing 収集中...")
    filings = _collect_filings(start, end, has_xbrl=False)
    total_filings = len(filings)
    print(f"  合計: {total_filings} 件")

    xbrl_filings = [f for f in filings if f.has_xbrl]
    non_xbrl_filings = [f for f in filings if not f.has_xbrl]
    xbrl_count = len(xbrl_filings)
    print(f"  XBRL 付き: {xbrl_count} 件")

    # 2. Parquet 書き出し
    print(f"\n[2/3] Parquet 書き出し中... (concurrency={concurrency})")

    gc.collect()
    tracemalloc.start()
    t0 = time.perf_counter()

    writers = _ParquetWriters(output_dir, prefix, "zstd")
    xbrl_ok = 0
    errors = 0
    processed = 0

    try:
        # non-XBRL → 即書き出し
        if non_xbrl_filings:
            writers.write_rows(
                "filings",
                [serialize_filing(f, False) for f in non_xbrl_filings],
            )

        if use_process_pool:
            from concurrent.futures import ProcessPoolExecutor
            from tdnet.extension import _worker_parse_and_serialize

            loop = asyncio.get_running_loop()
            dl_sem = asyncio.Semaphore(concurrency)
            parse_sem = asyncio.Semaphore(max_workers * 2)

            async def _process(filing: Any, pool: Any) -> None:
                nonlocal xbrl_ok, errors, processed
                doc_id = filing.doc_id
                try:
                    async with parse_sem:
                        async with dl_sem:
                            dl_result = await filing.afetch_xbrl()
                            xbrl_data = dl_result.data
                        result = await loop.run_in_executor(
                            pool,
                            _worker_parse_and_serialize,
                            xbrl_data,
                            filing.company_code,
                            doc_id,
                            taxonomy_path,
                        )
                    writers.write_rows("filings", [serialize_filing(filing, True)])
                    writers.write_rows("line_items", result["li_rows"])
                    writers.write_rows("text_blocks", result["tb_rows"])
                    writers.write_rows("calc_edges", result["calc_rows"])
                    writers.write_rows("def_parents", result["def_rows"])
                    del result
                    xbrl_ok += 1
                except Exception:
                    logger.warning("XBRL パース失敗: %s", doc_id, exc_info=True)
                    writers.write_rows("filings", [serialize_filing(filing, False)])
                    errors += 1
                processed += 1
                if processed % 20 == 0:
                    gc.collect()
                if processed % 100 == 0:
                    print(f"  ... {processed}/{xbrl_count} 完了")

            with ProcessPoolExecutor(max_workers=max_workers) as pool:
                await asyncio.gather(
                    *[_process(f, pool) for f in xbrl_filings],
                )
        else:
            sem = asyncio.Semaphore(concurrency)

            async def _process_async(filing: Any) -> None:
                nonlocal xbrl_ok, errors, processed
                doc_id = filing.doc_id
                stmts = None
                async with sem:
                    try:
                        stmts = await filing.axbrl(taxonomy_path=taxonomy_path)
                    except Exception:
                        logger.warning("XBRL パース失敗: %s", doc_id, exc_info=True)
                        errors += 1
                writers.write_rows("filings", [serialize_filing(filing, stmts is not None)])
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
                        writers.write_rows("calc_edges", serialize_calc_edges(calc, doc_id))
                    defn = stmts._definition_linkbase
                    if defn is not None:
                        writers.write_rows("def_parents", serialize_def_parents(defn, doc_id))
                    del stmts
                    xbrl_ok += 1
                processed += 1
                if processed % 20 == 0:
                    gc.collect()
                if processed % 100 == 0:
                    print(f"  ... {processed}/{xbrl_count} 完了")

            await asyncio.gather(*[_process_async(f) for f in xbrl_filings])

    finally:
        result_paths = writers.close()

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gc.collect()

    file_sizes = _measure_files(output_dir, prefix)

    # 3. レポート
    print(f"\n[3/3] 結果")
    print(f"  書類数: {total_filings}")
    print(f"  XBRL: {xbrl_ok}/{xbrl_count} 成功")
    print(f"  エラー: {errors}")
    print(f"  時間: {_fmt_time(elapsed)}")
    print(f"  メモリ peak: {_fmt_mb(peak)}")
    print(f"  ファイルサイズ: {file_sizes['__total__']:.1f} MB")
    for name, sz in sorted(file_sizes.items()):
        if name != "__total__":
            print(f"    {name}: {sz:.1f} MB")

    return {
        "total_filings": total_filings,
        "xbrl_count": xbrl_count,
        "xbrl_ok": xbrl_ok,
        "errors": errors,
        "elapsed": elapsed,
        "mem_peak": peak,
        "file_size_mb": file_sizes["__total__"],
    }


async def main() -> None:
    """メイン処理。"""
    parser = argparse.ArgumentParser(
        description="TDnet 決算短信等を Parquet にダンプする",
    )
    parser.add_argument("--start", required=True, help="開始日 (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="終了日 (YYYY-MM-DD)")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "parquet" / "tdnet"),
        help="出力ディレクトリ (default: parquet/tdnet/)",
    )
    parser.add_argument(
        "--concurrency", type=int, default=8,
        help="同時ダウンロード数 (default: 8)",
    )
    parser.add_argument(
        "--process-pool", action="store_true", default=False,
        help="ProcessPoolExecutor でパースをオフロードする（GIL 完全回避）",
    )
    parser.add_argument(
        "--max-workers", type=int, default=4,
        help="ProcessPool のワーカー数 (default: 4)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{args.start}_{args.end}_"

    print("=" * 60)
    print("TDnet ダンプパイプライン")
    print("=" * 60)
    print(f"期間: {args.start} 〜 {args.end}")
    print(f"出力先: {output_dir}")
    print(f"並行数: {args.concurrency}")

    result = await _run_dump(
        start=args.start,
        end=args.end,
        output_dir=output_dir,
        prefix=prefix,
        concurrency=args.concurrency,
        taxonomy_path=None,
        use_process_pool=args.process_pool,
        max_workers=args.max_workers,
    )

    # レポート保存
    report_path = output_dir / "dump_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("TDnet ダンプパイプライン 結果レポート\n")
        f.write(f"期間: {args.start} 〜 {args.end}\n")
        f.write(f"出力先: {output_dir}\n\n")
        f.write(f"書類数: {result['total_filings']}\n")
        f.write(f"XBRL 成功: {result['xbrl_ok']}/{result['xbrl_count']}\n")
        f.write(f"エラー: {result['errors']}\n")
        f.write(f"時間: {_fmt_time(result['elapsed'])}\n")
        f.write(f"メモリ peak: {_fmt_mb(result['mem_peak'])}\n")
        f.write(f"ファイルサイズ: {result['file_size_mb']:.1f} MB\n")

    print(f"\nレポート保存: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
