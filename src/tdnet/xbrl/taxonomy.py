"""TDnet タクソノミのラベル解決。"""

from __future__ import annotations

import importlib.resources
import logging
from collections.abc import Sequence
from pathlib import Path

from xbrl_core import LabelInfo, LabelSource, RawLabel
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
        """指定パスからタクソノミラベルを読み込む。

        ``*-lab.xml`` と ``*_lab.xml`` の両パターンを探索する
        （TDnet: ハイフン区切り、EDINET: アンダースコア区切り）。
        """
        for lab_file in base.rglob("*-lab.xml"):
            self._parse_label_file(lab_file)
        for lab_file in base.rglob("*_lab.xml"):
            self._parse_label_file(lab_file)
        for lab_file in base.rglob("*-lab-en.xml"):
            self._parse_label_file(lab_file)
        for lab_file in base.rglob("*_lab-en.xml"):
            self._parse_label_file(lab_file)

    def _load_bundled(self) -> None:
        """バンドルされたタクソノミを読み込む。"""
        # 1. パッケージ同梱タクソノミ（最優先）
        bundled = _bundled_taxonomy_path()
        if bundled is not None:
            self._load_from_path(bundled)
            if self._labels:
                logger.debug("Loaded bundled taxonomy from %s", bundled)

        # 2. CWD の taxonomy/ ディレクトリ（開発時フォールバック）
        if not self._labels:
            cwd_tax = Path.cwd() / "taxonomy"
            if cwd_tax.exists():
                self._load_from_path(cwd_tax)
                if self._labels:
                    logger.debug("Loaded taxonomy from %s", cwd_tax)

        # 3. インストール済み EDINET タクソノミも自動ロード
        try:
            from tdnet.taxonomy_install import detect_installed_taxonomy
            installed = detect_installed_taxonomy()
            if installed is not None:
                self._load_from_path(Path(installed))
                logger.debug("Loaded installed taxonomy from %s", installed)
        except Exception:
            pass

        if not self._labels:
            logger.debug("No bundled taxonomy found")

    def inject_filer_labels(self, raw_labels: tuple[RawLabel, ...]) -> None:
        """ZIP 内 lab.xml からパースした filer ラベルを注入する。

        標準ラベルがロード済みの状態で呼び出すこと。
        ``LabelSource.EXTENSION`` で登録し、``convert_line_item`` で
        ``LabelSource.FILER`` に変換される。

        Args:
            raw_labels: ZIP 内ラベルリンクベースからパースした RawLabel のタプル。
        """
        self._ensure_loaded()

        for rl in raw_labels:
            concept_name = rl.concept_name

            label = LabelInfo(
                text=rl.text,
                role=rl.role,
                lang=rl.lang,
                source=LabelSource.EXTENSION,
            )

            # concept_name で登録（filer ラベルは上書き）
            self._labels[(concept_name, rl.lang, rl.role)] = label

            # local_name でも登録
            if "_" in concept_name:
                _, local_name = concept_name.split("_", 1)
            else:
                local_name = concept_name
            self._labels[(local_name, rl.lang, rl.role)] = label

    def _parse_label_file(self, path: Path) -> None:
        """ラベルリンクベースファイルをパースして ``_labels`` に登録する。"""
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
        """ラベルを解決する。

        Clark notation (``{ns}LocalName``) の完全一致を試み、
        見つからなければ local_name にフォールバックする。

        Args:
            concept_qname: 概念名（Clark notation または local_name）。
            lang: 言語コード（``"ja"`` / ``"en"``）。
            role: ラベルロール URI。

        Returns:
            解決された LabelInfo。見つからなければ ``None``。
        """
        self._ensure_loaded()
        result = self._labels.get((concept_qname, lang, role))
        if result is not None:
            return result
        # Clark notation → local_name フォールバック
        if "}" in concept_qname:
            local_name = concept_qname.split("}")[-1]
            return self._labels.get((local_name, lang, role))
        return None

    def resolve_batch(
        self,
        concept_qnames: Sequence[str],
        lang: str,
        role: str = _STANDARD_ROLE,
    ) -> dict[str, LabelInfo | None]:
        """複数の概念名のラベルを一括解決する。

        Args:
            concept_qnames: 概念名のシーケンス。
            lang: 言語コード。
            role: ラベルロール URI。

        Returns:
            概念名をキー、LabelInfo を値とする辞書。
        """
        self._ensure_loaded()
        return {qn: self.resolve(qn, lang, role) for qn in concept_qnames}
