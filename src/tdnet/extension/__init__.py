"""Parquet 永続化: Filing + Statements のシリアライズ/デシリアライズ。"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tdnet.filing import Filing
    from tdnet.models.statements import Statements

__all__ = ["export_parquet", "import_parquet", "to_parquet", "from_parquet"]


def export_parquet(
    data: Sequence[tuple[Filing, Statements | None]],
    path: str | Path,
    *,
    prefix: str = "",
) -> None:
    """Filing + Statements を Parquet に永続化する。

    ``{path}/{prefix}filings.parquet`` と
    ``{path}/{prefix}line_items.parquet`` を出力する。

    Args:
        data: (Filing, Statements | None) のシーケンス。
        path: 出力先ディレクトリ。
        prefix: 出力ファイル名の先頭に付与する文字列。
            例: ``prefix="2026-03-06_"`` →
            ``2026-03-06_filings.parquet``。
    """
    import pandas as pd

    from tdnet.extension._serialize import _filing_rows, _line_item_rows

    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)

    filings_df = pd.DataFrame(_filing_rows(data))
    items_df = pd.DataFrame(_line_item_rows(data))

    filings_df.to_parquet(out / f"{prefix}filings.parquet", index=False)
    items_df.to_parquet(out / f"{prefix}line_items.parquet", index=False)


def import_parquet(
    path: str | Path,
    *,
    prefix: str = "",
) -> list[tuple[Filing, Statements | None]]:
    """Parquet から Filing + Statements を復元する。

    Args:
        path: Parquet ファイルが格納されたディレクトリ。
        prefix: ``export_parquet`` で指定した prefix と同じ値。

    Returns:
        (Filing, Statements | None) のリスト。
    """
    import pandas as pd

    from tdnet.extension._deserialize import _restore_filings_and_statements

    p = Path(path)
    filings_df = pd.read_parquet(p / f"{prefix}filings.parquet")
    items_path = p / f"{prefix}line_items.parquet"
    if items_path.exists():
        items_df = pd.read_parquet(items_path)
    else:
        items_df = pd.DataFrame()

    return _restore_filings_and_statements(filings_df, items_df)


# ---------------------------------------------------------------------------
# 非推奨エイリアス
# ---------------------------------------------------------------------------

def to_parquet(
    data: Sequence[tuple[Filing, Statements | None]],
    path: str | Path,
    *,
    prefix: str = "",
) -> None:
    """``export_parquet`` の非推奨エイリアス。"""
    warnings.warn(
        "to_parquet() は非推奨です。export_parquet() を使用してください。",
        DeprecationWarning,
        stacklevel=2,
    )
    export_parquet(data, path, prefix=prefix)


def from_parquet(
    path: str | Path,
    *,
    prefix: str = "",
) -> list[tuple[Filing, Statements | None]]:
    """``import_parquet`` の非推奨エイリアス。"""
    warnings.warn(
        "from_parquet() は非推奨です。import_parquet() を使用してください。",
        DeprecationWarning,
        stacklevel=2,
    )
    return import_parquet(path, prefix=prefix)
