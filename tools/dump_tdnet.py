"""TDnet 決算短信等を Parquet にダンプするスクリプト。

対象: 決算短信、業績予想の修正、配当予想の修正（全 XBRL 書類を一括ダンプ）。

使い方:
    uv run python tools/dump_tdnet.py \
        --start 2025-03-01 --end 2025-03-31

    # 出力先や並行数の変更
    uv run python tools/dump_tdnet.py \
        --start 2025-03-01 --end 2025-03-31 \
        --output-dir ./parquet/tdnet \
        --concurrency 4

    # ProcessPool でパースを高速化
    uv run python tools/dump_tdnet.py \
        --start 2025-03-01 --end 2025-03-31 \
        --process-pool --max-workers 4
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

ROOT = Path(__file__).resolve().parent.parent


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


async def _run_dump(
    *,
    start: str,
    end: str,
    output_dir: Path,
    prefix: str,
    concurrency: int,
    taxonomy_path: str | None,
    use_thread_pool: bool,
    use_process_pool: bool,
    max_workers: int,
) -> dict[str, Any]:
    """ダンプを実行し計測結果を返す。"""
    if use_process_pool:
        mode_label = f"process-pool(workers={max_workers})"
    elif use_thread_pool:
        mode_label = f"thread-pool(workers={max_workers})"
    else:
        mode_label = "async"

    print(f"\n{'─' * 60}")
    print(f"TDnet ダンプ ({mode_label})")
    print(f"  prefix={prefix}, 期間={start}〜{end}")
    print(f"{'─' * 60}")

    gc.collect()
    tracemalloc.start()
    t0 = time.perf_counter()

    common_kwargs: dict[str, Any] = {
        "start": start,
        "end": end,
        "output_dir": output_dir,
        "prefix": prefix,
        "concurrency": concurrency,
        "taxonomy_path": taxonomy_path,
    }

    if use_process_pool:
        from tdnet.extension import adump_to_parquet_process_pool

        result = await adump_to_parquet_process_pool(
            **common_kwargs, max_workers=max_workers,
        )
    elif use_thread_pool:
        from tdnet.extension import adump_to_parquet_thread_pool

        result = await adump_to_parquet_thread_pool(
            **common_kwargs, max_workers=max_workers,
        )
    else:
        from tdnet.extension import adump_to_parquet

        result = await adump_to_parquet(**common_kwargs)

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gc.collect()

    file_sizes = _measure_files(output_dir, prefix)

    print(f"  書類数: {result.total_filings}")
    print(f"  XBRL: {result.xbrl_ok}/{result.xbrl_count} 成功")
    print(f"  エラー: {result.errors}")
    print(f"  時間: {_fmt_time(elapsed)}")
    print(f"  メモリ peak: {_fmt_mb(peak)}")
    print(f"  ファイルサイズ: {file_sizes['__total__']:.1f} MB")

    return {
        "total_filings": result.total_filings,
        "xbrl_count": result.xbrl_count,
        "xbrl_ok": result.xbrl_ok,
        "errors": result.errors,
        "elapsed": elapsed,
        "mem_peak": peak,
        "file_size_mb": file_sizes["__total__"],
        "file_sizes": file_sizes,
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
        "--thread-pool", action="store_true", default=False,
        help="ThreadPoolExecutor でパースをオフロードする",
    )
    parser.add_argument(
        "--process-pool", action="store_true", default=False,
        help="ProcessPoolExecutor でパースをオフロードする（GIL 完全回避）",
    )
    parser.add_argument(
        "--max-workers", type=int, default=4,
        help="Thread/ProcessPool のワーカー数 (default: 4)",
    )
    args = parser.parse_args()

    if args.thread_pool and args.process_pool:
        parser.error("--thread-pool と --process-pool は同時に指定できません")

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
        use_thread_pool=args.thread_pool,
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
