from tdnet._config import configure as configure
from tdnet._version import __version__ as __version__
from tdnet.api import list_by_code as list_by_code, list_by_date as list_by_date, list_by_range as list_by_range, list_recent as list_recent, search as search
from tdnet.exceptions import TdnetAPIError as TdnetAPIError, TdnetConfigError as TdnetConfigError, TdnetError as TdnetError, TdnetParseError as TdnetParseError, TdnetWarning as TdnetWarning
from tdnet.filing import DownloadResult as DownloadResult, Filing as Filing
from tdnet.mapper import ConceptMapper as ConceptMapper, MapperContext as MapperContext, build_parent_index as build_parent_index, calc_mapper as calc_mapper, definition_mapper as definition_mapper, dict_mapper as dict_mapper, dividend_mapper as dividend_mapper, forecast_mapper as forecast_mapper, statement_mapper as statement_mapper, summary_mapper as summary_mapper
from tdnet.models.ck import CK as CK
from tdnet.models.extract import ExtractedValue as ExtractedValue, extract_values as extract_values, extracted_to_dict as extracted_to_dict
from tdnet.models.financial_statement import FinancialStatement as FinancialStatement
from tdnet.models.statement_type import StatementType as StatementType
from tdnet.models.statements import Statements as Statements
from tdnet.models.types import LabelInfo as LabelInfo, LabelSource as LabelSource, LineItem as LineItem
from tdnet.xbrl.parser import parse_ixbrl_files as parse_ixbrl_files, parse_zip as parse_zip
from xbrl_core import DimensionMember as DimensionMember, DurationPeriod as DurationPeriod, InstantPeriod as InstantPeriod, Period as Period

__all__ = ['__version__', 'configure', 'TdnetWarning', 'TdnetError', 'TdnetConfigError', 'TdnetAPIError', 'TdnetParseError', 'LineItem', 'LabelInfo', 'LabelSource', 'DimensionMember', 'InstantPeriod', 'DurationPeriod', 'Period', 'CK', 'StatementType', 'FinancialStatement', 'Statements', 'ExtractedValue', 'extract_values', 'extracted_to_dict', 'ConceptMapper', 'MapperContext', 'build_parent_index', 'calc_mapper', 'definition_mapper', 'dict_mapper', 'dividend_mapper', 'forecast_mapper', 'statement_mapper', 'summary_mapper', 'parse_zip', 'parse_ixbrl_files', 'Filing', 'DownloadResult', 'documents', 'list_by_date', 'list_recent', 'list_by_code', 'list_by_range', 'search']

def documents(target_date: str | None = None, *, code: str | int | None = None, has_xbrl: bool = False, limit: int = 300, source: str = 'yanoshin') -> list[Filing]:
    '''開示書類一覧を取得する。

    Args:
        target_date: 日付文字列 (YYYYMMDD or YYYY-MM-DD) または None (最新)。
        code: 証券コードで絞り込み。
        has_xbrl: True で XBRL 付きのみ。
        limit: 最大取得件数。
        source: データソース ("yanoshin" or "scrape")。

    Returns:
        Filing のリスト。
    '''
