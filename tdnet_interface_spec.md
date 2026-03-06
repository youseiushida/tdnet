# TDnet ライブラリ インターフェース仕様書

姉妹ライブラリ `edinet`（EDINET 開示書類の Python ライブラリ）と **出力側インターフェースを統一** するための仕様。
ユーザーが EDINET でも TDnet でも同じコードで財務データを扱えることを目標とする。

---

## 1. 設計方針

| レイヤー | 方針 |
|---|---|
| **入力（API・Filing）** | TDnet 固有。合わせない |
| **出力（財務データモデル）** | edinet と同一インターフェースにする |
| **CK（正規化キー）** | 完全に同一の定義を使う |
| **例外・警告** | 命名規則を揃える（`Tdnet` プレフィックス） |
| **設定** | `configure()` のシグネチャ構造を揃える |

---

## 2. CK（CanonicalKey）— 完全コピー対象

`StrEnum` で定義された財務科目の正規化キー。EDINET/TDnet 共通の語彙。
tdnet ライブラリでもこの定義を **そのままコピー** して使う。

```python
from enum import StrEnum

class CK(StrEnum):
    """CanonicalKey 定数群。

    StrEnum を使用。``CK.REVENUE == "revenue"`` が True（.value 不要）。
    ``isinstance(CK.REVENUE, str)`` も True のため dict[str, ...] にそのまま使える。
    """
    # === PL（損益計算書） ===
    REVENUE = 'revenue'
    COST_OF_SALES = 'cost_of_sales'
    GROSS_PROFIT = 'gross_profit'
    SGA_EXPENSES = 'sga_expenses'
    OPERATING_INCOME = 'operating_income'
    NON_OPERATING_INCOME = 'non_operating_income'
    NON_OPERATING_EXPENSES = 'non_operating_expenses'
    ORDINARY_INCOME = 'ordinary_income'
    EXTRAORDINARY_INCOME = 'extraordinary_income'
    EXTRAORDINARY_LOSS = 'extraordinary_loss'
    OTHER_INCOME_IFRS = 'other_income_ifrs'
    OTHER_EXPENSES_IFRS = 'other_expenses_ifrs'
    FINANCE_INCOME = 'finance_income'
    FINANCE_COSTS = 'finance_costs'
    EQUITY_METHOD_INCOME_IFRS = 'equity_method_income_ifrs'
    INTEREST_INCOME_PL = 'interest_income_pl'
    INTEREST_EXPENSE_PL = 'interest_expense_pl'
    RD_EXPENSES = 'rd_expenses'
    INCOME_BEFORE_TAX = 'income_before_tax'
    INCOME_TAXES = 'income_taxes'
    INCOME_TAXES_DEFERRED = 'income_taxes_deferred'
    NET_INCOME = 'net_income'
    NET_INCOME_PARENT = 'net_income_parent'
    NET_INCOME_MINORITY = 'net_income_minority'
    DIVIDEND_INCOME = 'dividend_income'
    IMPAIRMENT_LOSS_PL = 'impairment_loss_pl'
    DEPRECIATION_SGA = 'depreciation_sga'

    # === BS（貸借対照表） ===
    CASH_AND_DEPOSITS = 'cash_and_deposits'
    CASH_AND_EQUIVALENTS = 'cash_and_equivalents'
    TRADE_RECEIVABLES = 'trade_receivables'
    NOTES_RECEIVABLE = 'notes_receivable'
    INVENTORIES = 'inventories'
    PREPAID_EXPENSES = 'prepaid_expenses'
    CONTRACT_ASSETS = 'contract_assets'
    CURRENT_ASSETS = 'current_assets'
    NONCURRENT_ASSETS = 'noncurrent_assets'
    PPE = 'ppe'
    LAND = 'land'
    BUILDINGS_NET = 'buildings_net'
    CONSTRUCTION_IN_PROGRESS = 'construction_in_progress'
    INTANGIBLE_ASSETS = 'intangible_assets'
    GOODWILL = 'goodwill'
    INVESTMENT_SECURITIES = 'investment_securities'
    INVESTMENTS_AND_OTHER = 'investments_and_other'
    DEFERRED_ASSETS = 'deferred_assets'
    TOTAL_ASSETS = 'total_assets'
    TRADE_PAYABLES = 'trade_payables'
    NOTES_PAYABLE = 'notes_payable'
    CONTRACT_LIABILITIES = 'contract_liabilities'
    SHORT_TERM_LOANS = 'short_term_loans'
    CURRENT_PORTION_OF_BONDS = 'current_portion_of_bonds'
    CURRENT_PORTION_OF_LONG_TERM_LOANS = 'current_portion_of_long_term_loans'
    PROVISIONS_CL = 'provisions_cl'
    CURRENT_LIABILITIES = 'current_liabilities'
    LONG_TERM_LOANS = 'long_term_loans'
    BONDS_PAYABLE = 'bonds_payable'
    PROVISIONS_NCL = 'provisions_ncl'
    NONCURRENT_LIABILITIES = 'noncurrent_liabilities'
    TOTAL_LIABILITIES = 'total_liabilities'
    CAPITAL_STOCK = 'capital_stock'
    CAPITAL_SURPLUS = 'capital_surplus'
    RETAINED_EARNINGS = 'retained_earnings'
    TREASURY_STOCK = 'treasury_stock'
    SHAREHOLDERS_EQUITY = 'shareholders_equity'
    OCI_ACCUMULATED = 'oci_accumulated'
    SUBSCRIPTION_RIGHTS = 'subscription_rights'
    EQUITY_PARENT = 'equity_parent'
    MINORITY_INTERESTS = 'minority_interests'
    NET_ASSETS = 'net_assets'
    LIABILITIES_AND_NET_ASSETS = 'liabilities_and_net_assets'

    # === CF（キャッシュフロー計算書） ===
    DEPRECIATION_CF = 'depreciation_cf'
    IMPAIRMENT_LOSS_CF = 'impairment_loss_cf'
    GOODWILL_AMORTIZATION_CF = 'goodwill_amortization_cf'
    ALLOWANCE_DOUBTFUL_CHANGE_CF = 'allowance_doubtful_change_cf'
    INTEREST_DIVIDEND_INCOME_CF = 'interest_dividend_income_cf'
    INTEREST_EXPENSE_CF = 'interest_expense_cf'
    FX_LOSS_GAIN_CF = 'fx_loss_gain_cf'
    EQUITY_METHOD_CF = 'equity_method_cf'
    PPE_SALE_LOSS_GAIN_CF = 'ppe_sale_loss_gain_cf'
    TRADE_RECEIVABLES_CHANGE_CF = 'trade_receivables_change_cf'
    INVENTORIES_CHANGE_CF = 'inventories_change_cf'
    TRADE_PAYABLES_CHANGE_CF = 'trade_payables_change_cf'
    OTHER_OPERATING_CF = 'other_operating_cf'
    SUBTOTAL_OPERATING_CF = 'subtotal_operating_cf'
    INCOME_TAXES_PAID_CF = 'income_taxes_paid_cf'
    OPERATING_CF = 'operating_cf'
    PURCHASE_PPE_CF = 'purchase_ppe_cf'
    PROCEEDS_PPE_SALE_CF = 'proceeds_ppe_sale_cf'
    PURCHASE_INVESTMENT_SECURITIES_CF = 'purchase_investment_securities_cf'
    PROCEEDS_INVESTMENT_SECURITIES_CF = 'proceeds_investment_securities_cf'
    LOANS_PAID_CF = 'loans_paid_cf'
    LOANS_COLLECTED_CF = 'loans_collected_cf'
    OTHER_INVESTING_CF = 'other_investing_cf'
    INVESTING_CF = 'investing_cf'
    PROCEEDS_LONG_TERM_LOANS_CF = 'proceeds_long_term_loans_cf'
    REPAYMENT_LONG_TERM_LOANS_CF = 'repayment_long_term_loans_cf'
    PROCEEDS_BONDS_CF = 'proceeds_bonds_cf'
    REDEMPTION_BONDS_CF = 'redemption_bonds_cf'
    PURCHASE_TREASURY_STOCK_CF = 'purchase_treasury_stock_cf'
    DIVIDENDS_PAID_CF = 'dividends_paid_cf'
    OTHER_FINANCING_CF = 'other_financing_cf'
    FINANCING_CF = 'financing_cf'
    FX_EFFECT_ON_CASH = 'fx_effect_on_cash'
    NET_CHANGE_IN_CASH = 'net_change_in_cash'
    CONSOLIDATION_SCOPE_CHANGE_CASH = 'consolidation_scope_change_cash'
    CASH_END = 'cash_end'
    SBC_CF = 'sbc_cf'
    DIVIDENDS_RECEIVED_CF = 'dividends_received_cf'
    DIVIDENDS_PAID_NCI_CF = 'dividends_paid_nci_cf'
    NCI_CAPITAL_CONTRIBUTION_CF = 'nci_capital_contribution_cf'
    SHORT_TERM_BORROWINGS_NET_CF = 'short_term_borrowings_net_cf'

    # === KPI ===
    EPS = 'eps'
    EPS_DILUTED = 'eps_diluted'
    BPS = 'bps'
    DPS = 'dps'
    EQUITY_RATIO = 'equity_ratio'
    ROE = 'roe'
    PER = 'per'
    EMPLOYEES = 'employees'
    INTERIM_DPS = 'interim_dps'
    PAYOUT_RATIO = 'payout_ratio'
    TOTAL_SHARES_ISSUED = 'total_shares_issued'
    EQUITY_METHOD_INCOME = 'equity_method_income'
    CONTINUING_OPERATIONS_INCOME = 'continuing_operations_income'

    # === CI（包括利益） ===
    COMPREHENSIVE_INCOME = 'comprehensive_income'
    COMPREHENSIVE_INCOME_PARENT = 'comprehensive_income_parent'
    COMPREHENSIVE_INCOME_MINORITY = 'comprehensive_income_minority'

    # === 業種特有（銀行・保険） ===
    CAPITAL_ADEQUACY_RATIO_BIS = 'capital_adequacy_ratio_bis'
    CAPITAL_ADEQUACY_RATIO_DOMESTIC = 'capital_adequacy_ratio_domestic'
    CAPITAL_ADEQUACY_RATIO_DOMESTIC_2 = 'capital_adequacy_ratio_domestic_2'
    CAPITAL_ADEQUACY_RATIO_INTERNATIONAL = 'capital_adequacy_ratio_international'
    DEPOSITS = 'deposits'
    LOANS_AND_BILLS_DISCOUNTED = 'loans_and_bills_discounted'
    SECURITIES_BANKING = 'securities_banking'
    NET_PREMIUMS_WRITTEN = 'net_premiums_written'
    INTEREST_DIVIDEND_INCOME_INS = 'interest_dividend_income_ins'
    INVESTMENT_YIELD_INCOME = 'investment_yield_income'
    INVESTMENT_YIELD_REALIZED = 'investment_yield_realized'
    NET_LOSS_RATIO = 'net_loss_ratio'
    NET_OPERATING_EXPENSE_RATIO = 'net_operating_expense_ratio'

    # === ESG・ガバナンス ===
    FEMALE_MANAGERS_RATIO = 'female_managers_ratio'
    GENDER_PAY_GAP = 'gender_pay_gap'
    MALE_CHILDCARE_LEAVE_RATE = 'male_childcare_leave_rate'
    FEMALE_DIRECTORS_RATIO = 'female_directors_ratio'

    # === 追加 BS/PL 詳細 ===
    CAPEX = 'capex'
    INVENTORY_WRITEDOWNS = 'inventory_writedowns'
    AUDIT_FEES = 'audit_fees'
    CROSS_SHAREHOLDINGS_COUNT = 'cross_shareholdings_count'
    CROSS_SHAREHOLDINGS_AMOUNT = 'cross_shareholdings_amount'
    INTEREST_BEARING_DEBT_CL = 'interest_bearing_debt_cl'
    INTEREST_BEARING_DEBT_NCL = 'interest_bearing_debt_ncl'
    INTEREST_BEARING_DEBT = 'interest_bearing_debt'
    LEASE_LIABILITIES_CL = 'lease_liabilities_cl'
    LEASE_LIABILITIES_NCL = 'lease_liabilities_ncl'
    LEASE_LIABILITIES = 'lease_liabilities'
    INVESTMENT_PROPERTY = 'investment_property'
    REAL_ESTATE_FOR_SALE = 'real_estate_for_sale'
    RIGHT_OF_USE_ASSETS = 'right_of_use_assets'
    EQUITY_METHOD_INVESTMENTS = 'equity_method_investments'
    DEFERRED_TAX_ASSETS = 'deferred_tax_assets'
    DEFERRED_TAX_LIABILITIES = 'deferred_tax_liabilities'
    RETIREMENT_BENEFIT_LIABILITY = 'retirement_benefit_liability'
```

