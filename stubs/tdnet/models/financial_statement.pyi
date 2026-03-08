import pandas as pd
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from tdnet.models.statement_type import StatementType as StatementType
from tdnet.models.types import LineItem as LineItem
from xbrl_core.periods import Period as Period

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
          1. label_ja.text
          2. label_en.text
          3. local_name
        """
    def get(self, key: str, default: LineItem | None = None) -> LineItem | None:
        """科目を検索する。見つからなければ default を返す。"""
    def __contains__(self, key: object) -> bool: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[LineItem]: ...
    def to_dict(self) -> list[dict[str, object]]:
        """辞書のリストに変換する。"""
    def to_dataframe(self, *, full: bool = False) -> pd.DataFrame:
        """pandas DataFrame に変換する。

        ``value`` 列は数値（float）のみ。文字列値は ``value_text`` 列に格納される。
        Decimal → float 変換済み（parquet/arrow 互換）。
        """
    def to_csv(self, path: str | Path, **kwargs: object) -> None:
        """全カラム DataFrame を CSV に出力する。"""
    def to_parquet(self, path: str | Path, **kwargs: object) -> None:
        """全カラム DataFrame を Parquet に出力する。"""
    def to_excel(self, path: str | Path, **kwargs: object) -> None:
        """全カラム DataFrame を Excel に出力する。"""
