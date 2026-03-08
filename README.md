# tdnet — TDnet 適時開示情報 Python ライブラリ

[![PyPI version](https://img.shields.io/pypi/v/tdnet.svg)](https://pypi.org/project/tdnet/)
[![Python](https://img.shields.io/pypi/pyversions/tdnet.svg)](https://pypi.org/project/tdnet/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Context7 Indexed](https://img.shields.io/badge/Context7-Indexed-047857)](https://context7.com/youseiushida/tdnet)
[![Context7 llms.txt](https://img.shields.io/badge/Context7-llms.txt-047857)](https://context7.com/youseiushida/tdnet/llms.txt)

**tdnet** は、[TDnet（適時開示情報伝達システム）](https://www.release.tdnet.info/)の開示書類を取得・解析する Python ライブラリです。決算短信・業績予想修正・配当予想修正などの XBRL を自動パースし、230+ の正規化キー（CK）で J-GAAP / IFRS / US-GAAP の財務数値を統一的に抽出できます。内部の HTTP 通信には [httpx](https://github.com/encode/httpx) を、iXBRL 解析には [xbrl-core](https://github.com/youseiushida/xbrl-core) を使用しています。

## インストール

```sh
pip install tdnet
```

依存: `httpx`, `xbrl-core`, `lxml`, `pandas`

## クイックスタート

API キーは不要です。インストールしたらすぐに使えます。

```python
import tdnet
from tdnet import CK, extract_values, extracted_to_dict

# 開示一覧を取得（XBRL 付きのみ）
filings = tdnet.documents("20260304", has_xbrl=True)

# 最初の決算短信を XBRL パース
f = [f for f in filings if "決算短信" in f.title][0]
stmts = f.xbrl()

# 主要指標を一括取得
result = extract_values(
    stmts,
    [CK.REVENUE, CK.OPERATING_INCOME, CK.NET_INCOME_PARENT, CK.EPS],
    period="current",
    consolidated=True,
)
row = extracted_to_dict(result)
for k, v in row.items():
    print(f"{k}: {v}")
```

## 開示一覧の取得

```python
import tdnet

# 日付指定
filings = tdnet.documents("20260304", has_xbrl=True)

# 証券コード指定（直近の開示）
filings = tdnet.documents(code=7203, has_xbrl=True, limit=10)

# 最新の開示
filings = tdnet.documents(has_xbrl=True)

# 期間指定
from tdnet import list_by_range
items = list_by_range("20260301", "20260305", has_xbrl=True)
```

データソースは [やのしんWEB-API](https://webapi.yanoshin.jp/) をデフォルトで使用します。やのしん API が利用できない場合（ネットワークエラー・サーバーエラー）は release.tdnet.info のスクレイピングに自動フォールバックします。`source="scrape"` で直接スクレイピングを指定することもできます。

## Filing

`Filing` は開示書類 1 件を表します。

```python
f = filings[0]
print(f.company_code)   # '25900'
print(f.company_name)   # 'ＤｙＤｏ'
print(f.title)          # '2026年1月期 決算短信〔日本基準〕（連結）'
print(f.pubdate)        # '2026-03-04 15:30:00'
print(f.has_xbrl)       # True
print(f.doc_id)         # '575305'

# XBRL パース → Statements
stmts = f.xbrl()

# XBRL ZIP の生バイト取得（キャッシュ対応）
result = f.fetch_xbrl()
result.data        # bytes: ZIP データ
result.source_url  # str: 実際にダウンロードした URL

# PDF 取得
result = f.fetch_pdf()
result.data        # bytes: PDF データ
result.source_url  # str: 実際にダウンロードした URL

# async 版（asyncio.gather で並行処理可能）
stmts = await f.axbrl()
result = await f.afetch_xbrl()
result = await f.afetch_pdf()
```

> XBRL / PDF は release.tdnet.info 上で約 30-40 日で削除されます。期限切れの場合は JPX の永続 URL (`www2.jpx.co.jp`) に自動フォールバックします。`source_url` でどちらから取得したか確認できます。

## 正規化キー（CK）による値取得

`extract_values()` は Statements を 1 パス走査し、正規化キー（CK）で値を抽出します。

```python
from tdnet import CK, extract_values, extracted_to_dict

# PL
result = extract_values(stmts, [
    CK.REVENUE, CK.COST_OF_SALES, CK.GROSS_PROFIT,
    CK.SGA_EXPENSES, CK.OPERATING_INCOME,
    CK.ORDINARY_INCOME, CK.NET_INCOME_PARENT,
], period="current", consolidated=True)
row = extracted_to_dict(result)

# BS
result = extract_values(stmts, [
    CK.TOTAL_ASSETS, CK.CURRENT_ASSETS, CK.NONCURRENT_ASSETS,
    CK.TOTAL_LIABILITIES, CK.NET_ASSETS,
    CK.CASH_AND_DEPOSITS, CK.INVENTORIES,
    CK.SHAREHOLDERS_EQUITY, CK.RETAINED_EARNINGS,
], period="current", consolidated=True)

# CF
result = extract_values(stmts, [
    CK.OPERATING_CF, CK.INVESTING_CF, CK.FINANCING_CF,
    CK.DEPRECIATION_CF, CK.PURCHASE_PPE_CF,
], period="current", consolidated=True)

# KPI
result = extract_values(stmts, [
    CK.EPS, CK.BPS, CK.ROE, CK.ROA,
    CK.EQUITY_RATIO, CK.OPERATING_MARGIN,
], period="current", consolidated=True)
```

### 全マッピング可能 CK の自動抽出

`keys` を省略すると、マッピング可能な全 CK を自動抽出します。

```python
all_result = extract_values(stmts, period="current", consolidated=True)
print(f"取得: {len(all_result)} CKs")
for k, ev in sorted(all_result.items()):
    print(f"  {k}: {ev.value}")
```

### 前期比較

```python
current = extracted_to_dict(
    extract_values(stmts, [CK.REVENUE], period="current", consolidated=True)
)
prior = extracted_to_dict(
    extract_values(stmts, [CK.REVENUE], period="prior", consolidated=True)
)
```

### 非連結（個別）

```python
# 配当 (DPS) は常に非連結で取得
result = extract_values(stmts, [CK.DPS], period="current", consolidated=False)
```

> 非連結決算短信では `consolidated=True` だと 0 件になります。`consolidated=False` を指定してください。

### 変動率・変動額

決算短信サマリーの前年同期比や業績予想修正の変動情報を取得できます。

```python
result = extract_values(stmts, [
    CK.CHANGE_REVENUE, CK.CHANGE_OPERATING_INCOME,
    CK.CHANGE_NET_INCOME_PARENT,
    CK.AMOUNT_CHANGE_REVENUE, CK.AMOUNT_CHANGE_OPERATING_INCOME,
], period="current", consolidated=True)
```

### 業績予想

```python
result = extract_values(stmts, [
    CK.FORECAST_REVENUE, CK.FORECAST_OPERATING_INCOME,
    CK.FORECAST_NET_INCOME_PARENT, CK.FORECAST_EPS,
    CK.FORECAST_DPS,
])
```

### ExtractedValue

`extract_values()` の戻り値は `dict[str, ExtractedValue | None]` です。

```python
result = extract_values(stmts, [CK.REVENUE], period="current", consolidated=True)
ev = result[CK.REVENUE]
if ev is not None:
    print(ev.value)          # Decimal('237189000000')
    print(ev.canonical_key)  # 'revenue'
    print(ev.mapper_name)    # 'summary_mapper'
    print(ev.item)           # 元の LineItem
```

## ローカル XBRL の解析

別途ダウンロードした XBRL ZIP ファイルを直接解析できます。API 通信は不要です。

```python
from tdnet import parse_zip, CK, extract_values, extracted_to_dict

# ZIP ファイルを読み込み
with open("140120250306553722.zip", "rb") as f:
    zip_data = f.read()

# 解析
stmts = parse_zip(zip_data)

# 値の抽出
result = extract_values(
    stmts,
    [CK.REVENUE, CK.OPERATING_INCOME, CK.NET_INCOME_PARENT],
    period="current",
    consolidated=True,
)
row = extracted_to_dict(result)
for k, v in row.items():
    print(f"{k}: {v}")
```

iXBRL ファイルを直接渡すこともできます。

```python
from tdnet import parse_ixbrl_files

# ファイル名をキー、iXBRL bytes を値とする辞書
files = {
    "summary-ixbrl.htm": open("summary-ixbrl.htm", "rb").read(),
    "attachment-ixbrl.htm": open("attachment-ixbrl.htm", "rb").read(),
}
stmts = parse_ixbrl_files(files)
```

## CK 以外の FACT へのアクセス

CK にマッピングされていない科目は `local_name` / `search()` / イテレーションで直接取得できます。

```python
# local_name で取得
item = stmts["AllowanceForDoubtfulAccountsCA"]
item = stmts.get("AllowanceForDoubtfulAccountsCA")  # None if not found
print(item.value)

# キーワード検索（ラベル・local_name を部分一致）
items = stmts.search("貸倒")
for item in items:
    print(f"{item.local_name}: {item.value}")

# 全件走査
for item in stmts:
    if "SGA" in item.local_name:
        print(f"{item.local_name}: {item.value}")
```

### LineItem の属性

```python
item.local_name      # 'CashAndDeposits'
item.namespace_uri   # 'http://disclosure.edinet-fsa.go.jp/...'
item.value           # Decimal('30657000000')
item.unit_ref        # 'JPY'
item.decimals        # '-6'
item.period          # InstantPeriod / DurationPeriod
item.dimensions      # tuple[DimensionMember, ...]
item.label_ja        # LabelInfo(text='現金及び預金', source=LabelSource.STANDARD)
item.label_en        # LabelInfo(text='Cash and deposits', source=LabelSource.STANDARD)
```

## 財務諸表コンテナ

`Statements` から個別の財務諸表を組み立てることもできます。

```python
pl = stmts.income_statement(consolidated=True, period="current")
bs = stmts.balance_sheet(consolidated=True, period="current")
cf = stmts.cash_flow_statement(consolidated=True, period="current")
ci = stmts.comprehensive_income(consolidated=True, period="current")
eq = stmts.equity_statement(consolidated=True, period="current")

for item in pl:
    print(f"{item.local_name}: {item.value}")
```

## パイプラインマッパー

デフォルトのマッパーパイプラインは以下の 6 マッパーです。

| 順位 | マッパー | 対象 | 概念数 |
|:---|:---|:---|:---|
| 1 | `dividend_mapper` | 配当（DPS）、AnnualDividendPaymentScheduleAxis 対応 | — |
| 2 | `forecast_mapper` | 業績予想（ResultForecastAxis=ForecastMember） | — |
| 3 | `summary_mapper` | tse-ed-t サマリー科目（経営指標） | 230+ (XSD検証済) |
| 4 | `statement_mapper` | jppfs_cor / IFRS / US-GAAP / REIT PL/BS/CF 本体 | 190+ |
| 5 | `definition_mapper()` | Definition Linkbase の general-special で独自科目 → 標準科目に遡上 | 動的 |
| 6 | `calc_mapper()` | Calculation Linkbase の summation-item で独自科目 → 親標準科目に遡上 | 動的 |

先頭のマッパーほど高優先。1 アイテムに対して最初にマッチしたマッパーが採用されます。

`definition_mapper()` / `calc_mapper()` はリンクベースデータが `Statements` に設定されている場合に機能します。TDnet の決算短信 ZIP にはリンクベースが同梱されないため、デフォルトでは何もマッチしません（既存動作に影響なし）。外部から取得したリンクベースを渡す場合は `Statements` の `definition_linkbase` / `calculation_linkbase` パラメータを使用してください。

### カスタムマッパーの追加

`dict_mapper()` で独自のマッピングを追加できます。

```python
from tdnet import dict_mapper, summary_mapper, statement_mapper, extract_values

custom = dict_mapper({
    "GainOnSalesOfInvestmentSecuritiesEI": "custom_gain_investment_sales",
    "LossOnRetirementOfNoncurrentAssetsEL": "custom_loss_retirement",
})

result = extract_values(
    stmts,
    ["custom_gain_investment_sales", "custom_loss_retirement"],
    mapper=[summary_mapper, statement_mapper, custom],
)
```

マッパーは `Callable[[LineItem, MapperContext], str | None]` のシグネチャです。関数を直接書くこともできます。

```python
from tdnet import ConceptMapper, MapperContext
from xbrl_core import LineItem

def my_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    if item.local_name == "SpecialConcept":
        return "my_special_key"
    return None
```

### リンクベースマッパーのカスタム lookup 注入

`definition_mapper()` と `calc_mapper()` は `lookup` 引数で名寄せ先の辞書を注入できます。内蔵の CK を使わず、独自の名寄せ体系で完結させることが可能です。

```python
from tdnet import definition_mapper, calc_mapper, dict_mapper, extract_values

# 独自の名寄せ辞書
my_map = {"NetSales": "売上高", "OperatingIncome": "営業利益", "CostOfSales": "売上原価"}

pipeline = [
    dict_mapper(my_map),                     # 辞書完全一致
    definition_mapper(lookup=my_map.get),     # def linkbase で祖先を辿り → my_map で解決
    calc_mapper(lookup=my_map.get),           # calc linkbase で祖先を辿り → my_map で解決
]

result = extract_values(stmts, ["売上高", "営業利益"], mapper=pipeline)
```

## pandas 連携

```python
# 全 LineItem を DataFrame に変換
df = stmts.to_dataframe()
print(df[["label_ja", "value", "local_name"]].head())

# CSV / Parquet / Excel 出力
stmts.to_csv("output.csv")
stmts.to_parquet("output.parquet")
stmts.to_excel("output.xlsx")

# 個別の財務諸表も DataFrame 変換可能
pl_df = stmts.income_statement().to_dataframe()
bs_df = stmts.balance_sheet().to_dataframe(full=True)  # 全カラム
```

## 複数銘柄の一括処理

```python
import tdnet
from tdnet import CK, extract_values, extracted_to_dict

filings = tdnet.documents("20260304", has_xbrl=True)

for f in filings:
    if "決算短信" not in f.title:
        continue
    stmts = f.xbrl()
    result = extract_values(
        stmts,
        [CK.REVENUE, CK.OPERATING_INCOME, CK.NET_INCOME_PARENT],
        period="current", consolidated=True,
    )
    row = extracted_to_dict(result)
    print(f"{f.company_code} {f.company_name}: 売上={row.get(CK.REVENUE)}")
```

### 非同期 (async) での一括処理

`Filing` は async メソッド (`axbrl()`, `afetch_xbrl()`, `afetch_pdf()`) を提供しています。`asyncio.gather()` で並行ダウンロード・パースが可能です。

```python
import asyncio
import tdnet
from tdnet import CK, extract_values, extracted_to_dict

async def main():
    filings = tdnet.documents("20260304", has_xbrl=True)

    # 全件を並行ダウンロード＋パース
    stmts_list = await asyncio.gather(*[f.axbrl() for f in filings])

    for f, stmts in zip(filings, stmts_list):
        row = extracted_to_dict(
            extract_values(stmts, [CK.REVENUE], period="current", consolidated=True)
        )
        print(f"{f.company_code}: {row.get(CK.REVENUE)}")

asyncio.run(main())
```

## TDnet 検索

キーワード・期間で TDnet の開示を検索できます。

```python
from tdnet import search

results = search(start_date="20260301", end_date="20260305", keyword="業績予想")
for item in results:
    print(item["company_code"], item["title"])
```

## キャッシュ

`cache_dir` を設定すると、XBRL ZIP のダウンロードをディスクキャッシュします。

```python
import tdnet

tdnet.configure(cache_dir="./cache")

# 以降の fetch_xbrl() はキャッシュを使用
stmts = filing.xbrl()  # 2回目以降はキャッシュから読み込み

# キャッシュ情報
from tdnet.cache import cache_info, clear_cache
info = cache_info()
print(f"entries: {info.entry_count}, size: {info.total_bytes} bytes")

# キャッシュクリア
clear_cache()
```

## 設定

`configure()` でグローバル設定を変更できます。

```python
import tdnet

tdnet.configure(
    cache_dir="./cache",       # キャッシュディレクトリ（None で無効）
    timeout=60.0,              # HTTP タイムアウト秒（デフォルト: 30）
    max_retries=5,             # リトライ回数（デフォルト: 3）
    rate_limit=2.0,            # リクエスト間隔秒（デフォルト: 1.0）
    taxonomy_path=None,        # タクソノミパス（None でバンドル使用）
)
```

## リトライ・レート制限

通信エラー（タイムアウト、接続エラー）および HTTP 429/500 番台は、指数バックオフで自動リトライされます（デフォルト最大 3 回）。レート制限はデフォルト 1 秒に 1 リクエストです。

## エラーハンドリング

すべての例外は `TdnetError` を継承しています。

```python
import tdnet
from tdnet import TdnetError, TdnetAPIError, TdnetParseError, TdnetConfigError

try:
    stmts = filing.xbrl()
except TdnetAPIError as e:
    print(f"HTTP {e.status_code}: {e}")
except TdnetParseError as e:
    print(f"Parse error: {e}")
except TdnetError as e:
    print(f"Error: {e}")
```

| 例外クラス | 説明 |
|:---|:---|
| `TdnetError` | 基底例外 |
| `TdnetConfigError` | 設定に関するエラー |
| `TdnetAPIError` | HTTP エラー（status_code 付き） |
| `TdnetParseError` | XBRL / HTML 解析エラー |
| `TdnetWarning` | 警告（warnings モジュール経由） |

## CK 一覧（主要）

`CK` は `StrEnum` です。`CK.REVENUE == "revenue"` が `True` になります。

### PL（損益計算書）

| CK | 値 | 説明 |
|:---|:---|:---|
| `CK.REVENUE` | `revenue` | 売上高 |
| `CK.COST_OF_SALES` | `cost_of_sales` | 売上原価 |
| `CK.GROSS_PROFIT` | `gross_profit` | 売上総利益 |
| `CK.SGA_EXPENSES` | `sga_expenses` | 販管費 |
| `CK.OPERATING_INCOME` | `operating_income` | 営業利益 |
| `CK.ORDINARY_INCOME` | `ordinary_income` | 経常利益 |
| `CK.NET_INCOME_PARENT` | `net_income_parent` | 親会社株主帰属純利益 |
| `CK.NET_INCOME` | `net_income` | 当期純利益 |
| `CK.INCOME_BEFORE_TAX` | `income_before_tax` | 税引前利益 |

### BS（貸借対照表）

| CK | 値 | 説明 |
|:---|:---|:---|
| `CK.TOTAL_ASSETS` | `total_assets` | 総資産 |
| `CK.CURRENT_ASSETS` | `current_assets` | 流動資産 |
| `CK.NONCURRENT_ASSETS` | `noncurrent_assets` | 固定資産 |
| `CK.CASH_AND_DEPOSITS` | `cash_and_deposits` | 現金及び預金 |
| `CK.TRADE_RECEIVABLES` | `trade_receivables` | 売上債権 |
| `CK.INVENTORIES` | `inventories` | 棚卸資産 |
| `CK.TOTAL_LIABILITIES` | `total_liabilities` | 負債合計 |
| `CK.NET_ASSETS` | `net_assets` | 純資産 |
| `CK.SHAREHOLDERS_EQUITY` | `shareholders_equity` | 株主資本 |

### CF（キャッシュフロー計算書）

| CK | 値 | 説明 |
|:---|:---|:---|
| `CK.OPERATING_CF` | `operating_cf` | 営業CF |
| `CK.INVESTING_CF` | `investing_cf` | 投資CF |
| `CK.FINANCING_CF` | `financing_cf` | 財務CF |
| `CK.DEPRECIATION_CF` | `depreciation_cf` | 減価償却費 |
| `CK.CASH_END` | `cash_end` | 期末現金残高 |

### KPI

| CK | 値 | 説明 |
|:---|:---|:---|
| `CK.EPS` | `eps` | 1株当たり利益 |
| `CK.BPS` | `bps` | 1株当たり純資産 |
| `CK.DPS` | `dps` | 1株当たり配当 |
| `CK.ROE` | `roe` | 自己資本利益率 |
| `CK.ROA` | `roa` | 総資産利益率 |
| `CK.EQUITY_RATIO` | `equity_ratio` | 自己資本比率 |
| `CK.OPERATING_MARGIN` | `operating_margin` | 営業利益率 |

### 変動率

| CK | 値 | 説明 |
|:---|:---|:---|
| `CK.CHANGE_REVENUE` | `change_revenue` | 売上高増減率 |
| `CK.CHANGE_OPERATING_INCOME` | `change_operating_income` | 営業利益増減率 |
| `CK.CHANGE_NET_INCOME_PARENT` | `change_net_income_parent` | 純利益増減率 |

全 CK 定義は `CK` enum（250+ メンバー）を参照してください。業種別（銀行・保険・証券）、IFRS/US-GAAP 固有、業績予想、ESG 等を含みます。

## 注意事項

- **配当 (DPS)**: 常に `consolidated=False` で取得してください
- **非連結決算**: `consolidated=False` を指定（`True` だと 0 件）
- **銀行・保険**: `CK.ORDINARY_REVENUE_BANKING` 等の業種固有 CK を使用
- **XBRL/PDF の公開期限**: release.tdnet.info 上で約 30-40 日で削除。期限切れ時は JPX 永続 URL に自動フォールバック
- **タクソノミ**: tse-ed-t (2014-01-12) をパッケージに同梱済み。設定不要

## 動作要件

Python 3.12 以上。