TDnet 固有の科目（業績予想の修正率など）がある場合は CK を **拡張** してよい。
ただし edinet 側と重複するキー名・値は絶対に変えないこと。

---

## 3. 期間モデル — 完全コピー対象

```python
import datetime
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class InstantPeriod:
    """時点を表す期間。"""
    instant: datetime.date

@dataclass(frozen=True, slots=True)
class DurationPeriod:
    """期間を表す期間。"""
    start_date: datetime.date
    end_date: datetime.date

Period = InstantPeriod | DurationPeriod
```

---

## 4. ラベルモデル — 完全コピー対象

```python
import enum
from dataclasses import dataclass

class LabelSource(enum.Enum):
    """ラベルの情報源。"""
    STANDARD = 'standard'   # 標準タクソノミ由来
    FILER = 'filer'         # 提出者別タクソノミ由来
    FALLBACK = 'fallback'   # ラベル未発見で local_name を使用

@dataclass(frozen=True, slots=True)
class LabelInfo:
    """解決されたラベル情報。"""
    text: str       # 例: "売上高"
    role: str       # ラベルロール URI
    lang: str       # "ja" / "en"
    source: LabelSource
```

---

## 5. LineItem — 完全コピー対象

XBRL Fact 1件を表す型付きデータ。edinet と同一フィールド・同一型にする。

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

