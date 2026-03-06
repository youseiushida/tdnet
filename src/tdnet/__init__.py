"""tdnet — TDnet 適時開示情報の Python ライブラリ。"""

from tdnet._version import __version__
from tdnet._config import configure
from tdnet.exceptions import (
    TdnetWarning,
    TdnetError,
    TdnetConfigError,
    TdnetAPIError,
    TdnetParseError,
)
from tdnet.models.ck import CK
from tdnet.models.statement_type import StatementType
from tdnet.models.extract import ExtractedValue, extract_values, extracted_to_dict
from tdnet.mapper import (
    ConceptMapper,
    MapperContext,
    dividend_mapper,
    forecast_mapper,
    summary_mapper,
    statement_mapper,
    dict_mapper,
)
from tdnet.filing import Filing
from tdnet.api import (
    list_by_date,
    list_recent,
    list_by_code,
    list_by_range,
    search,
)

# 公開型（edinet 互換）
from tdnet.models.types import (
    LineItem,
    LabelInfo,
    LabelSource,
)

# xbrl_core からの型の再エクスポート（Period / Dimension は共通）
from xbrl_core import (
    DimensionMember,
    InstantPeriod,
    DurationPeriod,
    Period,
)

from tdnet.models.financial_statement import FinancialStatement
from tdnet.models.statements import Statements


def documents(
    target_date: str | None = None,
    *,
    code: str | int | None = None,
    has_xbrl: bool = False,
    limit: int = 300,
    source: str = "yanoshin",
) -> list[Filing]:
    """開示書類一覧を取得する。

    Args:
        target_date: 日付文字列 (YYYYMMDD or YYYY-MM-DD) または None (最新)。
        code: 証券コードで絞り込み。
        has_xbrl: True で XBRL 付きのみ。
        limit: 最大取得件数。
        source: データソース ("yanoshin" or "scrape")。

    Returns:
        Filing のリスト。
    """
    if source == "yanoshin":
        if code is not None:
            items = list_by_code(code, has_xbrl=has_xbrl, limit=limit)
        elif target_date is not None:
            date_str = target_date.replace("-", "")
            items = list_by_date(date_str, has_xbrl=has_xbrl, limit=limit)
        else:
            items = list_recent(has_xbrl=has_xbrl, limit=limit)
        return [Filing.from_yanoshin(item) for item in items]
    elif source == "scrape":
        from tdnet.api import _scrape_list_page

        if target_date is None:
            from datetime import date as _date
            target_date = _date.today().strftime("%Y%m%d")
        date_str = target_date.replace("-", "")
        items = _scrape_list_page(date_str)
        return [Filing.from_scrape(item) for item in items]
    else:
        raise ValueError(f"Unknown source: {source!r}. Use 'yanoshin' or 'scrape'.")


__all__ = [
    # 設定
    "__version__",
    "configure",
    # 例外
    "TdnetWarning",
    "TdnetError",
    "TdnetConfigError",
    "TdnetAPIError",
    "TdnetParseError",
    # データモデル（xbrl_core 由来）
    "LineItem",
    "LabelInfo",
    "LabelSource",
    "DimensionMember",
    "InstantPeriod",
    "DurationPeriod",
    "Period",
    # データモデル（tdnet 独自）
    "CK",
    "StatementType",
    "FinancialStatement",
    "Statements",
    "ExtractedValue",
    "extract_values",
    "extracted_to_dict",
    # マッパー
    "ConceptMapper",
    "MapperContext",
    "dividend_mapper",
    "forecast_mapper",
    "summary_mapper",
    "statement_mapper",
    "dict_mapper",
    # ファイリング
    "Filing",
    "documents",
    # API
    "list_by_date",
    "list_recent",
    "list_by_code",
    "list_by_range",
    "search",
]
