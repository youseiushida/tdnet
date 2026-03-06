"""組み立て済みの財務諸表。"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from xbrl_core.periods import Period

from tdnet.models.statement_type import StatementType
from tdnet.models.types import LineItem

if TYPE_CHECKING:
    import pandas as pd


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
        for item in self.items:
            if item.label_ja.text == key:
                return item
        for item in self.items:
            if item.label_en.text == key:
                return item
        for item in self.items:
            if item.local_name == key:
                return item
        raise KeyError(key)

    def get(self, key: str, default: LineItem | None = None) -> LineItem | None:
        """科目を検索する。見つからなければ default を返す。"""
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return self.get(key) is not None

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[LineItem]:
        return iter(self.items)

    def to_dict(self) -> list[dict[str, object]]:
        """辞書のリストに変換する。"""
        result: list[dict[str, object]] = []
        for item in self.items:
            result.append({
                "label_ja": item.label_ja.text,
                "label_en": item.label_en.text,
                "value": item.value,
                "unit": item.unit_ref,
                "concept": item.concept,
            })
        return result

    def to_dataframe(self, *, full: bool = False) -> pd.DataFrame:
        """pandas DataFrame に変換する。

        ``value`` 列は数値（float）のみ。文字列値は ``value_text`` 列に格納される。
        Decimal → float 変換済み（parquet/arrow 互換）。
        """
        import pandas as pd
        from decimal import Decimal

        rows: list[dict[str, object]] = []
        for item in self.items:
            raw = item.value
            if isinstance(raw, Decimal):
                num_val: float | None = float(raw)
                text_val: str | None = None
            elif isinstance(raw, str):
                num_val = None
                text_val = raw
            else:
                num_val = None
                text_val = None
            row: dict[str, object] = {
                "label_ja": item.label_ja.text,
                "label_en": item.label_en.text,
                "value": num_val,
                "value_text": text_val,
                "unit": item.unit_ref,
                "concept": item.concept,
            }
            if full:
                row["context_id"] = item.context_id
                row["local_name"] = item.local_name
                row["namespace_uri"] = item.namespace_uri
                row["decimals"] = item.decimals
                row["is_nil"] = item.is_nil
                row["order"] = item.order
                row["period"] = str(item.period)
                dims = "; ".join(f"{d.axis}={d.member}" for d in item.dimensions)
                row["dimensions"] = dims if dims else ""
            rows.append(row)

        df = pd.DataFrame(rows)
        df.attrs["statement_type"] = self.statement_type.value
        df.attrs["consolidated"] = self.consolidated
        df.attrs["period"] = str(self.period) if self.period else None
        df.attrs["entity_id"] = self.entity_id
        return df

    def _full_dataframe(self) -> pd.DataFrame:
        return self.to_dataframe(full=True)

    def to_csv(self, path: str | Path, **kwargs: object) -> None:
        """全カラム DataFrame を CSV に出力する。"""
        self._full_dataframe().to_csv(str(path), index=False, **kwargs)  # type: ignore[arg-type]

    def to_parquet(self, path: str | Path, **kwargs: object) -> None:
        """全カラム DataFrame を Parquet に出力する。"""
        self._full_dataframe().to_parquet(str(path), index=False, **kwargs)  # type: ignore[arg-type]

    def to_excel(self, path: str | Path, **kwargs: object) -> None:
        """全カラム DataFrame を Excel に出力する。"""
        self._full_dataframe().to_excel(str(path), index=False, **kwargs)  # type: ignore[arg-type]