@dataclass(frozen=True, slots=True, kw_only=True)
class LineItem:
    """型付き・ラベル付きの XBRL Fact。"""
    concept: str                           # Clark notation QName: "{ns}NetSales"
    namespace_uri: str                     # 名前空間 URI
    local_name: str                        # "NetSales"
    label_ja: LabelInfo                    # 日本語ラベル
    label_en: LabelInfo                    # 英語ラベル
    value: Decimal | str | None            # 数値→Decimal, テキスト→str, nil→None
    unit_ref: str | None                   # "JPY" 等。テキストは None
    decimals: int | Literal['INF'] | None
    context_id: str                        # contextRef
    period: Period                         # InstantPeriod | DurationPeriod
    entity_id: str
    dimensions: tuple[DimensionMember, ...]
    is_nil: bool
    source_line: int | None
    order: int                             # 元文書内の出現順
```

### DimensionMember（LineItem が依存）

```python
@dataclass(frozen=True, slots=True)
class DimensionMember:
    """Dimension の軸とメンバーの組。"""
    axis: str    # Clark notation: "{namespace}axisName"
    member: str  # Clark notation: "{namespace}memberName"
```

---

## 6. StatementType — 完全コピー対象

```python
import enum

class StatementType(enum.Enum):
    """財務諸表の種類。"""
    INCOME_STATEMENT = 'income_statement'
    BALANCE_SHEET = 'balance_sheet'
    CASH_FLOW_STATEMENT = 'cash_flow_statement'
    STATEMENT_OF_CHANGES_IN_EQUITY = 'statement_of_changes_in_equity'
    COMPREHENSIVE_INCOME = 'comprehensive_income'
