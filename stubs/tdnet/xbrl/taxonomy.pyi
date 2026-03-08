from _typeshed import Incomplete
from pathlib import Path
from xbrl_core import LabelInfo

logger: Incomplete

def bundled_xsd_path() -> Path | None:
    """パッケージ同梱の tse-ed-t XSD パスを返す。"""

class TdnetLabelResolver:
    """TDnet タクソノミのラベルリゾルバ。

    LabelResolver プロトコルを満たす。
    複数のタクソノミ名前空間（tse-ed-t, tse-atcrp-t 等）のラベルを統合的に解決する。
    """
    def __init__(self, taxonomy_path: str | Path | None = None) -> None: ...
    def resolve(self, concept_qname: str, lang: str, role: str = ...) -> LabelInfo | None: ...
    def resolve_batch(self, concept_qnames: list[str] | tuple[str, ...], lang: str, role: str = ...) -> dict[str, LabelInfo | None]: ...
