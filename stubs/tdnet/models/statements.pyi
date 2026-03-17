import pandas as pd
from collections.abc import Iterator
from pathlib import Path
from tdnet.models.financial_statement import FinancialStatement as FinancialStatement
from tdnet.models.statement_type import StatementType as StatementType
from tdnet.models.types import LineItem as LineItem
from typing import Literal
from xbrl_core import CalculationLinkbase as CalculationLinkbase, DefinitionTree as DefinitionTree, PresentationTree as PresentationTree
from xbrl_core.periods import DurationPeriod, InstantPeriod, Period as Period

class Statements:
    """財務諸表コンテナ。"""
    def __init__(self, items: tuple[LineItem, ...], *, entity_id: str = '', warnings: tuple[str, ...] = (), definition_linkbase: dict[str, DefinitionTree] | None = None, calculation_linkbase: CalculationLinkbase | None = None, presentation_linkbase: dict[str, PresentationTree] | None = None) -> None: ...
    def income_statement(self, *, consolidated: bool = True, period: DurationPeriod | Literal['current', 'prior'] | None = None, strict: bool = False) -> FinancialStatement:
        """損益計算書を組み立てる。"""
    def balance_sheet(self, *, consolidated: bool = True, period: InstantPeriod | Literal['current', 'prior'] | None = None, strict: bool = False) -> FinancialStatement:
        """貸借対照表を組み立てる。"""
    def cash_flow_statement(self, *, consolidated: bool = True, period: DurationPeriod | Literal['current', 'prior'] | None = None, strict: bool = False) -> FinancialStatement:
        """キャッシュフロー計算書を組み立てる。"""
    def equity_statement(self, *, consolidated: bool = True, period: DurationPeriod | Literal['current', 'prior'] | None = None, strict: bool = False) -> FinancialStatement:
        """株主資本等変動計算書を組み立てる。"""
    def comprehensive_income(self, *, consolidated: bool = True, period: DurationPeriod | Literal['current', 'prior'] | None = None, strict: bool = False) -> FinancialStatement:
        """包括利益計算書を組み立てる。"""
    def __getitem__(self, key: str) -> LineItem:
        """全科目から検索。"""
    def get(self, key: str, default: LineItem | None = None) -> LineItem | None: ...
    def __contains__(self, key: object) -> bool: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[LineItem]: ...
    def search(self, keyword: str) -> list[LineItem]:
        """キーワードで部分一致検索。"""
    def to_dataframe(self) -> pd.DataFrame:
        """全 LineItem を全カラム DataFrame に変換する。

        ``value`` 列は数値（float）のみ。文字列値は ``value_text`` 列に格納される。
        Decimal → float 変換済み（parquet/arrow 互換）。
        """
    def to_csv(self, path: str | Path, **kwargs: object) -> None: ...
    def to_parquet(self, path: str | Path, **kwargs: object) -> None: ...
    def to_excel(self, path: str | Path, **kwargs: object) -> None: ...
