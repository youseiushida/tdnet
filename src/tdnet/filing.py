"""TDnet の開示書類 (Filing)。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from tdnet._config import get_config
from tdnet.cache import _get_cache_store
from tdnet.exceptions import TdnetError
from tdnet.models.statements import Statements

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Filing:
    """TDnet の開示書類 1 件。"""

    pubdate: str
    company_code: str
    company_name: str
    title: str
    document_url: str
    xbrl_url: str
    markets_string: str

    @property
    def has_xbrl(self) -> bool:
        """XBRL が利用可能かどうか。"""
        return bool(self.xbrl_url)

    @property
    def doc_id(self) -> str:
        """文書 ID（URL から抽出）。"""
        url = self.document_url or self.xbrl_url
        if not url:
            return ""
        # URL末尾の {prefix}{YYYYMMDD}{DOCID}.{ext} から DOCID を取得
        name = url.rsplit("/", 1)[-1]
        # prefix(4) + YYYYMMDD(8) + DOCID(6) + .ext
        stem = name.rsplit(".", 1)[0]
        if len(stem) >= 18:
            return stem[12:]  # DOCID 部分
        return stem

    def fetch_xbrl(self, *, refresh: bool = False) -> bytes:
        """XBRL ZIP をダウンロードする。キャッシュがあればそれを使う。"""
        if not self.xbrl_url:
            raise TdnetError("This filing has no XBRL data")

        from tdnet.api import download_xbrl

        cache_key = self._cache_key()
        store = _get_cache_store()

        if store is not None and not refresh:
            cached = store.get(cache_key)
            if cached is not None:
                return cached

        data = download_xbrl(self.xbrl_url)

        if store is not None:
            store.put(cache_key, data)

        return data

    def xbrl(self, *, taxonomy_path: str | Path | None = None, refresh: bool = False) -> Statements:
        """XBRL を解析し財務諸表コンテナを返す。

        Returns:
            Statements コンテナ。income_statement() / balance_sheet() /
            cash_flow_statement() でアクセスする。
        """
        from tdnet.xbrl.parser import parse_zip

        zip_data = self.fetch_xbrl(refresh=refresh)

        tp = taxonomy_path
        if tp is None:
            config = get_config()
            tp = config.taxonomy_path

        return parse_zip(
            zip_data,
            taxonomy_path=tp,
            entity_id=self.company_code,
        )

    def fetch_pdf(self) -> bytes:
        """PDF をダウンロードする。

        Raises:
            TdnetError: PDF が存在しない、または取得したデータが PDF でない場合。
        """
        if not self.document_url:
            raise TdnetError("This filing has no PDF URL (document_url is empty)")

        from tdnet.api import download_file

        data = download_file(self.document_url)
        if data[:5] == b"%PDF-":
            return data

        # document_url が PDF でなかった場合、xbrl_url からPDF URLを推測
        if self.xbrl_url:
            # xbrl_url の拡張子を .pdf に置換して試行
            pdf_url_guess = self.xbrl_url.rsplit(".", 1)[0] + ".pdf"
            if pdf_url_guess != self.document_url:
                try:
                    data2 = download_file(pdf_url_guess)
                    if data2[:5] == b"%PDF-":
                        return data2
                except TdnetError:
                    pass

        raise TdnetError(
            "PDF を取得できませんでした。"
            "document_url が PDF ではなく、代替 URL からも取得できません。"
        )

    def _cache_key(self) -> str:
        """キャッシュキーを生成する。"""
        url = self.xbrl_url or self.document_url
        name = url.rsplit("/", 1)[-1]
        return name.rsplit(".", 1)[0]

    @classmethod
    def from_yanoshin(cls, item: dict) -> Filing:
        """やのしんWEB-API のレスポンスから Filing を生成する。"""
        return cls(
            pubdate=item.get("pubdate", ""),
            company_code=item.get("company_code", ""),
            company_name=item.get("company_name", ""),
            title=item.get("title", ""),
            document_url=item.get("document_url", ""),
            xbrl_url=item.get("url_xbrl", ""),
            markets_string=item.get("markets_string", ""),
        )

    @classmethod
    def from_scrape(cls, item: dict) -> Filing:
        """スクレイピング結果から Filing を生成する。"""
        return cls(
            pubdate=item.get("pubdate", ""),
            company_code=item.get("company_code", ""),
            company_name=item.get("company_name", ""),
            title=item.get("title", ""),
            document_url=item.get("document_url", ""),
            xbrl_url=item.get("url_xbrl", ""),
            markets_string=item.get("markets_string", ""),
        )
