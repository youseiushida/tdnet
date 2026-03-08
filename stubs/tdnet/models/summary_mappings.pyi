from dataclasses import dataclass

__all__ = ['SummaryMapping', 'all_summary_mappings', 'lookup_summary', 'validate_against_xsd']

@dataclass(frozen=True, slots=True)
class SummaryMapping:
    """TDnet サマリー科目の CK マッピング。"""
    concept: str
    canonical_key: str

def lookup_summary(concept: str) -> str | None:
    """TDnet サマリー concept から CK を返す。"""
def all_summary_mappings() -> tuple[SummaryMapping, ...]:
    """XSD に実在する全 SummaryMapping を返す。"""
def validate_against_xsd(xsd_path: str | None = None) -> list[str]:
    """マッピングの全 concept が XSD に実在するか検証する。

    エイリアス（_ALIASES）は検証対象外。

    Args:
        xsd_path: tse-ed-t XSD のパス。None の場合はバンドルを検索。

    Returns:
        XSD に存在しない concept 名のリスト（空なら全OK）。
    """
