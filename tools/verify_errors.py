"""ダンプエラーの検証スクリプト。

Parquet の filings テーブルから has_xbrl=False の XBRL 付き書類を抽出し、
HEAD リクエストで TDnet/JPX の URL 到達性を確認する。

使い方:
    # 特定の半年データを検証
    uv run python tools/verify_errors.py parquet_output --prefix "2025-01-01_2025-06-30_"

    # ローカルのデータを検証
    uv run python tools/verify_errors.py parquet/tdnet --prefix "2025-03-01_2025-03-07_"
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import httpx
import pyarrow.parquet as pq


def _head(url: str, client: httpx.Client) -> int:
    """HEAD リクエストを送りステータスコードを返す。"""
    try:
        r = client.head(url, follow_redirects=True)
        return r.status_code
    except httpx.TransportError:
        return -1


def _build_jpx_url(tdnet_url: str, company_code: str) -> str:
    """TDnet URL を JPX 永続 URL に変換する。"""
    filename = tdnet_url.rsplit("/", 1)[-1]
    code = company_code if len(company_code) == 5 else company_code + "0"
    return f"https://www2.jpx.co.jp/disc/{code}/{filename}"


def main() -> None:
    parser = argparse.ArgumentParser(description="ダンプエラーの検証")
    parser.add_argument("input_dir", help="Parquet ディレクトリ")
    parser.add_argument("--prefix", default="", help="ファイル名プレフィックス")
    parser.add_argument("--limit", type=int, default=0, help="検証件数上限 (0=全件)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    filings_path = input_dir / f"{args.prefix}filings.parquet"

    if not filings_path.exists():
        print(f"ファイルが見つかりません: {filings_path}")
        sys.exit(1)

    table = pq.read_table(filings_path)
    rows = table.to_pylist()

    # has_xbrl=False だが xbrl_url が空でない = DL/パース失敗した書類
    failed = [r for r in rows if not r.get("has_xbrl") and r.get("xbrl_url")]
    ok = [r for r in rows if r.get("has_xbrl")]
    no_xbrl = [r for r in rows if not r.get("xbrl_url")]

    print(f"filings 合計: {len(rows)}")
    print(f"  XBRL 成功 (has_xbrl=True): {len(ok)}")
    print(f"  XBRL 失敗 (has_xbrl=False, xbrl_url あり): {len(failed)}")
    print(f"  XBRL なし (xbrl_url 空): {len(no_xbrl)}")

    if not failed:
        print("\nエラーなし。検証不要。")
        return

    if args.limit:
        failed = failed[:args.limit]

    print(f"\n{len(failed)} 件を HEAD リクエストで検証中...")

    tdnet_status: Counter[int] = Counter()
    jpx_status: Counter[int] = Counter()
    other_errors: list[dict] = []

    with httpx.Client(timeout=10, follow_redirects=True) as client:
        for i, row in enumerate(failed):
            xbrl_url = row["xbrl_url"]
            company_code = row["company_code"]
            doc_id = row["doc_id"]

            # TDnet HEAD
            ts = _head(xbrl_url, client)
            tdnet_status[ts] += 1

            # JPX HEAD
            jpx_url = _build_jpx_url(xbrl_url, company_code)
            js = _head(jpx_url, client)
            jpx_status[js] += 1

            # 両方 404 以外のケースを記録
            if ts not in (403, 404) or js != 404:
                other_errors.append({
                    "doc_id": doc_id,
                    "tdnet_status": ts,
                    "jpx_status": js,
                    "xbrl_url": xbrl_url,
                })

            if (i + 1) % 50 == 0:
                print(f"  ... {i + 1}/{len(failed)}")

    print(f"\n=== TDnet ステータス ===")
    for status, count in sorted(tdnet_status.items()):
        print(f"  {status}: {count}")

    print(f"\n=== JPX ステータス ===")
    for status, count in sorted(jpx_status.items()):
        print(f"  {status}: {count}")

    # 判定
    both_404 = sum(
        1 for r in failed[:len(failed)]
        if True  # カウントは上で取ってる
    )
    expected_404 = min(tdnet_status.get(403, 0) + tdnet_status.get(404, 0), len(failed))

    print(f"\n=== 判定 ===")
    print(f"  TDnet 403/404: {tdnet_status.get(403, 0) + tdnet_status.get(404, 0)}/{len(failed)}")
    print(f"  JPX 404: {jpx_status.get(404, 0)}/{len(failed)}")

    if other_errors:
        print(f"\n=== 404 以外のエラー ({len(other_errors)} 件) ===")
        for e in other_errors[:20]:
            print(f"  {e['doc_id']}: TDnet={e['tdnet_status']} JPX={e['jpx_status']}")
            print(f"    {e['xbrl_url']}")
        if len(other_errors) > 20:
            print(f"  ... 他 {len(other_errors) - 20} 件")
    else:
        print(f"\n全エラーが TDnet 403/404 + JPX 404。ファイル消失が原因。問題なし。")


if __name__ == "__main__":
    main()
