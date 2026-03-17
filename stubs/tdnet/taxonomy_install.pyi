from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class TaxonomyInfo:
    """インストール済みタクソノミの情報。"""
    year: int
    folder_name: str
    path: Path
    configured: bool

def list_taxonomy_versions() -> list[int]:
    """ダウンロード可能なタクソノミ年度の一覧を返す。"""
def taxonomy_info() -> TaxonomyInfo | None:
    """インストール済みタクソノミの情報を返す。"""
def install_taxonomy(year: int | None = None, *, force: bool = False, timeout: float = 120.0) -> TaxonomyInfo:
    """EDINET タクソノミをダウンロードしてインストールする。"""
def uninstall_taxonomy(year: int | None = None) -> bool:
    """インストール済みタクソノミを削除する。"""
def detect_installed_taxonomy() -> str | None:
    """インストール済みタクソノミのパスを自動検出する。"""
