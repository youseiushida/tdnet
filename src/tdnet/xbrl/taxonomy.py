"""TDnet タクソノミのラベル解決。"""

from __future__ import annotations

import importlib.resources
import logging
from pathlib import Path

from xbrl_core import LabelInfo, LabelSource
from xbrl_core.linkbase.label import parse_label_linkbase

logger = logging.getLogger(__name__)

# ラベルロール
_STANDARD_ROLE = "http://www.xbrl.org/2003/role/label"

# プレフィックス → 名前空間のマッピング
_PREFIX_NS: dict[str, str] = {
    "tse-ed-t": "http://www.xbrl.tdnet.info/taxonomy/jp/tse/tdnet/ed/t/2014-01-12",
    "tse-atcrp-t": "http://www.xbrl.tdnet.info/taxonomy/jp/tse/tdnet/atcrp/2025-01-31",
    "tse-atpfs-t": "http://www.xbrl.tdnet.info/taxonomy/jp/tse/tdnet/atpfs/2025-01-31",
    "tse-atigp-t": "http://www.xbrl.tdnet.info/taxonomy/jp/tse/tdnet/atigp/2025-01-31",
    "tse-t-cg": "http://www.xbrl.tdnet.info/taxonomy/jp/tse/tdnet/cg/2007-06-30",
}


def _bundled_taxonomy_path() -> Path | None:
    """パッケージ同梱のタクソノミパスを返す。"""
    try:
        ref = importlib.resources.files("tdnet.data.taxonomy")
        p = Path(str(ref / "tse-ed"))
        if p.exists():
            return p.parent
    except Exception:
        pass
    return None


def bundled_xsd_path() -> Path | None:
    """パッケージ同梱の tse-ed-t XSD パスを返す。"""
    try:
        ref = importlib.resources.files("tdnet.data.taxonomy")
        p = Path(
            str(ref / "tse-ed" / "tse-ed-2014-01-12" / "taxonomy"
                / "jp" / "tse" / "tdnet" / "ed" / "t" / "2014-01-12"
                / "tse-ed-t-2014-01-12.xsd")
        )
        if p.exists():
            return p
    except Exception:
        pass
    return None


class TdnetLabelResolver:
    """TDnet タクソノミのラベルリゾルバ。

    LabelResolver プロトコルを満たす。
    複数のタクソノミ名前空間（tse-ed-t, tse-atcrp-t 等）のラベルを統合的に解決する。
    """

    def __init__(self, taxonomy_path: str | Path | None = None) -> None:
        self._labels: dict[tuple[str, str, str], LabelInfo] = {}
        self._loaded = False
        self._taxonomy_path = Path(taxonomy_path) if taxonomy_path else None

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        if self._taxonomy_path is not None:
            self._load_from_path(self._taxonomy_path)
        else:
            self._load_bundled()

    def _load_from_path(self, base: Path) -> None:
        """指定パスからタクソノミラベルを読み込む。"""
        for lab_file in base.rglob("*-lab.xml"):
            self._parse_label_file(lab_file)
        for lab_file in base.rglob("*-lab-en.xml"):
            self._parse_label_file(lab_file)

    def _load_bundled(self) -> None:
        """バンドルされたタクソノミを読み込む。"""
        # 1. パッケージ同梱タクソノミ（最優先）
        bundled = _bundled_taxonomy_path()
        if bundled is not None:
            self._load_from_path(bundled)
            if self._labels:
                logger.debug("Loaded bundled taxonomy from %s", bundled)
                return

        # 2. CWD の taxonomy/ ディレクトリ（開発時フォールバック）
        cwd_tax = Path.cwd() / "taxonomy"
        if cwd_tax.exists():
            self._load_from_path(cwd_tax)
            if self._labels:
                logger.debug("Loaded taxonomy from %s", cwd_tax)
                return

        logger.debug("No bundled taxonomy found")

    def _parse_label_file(self, path: Path) -> None:
        try:
            raw_labels = parse_label_linkbase(path.read_bytes(), source_path=str(path))
        except Exception:
            logger.warning("Failed to parse label file: %s", path, exc_info=True)
            return

        for rl in raw_labels:
            concept_name = rl.concept_name
            # concept_name の形式: "tse-ed-t_NetSales" → prefix="tse-ed-t", local="NetSales"
            if "_" in concept_name:
                prefix, local_name = concept_name.split("_", 1)
            else:
                prefix = ""
                local_name = concept_name

            label = LabelInfo(
                text=rl.text,
                role=rl.role,
                lang=rl.lang,
                source=LabelSource.STANDARD,
            )

            # プレフィックスから名前空間を解決して Clark notation で登録
            ns = _PREFIX_NS.get(prefix)
            if ns:
                qname = f"{{{ns}}}{local_name}"
                self._labels[(qname, rl.lang, rl.role)] = label

            # 元の concept_name でもアクセス可能にする
            self._labels[(concept_name, rl.lang, rl.role)] = label

            # local_name 単体でもフォールバック解決できるようにする
            key_local = (local_name, rl.lang, rl.role)
            if key_local not in self._labels:
                self._labels[key_local] = label

    def resolve(
        self,
        concept_qname: str,
        lang: str,
        role: str = _STANDARD_ROLE,
    ) -> LabelInfo | None:
        self._ensure_loaded()
        return self._labels.get((concept_qname, lang, role))

    def resolve_batch(
        self,
        concept_qnames: list[str] | tuple[str, ...],
        lang: str,
        role: str = _STANDARD_ROLE,
    ) -> dict[str, LabelInfo | None]:
        self._ensure_loaded()
        return {qn: self.resolve(qn, lang, role) for qn in concept_qnames}