```

---

## 7. FinancialStatement — インターフェースコピー対象

組み立て済みの財務諸表。edinet と同じメソッド群を持つこと。

```python
import pandas as pd
from collections.abc import Iterator, Generator
from pathlib import Path

@dataclass(frozen=True, slots=True, kw_only=True)
class FinancialStatement:
    """組み立て済みの財務諸表。"""
    statement_type: StatementType
    period: Period | None
    items: tuple[LineItem, ...]
    consolidated: bool
    entity_id: str
    warnings_issued: tuple[str, ...]

    def __getitem__(self, key: str) -> LineItem:
        """科目を日本語ラベル・英語ラベル・local_name で検索する。

        照合順序:
          1. label_ja.text（例: "売上高"）
          2. label_en.text（例: "Net sales"）
          3. local_name（例: "NetSales"）

        Raises:
            KeyError: マッチする科目が見つからない場合。
        """

    def get(self, key: str, default: LineItem | None = None) -> LineItem | None:
        """科目を検索する。見つからなければ default を返す。"""

    def __contains__(self, key: object) -> bool:
        """科目の存在確認。"売上高" in pl のように使う。"""

    def __len__(self) -> int:
        """科目数を返す。"""

    def __iter__(self) -> Iterator[LineItem]:
        """科目を順に返す。"""

    def to_dict(self) -> list[dict[str, object]]:
        """辞書のリストに変換する。

        各辞書のキー: label_ja, label_en, value, unit, concept
        """

    def to_dataframe(self, *, full: bool = False) -> pd.DataFrame:
        """pandas DataFrame に変換する。

        デフォルト（full=False）のカラム:
          - label_ja: str
          - label_en: str
          - value: Decimal | str | None
          - unit: str | None
          - concept: str

        full=True の場合: context_id, period_type, dimensions 等も含む。
        DataFrame.attrs に statement_type, consolidated, period, entity_id を付与。
        """

    def to_csv(self, path: str | Path, **kwargs) -> None:
        """全カラム DataFrame を CSV に出力する。"""

    def to_parquet(self, path: str | Path, **kwargs) -> None:
        """全カラム DataFrame を Parquet に出力する。"""

    def to_excel(self, path: str | Path, **kwargs) -> None:
        """全カラム DataFrame を Excel に出力する。"""
