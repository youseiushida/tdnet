"""tdnet XBRL 解析モジュール。"""

from tdnet.xbrl.parser import parse_zip, parse_ixbrl_files
from tdnet.xbrl.taxonomy import TdnetLabelResolver

__all__ = ["parse_zip", "parse_ixbrl_files", "TdnetLabelResolver"]
