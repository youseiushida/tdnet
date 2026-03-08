"""Parquet 永続化: Filing + Statements のシリアライズ/デシリアライズ。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tdnet.filing import Filing
    from tdnet.models.statements import Statements

__all__ = ["to_parquet", "from_parquet"]


def to_parquet(
    data: Sequence[tuple[Filing, Statements | None]],
    path: str | Path,
) -> None:
    """Filing + Statements を Parquet に永続化する。

    ``{path}/filings.parquet`` と ``{path}/line_items.parquet`` を出力する。

    Args:
        data: (Filing, Statements | None) のシーケンス。
        path: 出力先ディレクトリ。
    """
    import pandas as pd

    from tdnet.extension._serialize import _filing_rows, _line_item_rows

    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)

    filings_df = pd.DataFrame(_filing_rows(data))
    items_df = pd.DataFrame(_line_item_rows(data))

    filings_df.to_parquet(out / "filings.parquet", index=False)
    items_df.to_parquet(out / "line_items.parquet", index=False)


def from_parquet(
    path: str | Path,
) -> list[tuple[Filing, Statements | None]]:
    """Parquet から Filing + Statements を復元する。

    Args:
        path: ``filings.parquet`` と ``line_items.parquet`` が格納されたディレクトリ。

    Returns:
        (Filing, Statements | None) のリスト。
    """
    import pandas as pd

    from tdnet.extension._deserialize import _restore_filings_and_statements

    p = Path(path)
    filings_df = pd.read_parquet(p / "filings.parquet")
    items_path = p / "line_items.parquet"
    if items_path.exists():
        items_df = pd.read_parquet(items_path)
    else:
        items_df = pd.DataFrame()

    return _restore_filings_and_statements(filings_df, items_df)
