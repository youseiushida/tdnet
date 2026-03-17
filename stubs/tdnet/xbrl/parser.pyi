from _typeshed import Incomplete
from pathlib import Path
from tdnet.models.statements import Statements as Statements
from tdnet.models.types import convert_line_item as convert_line_item
from tdnet.xbrl.taxonomy import TdnetLabelResolver as TdnetLabelResolver
from xbrl_core import ParsedXBRL as ParsedXBRL, RawLabel as RawLabel

logger: Incomplete

def parse_zip(zip_data: bytes, *, taxonomy_path: str | Path | None = None, entity_id: str = '') -> Statements:
    """XBRL ZIP を解析して Statements を返す。

    ZIP 内のリンクベース（lab/def/cal/pre）を自動抽出し、
    filer ラベルの注入および definition/calculation/presentation
    リンクベースの解析を行う。

    Args:
        zip_data: ZIP ファイルのバイト列。
        taxonomy_path: タクソノミのパス。None の場合はバンドルを使用。
        entity_id: エンティティ ID。

    Returns:
        Statements コンテナ。
    """
def parse_ixbrl_files(files: dict[str, bytes], *, taxonomy_path: str | Path | None = None, entity_id: str = '', filer_labels: tuple[RawLabel, ...] | None = None) -> Statements:
    """複数の iXBRL ファイルを解析して Statements を返す。

    Args:
        files: ファイル名をキー、iXBRL bytes を値とする辞書。
        taxonomy_path: タクソノミのパス。
        entity_id: エンティティ ID。
        filer_labels: ZIP 内ラベルリンクベースからパースした filer ラベル。

    Returns:
        Statements コンテナ。
    """
