"""エラー書類の分析スクリプト。

filings テーブルから失敗書類を抽出し、企業名・タイトル・日付の傾向を分析する。

使い方:
    uv run python tools/analyze_errors.py /tmp/2025-H1 --prefix "2025-01-01_2025-06-30_"
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pyarrow.parquet as pq


def main() -> None:
    parser = argparse.ArgumentParser(description="エラー書類の分析")
    parser.add_argument("input_dir", help="Parquet ディレクトリ")
    parser.add_argument("--prefix", default="", help="ファイル名プレフィックス")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    filings_path = input_dir / f"{args.prefix}filings.parquet"

    table = pq.read_table(filings_path)
    rows = table.to_pylist()

    failed = [r for r in rows if not r.get("has_xbrl") and r.get("xbrl_url")]

    if not failed:
        print("エラーなし。")
        return

    print(f"エラー書類: {len(failed)} 件\n")

    # タイトル分類
    title_counter: Counter[str] = Counter()
    for r in failed:
        title = r["title"]
        # 短縮: 企業名部分を除去してパターン化
        if "決算短信" in title:
            title_counter["決算短信"] += 1
        elif "業績予想" in title:
            title_counter["業績予想の修正"] += 1
        elif "配当予想" in title:
            title_counter["配当予想の修正"] += 1
        elif "剰余金" in title or "配当" in title:
            title_counter["配当関連"] += 1
        else:
            title_counter[title[:30]] += 1

    print("=== タイトル分類 ===")
    for title, count in title_counter.most_common():
        print(f"  {title}: {count}")

    # 月別分布
    month_counter: Counter[str] = Counter()
    for r in failed:
        pubdate = r.get("pubdate", "")
        if len(pubdate) >= 7:
            month_counter[pubdate[:7]] += 1

    print(f"\n=== 月別分布 ===")
    for month, count in sorted(month_counter.items()):
        print(f"  {month}: {count}")

    # 企業別（上位20）
    company_counter: Counter[str] = Counter()
    for r in failed:
        company_counter[f"{r['company_code']} {r['company_name']}"] += 1

    print(f"\n=== 企業別（上位20） ===")
    for company, count in company_counter.most_common(20):
        print(f"  {company}: {count}")

    # 全企業のユニーク数
    unique_companies = len(company_counter)
    print(f"\n  ユニーク企業数: {unique_companies}")

    # 成功書類の企業と比較（上場廃止判定）
    ok_codes = {r["company_code"] for r in rows if r.get("has_xbrl")}
    failed_codes = {r["company_code"] for r in failed}
    only_failed = failed_codes - ok_codes  # 成功が1件もない企業

    print(f"\n=== 上場廃止の可能性 ===")
    print(f"  失敗のみの企業（成功0件）: {len(only_failed)}")
    if only_failed:
        for code in sorted(only_failed):
            names = [r["company_name"] for r in failed if r["company_code"] == code]
            titles = [r["title"] for r in failed if r["company_code"] == code]
            print(f"    {code} {names[0]} ({len(titles)}件)")
            for t in titles[:3]:
                print(f"      - {t}")

    both = failed_codes & ok_codes
    print(f"  成功もある企業: {len(both)}")

    # 全件リスト出力
    print(f"\n=== 全エラー書類 ===")
    for r in sorted(failed, key=lambda x: x.get("pubdate", "")):
        print(f"  {r['pubdate'][:10]} {r['company_code']} {r['company_name']}: {r['title'][:40]}")


if __name__ == "__main__":
    main()