```

### 重要: `__getitem__` の照合順序

ユーザーが最も多用するインターフェース。以下の順で照合すること:

1. `label_ja.text` 完全一致
2. `label_en.text` 完全一致
3. `local_name` 完全一致

```python
# ユーザーコード例（edinet でも tdnet でも同じ）
revenue = pl["売上高"]
total_assets = bs["TotalAssets"]
print(revenue.value)  # Decimal('100000000000')
```

---

## 8. Statements コンテナ — インターフェースコピー対象

`Filing.xbrl()` に相当するメソッドの戻り値。メソッド名・引数名を揃える。

```python
class Statements:
    """財務諸表コンテナ。"""

    def income_statement(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | Literal['current', 'prior'] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """損益計算書を組み立てる。

        Args:
            consolidated: True→連結、False→個別。
            period: "current"/"prior" で当期/前期を自動選択。None→最新。
            strict: True→フォールバックせず空を返す。
        """

    def balance_sheet(
        self,
        *,
        consolidated: bool = True,
        period: InstantPeriod | Literal['current', 'prior'] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """貸借対照表を組み立てる。"""

    def cash_flow_statement(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | Literal['current', 'prior'] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """キャッシュフロー計算書を組み立てる。"""

    def equity_statement(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | Literal['current', 'prior'] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """株主資本等変動計算書を組み立てる。"""

    def comprehensive_income(
        self,
        *,
        consolidated: bool = True,
        period: DurationPeriod | Literal['current', 'prior'] | None = None,
        strict: bool = False,
    ) -> FinancialStatement:
        """包括利益計算書を組み立てる。"""

    # --- ユーティリティ ---

    def __getitem__(self, key: str) -> LineItem:
        """全科目から検索（照合順序は FinancialStatement と同じ）。"""

    def get(self, key: str, default: LineItem | None = None) -> LineItem | None:
        """科目を検索。見つからなければ default。"""

    def __contains__(self, key: object) -> bool:
        """科目の存在確認。"""

    def __len__(self) -> int:
        """全科目数。"""

    def __iter__(self) -> Iterator[LineItem]:
        """全科目を順に返す。"""

    def search(self, keyword: str) -> list[LineItem]:
        """キーワードで部分一致検索。大文字小文字区別なし（英語）。"""

    def to_dataframe(self) -> pd.DataFrame:
        """全 LineItem を全カラム DataFrame に変換する。"""

    def to_csv(self, path: str | Path, **kwargs) -> None: ...
    def to_parquet(self, path: str | Path, **kwargs) -> None: ...
    def to_excel(self, path: str | Path, **kwargs) -> None: ...
```

---

## 9. extract_values / ExtractedValue — インターフェースコピー対象

CK を使った正規化キーベースの値抽出。

```python
@dataclass(frozen=True, slots=True)
class ExtractedValue:
    """正規化キーで抽出された財務数値。"""
    canonical_key: str              # CK の値（例: "revenue"）
    value: Decimal | str | None     # 抽出された値
    item: LineItem                  # 元の LineItem（トレーサビリティ）
    mapper_name: str | None         # 値を採用したマッパー名

def extract_values(
    source: Statements,
    keys: Sequence[str] | None = None,
    *,
    period: Literal['current', 'prior'] | None = None,
    consolidated: bool | None = None,
    mapper: ConceptMapper | Sequence[ConceptMapper] | None = None,
) -> dict[str, ExtractedValue | None]:
    """正規化キーで値を抽出する。

    Args:
        source: Statements コンテナ。
        keys: 抽出する CK のリスト。None→全科目。
        period: "current"/"prior"/None。
        consolidated: True/False/None。
        mapper: カスタムマッパー。None→デフォルトパイプライン。
    """

def extracted_to_dict(
    *extracted_dicts: dict[str, ExtractedValue | None],
) -> dict[str, Decimal | str | None]:
    """extract_values() の結果を {key: value} 辞書に変換する。"""
```

### ConceptMapper プロトコル

```python
# ConceptMapper = Callable[[LineItem, MapperContext], str | None]
# item を受け取り、マッチした canonical_key を返す。マッチしなければ None。
```

---

## 10. 例外・警告 — 命名規則を揃える

```python
class TdnetWarning(UserWarning):
    """tdnet ライブラリが発行する warning の基底クラス。"""

class TdnetError(Exception):
    """tdnet ライブラリの基底例外。"""

class TdnetConfigError(TdnetError):
    """設定に関するエラー。"""

class TdnetAPIError(TdnetError):
    """TDnet からのエラー。"""
    status_code: int
    def __init__(self, status_code: int, message: str) -> None: ...

class TdnetParseError(TdnetError):
    """取得済みデータの解析に失敗した。"""
```

---

## 11. configure() — 構造を揃える

```python
def configure(
    *,
    taxonomy_path: str | None = ...,  # TDnet タクソノミパス
    cache_dir: str | None = ...,      # キャッシュディレクトリ
    timeout: float = ...,
    max_retries: int = ...,
    # TDnet 固有の設定があればここに追加
) -> None:
    """ライブラリのグローバル設定を更新する。"""
```

---

## 12. TDnet 固有のインターフェース（edinet にはないもの）

以下は edinet には存在しないが、TDnet ライブラリで独自に設計するもの。
ただし `Filing.xbrl()` → `Statements` の出力型は上記に従うこと。

### Filing（TDnet 固有）

TDnet の開示書類。メタデータは TDnet の仕様に従う。
ただし **`xbrl()` メソッドの戻り値は `Statements`** にすること。

```python
class Filing:
    """TDnet の開示書類 1 件。"""
    # フィールドは TDnet の仕様に合わせて自由に設計

    def xbrl(self, *, taxonomy_path: str | None = None) -> Statements:
        """XBRL を解析し財務諸表コンテナを返す。

        Returns:
            Statements コンテナ。income_statement() / balance_sheet() /
            cash_flow_statement() でアクセスする。
        """
```

### 決算短信特有の項目

TDnet の決算短信には edinet にはない項目がある。CK を拡張して対応する:

```python
class CK(StrEnum):
    # ... (edinet と共通の全キーをそのまま含む) ...

    # === TDnet 固有（業績予想等） ===
    FORECAST_REVENUE = 'forecast_revenue'
    FORECAST_OPERATING_INCOME = 'forecast_operating_income'
    FORECAST_ORDINARY_INCOME = 'forecast_ordinary_income'
    FORECAST_NET_INCOME_PARENT = 'forecast_net_income_parent'
    FORECAST_EPS = 'forecast_eps'
    FORECAST_DPS = 'forecast_dps'
    # 修正率
    REVISION_RATE_REVENUE = 'revision_rate_revenue'
    REVISION_RATE_OPERATING_INCOME = 'revision_rate_operating_income'
    # ... 必要に応じて追加
```

---

## 13. ユーザーコード例（EDINET と TDnet で共通）

```python
# --- edinet ---
import edinet

edinet.configure(api_key="xxx", taxonomy_path="/path/to/taxonomy")
filings = edinet.documents(date="2026-03-01", doc_type="有価証券報告書")
stmts = filings[0].xbrl()

# --- tdnet ---
import tdnet

filings = tdnet.documents(date="2026-03-01")  # API が違うので引数は異なってよい
stmts = filings[0].xbrl()

# --- ここから下は完全に同じコード ---
pl = stmts.income_statement(consolidated=True)
bs = stmts.balance_sheet()
cf = stmts.cash_flow_statement()

# ラベルでアクセス
revenue = pl["売上高"]
print(f"売上高: {revenue.value:,}")

# CK でアクセス
from tdnet import CK  # or from edinet import CK（同じ値）
result = extract_values(stmts, [CK.REVENUE, CK.OPERATING_INCOME, CK.NET_INCOME_PARENT])
row = extracted_to_dict(result)
print(row["revenue"])

# DataFrame
df = pl.to_dataframe()
df[df["value"] > 0]

# "売上高" in pl → True
if "営業利益" in pl:
    print(pl["営業利益"].value)
```

---

## 14. 合わせなくてよいもの（参考）

| 項目 | 理由 |
|---|---|
| `documents()` の引数 | TDnet の API が違う |
| `DocType` | TDnet 固有の書類種別 |
| `OrdinanceCode`, `FormCode` | EDINET 固有 |
| `DEI` | EDINET XBRL 固有のメタデータ |
| `Company.search()`, `Company.from_edinet_code()` | データソースが違う |
| `RevisionChain`, `build_revision_chain` | EDINET 固有の訂正報告書体系 |
| XBRL パーサー内部 | タクソノミが違う |

---

## 15. まとめ: コピー優先度

| 優先度 | 対象 | 方法 |
|---|---|---|
| **必須** | `CK` | 完全コピー + TDnet 固有キー追加 |
| **必須** | `Period`, `InstantPeriod`, `DurationPeriod` | 完全コピー |
| **必須** | `LabelInfo`, `LabelSource` | 完全コピー |
| **必須** | `DimensionMember` | 完全コピー |
| **必須** | `LineItem` | 完全コピー |
| **必須** | `StatementType` | 完全コピー |
| **必須** | `FinancialStatement` | インターフェースコピー |
| **強く推奨** | `Statements` のメソッド名・引数名 | インターフェースコピー |
| **強く推奨** | `ExtractedValue`, `extract_values()` | インターフェースコピー |
| **推奨** | 例外クラス階層 | 命名規則コピー |
| **推奨** | `configure()` の構造 | 構造コピー |
| 不要 | `Filing`, `documents()`, `DocType` 等 | TDnet 固有設計 |
