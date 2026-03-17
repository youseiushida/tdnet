from _typeshed import Incomplete
from collections.abc import Sequence
from pathlib import Path
from xbrl_core import LabelInfo, RawLabel

logger: Incomplete

def bundled_xsd_path() -> Path | None:
    """パッケージ同梱の tse-ed-t XSD パスを返す。"""

class TdnetLabelResolver:
    """TDnet タクソノミのラベルリゾルバ。

    LabelResolver プロトコルを満たす。
    複数のタクソノミ名前空間（tse-ed-t, tse-atcrp-t 等）のラベルを統合的に解決する。
    """
    def __init__(self, taxonomy_path: str | Path | None = None) -> None: ...
    def inject_filer_labels(self, raw_labels: tuple[RawLabel, ...]) -> None:
        """ZIP 内 lab.xml からパースした filer ラベルを注入する。"""
    def resolve(self, concept_qname: str, lang: str, role: str = ...) -> LabelInfo | None:
        """ラベルを解決する。Clark notation の完全一致→ local_name フォールバック。"""
    def resolve_batch(self, concept_qnames: Sequence[str], lang: str, role: str = ...) -> dict[str, LabelInfo | None]: ...
