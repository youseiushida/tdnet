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
class DownloadResult:
    """ダウンロード結果。

    Attributes:
        data: ダウンロードしたファイルデータ。
        source_url: 実際にダウンロードした URL。
            TDnet から取得した場合は元の URL、
            JPX にフォールバックした場合は JPX の永続 URL。
    """

    data: bytes
    source_url: str


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

    def fetch_xbrl(self, *, refresh: bool = False) -> DownloadResult:
        """XBRL ZIP をダウンロードする。キャッシュがあればそれを使う。

        TDnet で 403/404 の場合は JPX 永続 URL にフォールバックする。

        Returns:
            ダウンロード結果 (data, source_url)。
        """
        if not self.xbrl_url:
            raise TdnetError("This filing has no XBRL data")

        from tdnet.api import download_file_with_fallback

        cache_key = self._cache_key()
        store = _get_cache_store()

        if store is not None and not refresh:
            cached = store.get(cache_key)
            if cached is not None:
                return DownloadResult(data=cached, source_url=self.xbrl_url)

        data, source_url = download_file_with_fallback(
            self.xbrl_url, self.company_code,
        )

        if store is not None:
            store.put(cache_key, data)

        return DownloadResult(data=data, source_url=source_url)

    def xbrl(self, *, taxonomy_path: str | Path | None = None, refresh: bool = False) -> Statements:
        """XBRL を解析し財務諸表コンテナを返す。

        Returns:
            Statements コンテナ。income_statement() / balance_sheet() /
            cash_flow_statement() でアクセスする。
        """
        from tdnet.xbrl.parser import parse_zip

        result = self.fetch_xbrl(refresh=refresh)

        tp = taxonomy_path
        if tp is None:
            config = get_config()
            tp = config.taxonomy_path

        return parse_zip(
            result.data,
            taxonomy_path=tp,
            entity_id=self.company_code,
        )

    async def afetch_xbrl(self, *, refresh: bool = False) -> DownloadResult:
        """非同期で XBRL ZIP をダウンロードする。キャッシュがあればそれを使う。

        TDnet で 403/404 の場合は JPX 永続 URL にフォールバックする。

        Returns:
            ダウンロード結果 (data, source_url)。
        """
        if not self.xbrl_url:
            raise TdnetError("This filing has no XBRL data")

        from tdnet.api import adownload_file_with_fallback

        cache_key = self._cache_key()
        store = _get_cache_store()

        if store is not None and not refresh:
            cached = store.get(cache_key)
            if cached is not None:
                return DownloadResult(data=cached, source_url=self.xbrl_url)

        data, source_url = await adownload_file_with_fallback(
            self.xbrl_url, self.company_code,
        )

        if store is not None:
            store.put(cache_key, data)

        return DownloadResult(data=data, source_url=source_url)

    async def axbrl(
        self,
        *,
        taxonomy_path: str | Path | None = None,
        refresh: bool = False,
    ) -> Statements:
        """非同期で XBRL を解析し財務諸表コンテナを返す。

        Returns:
            Statements コンテナ。
        """
        from tdnet.xbrl.parser import parse_zip

        result = await self.afetch_xbrl(refresh=refresh)

        tp = taxonomy_path
        if tp is None:
            config = get_config()
            tp = config.taxonomy_path

        return parse_zip(
            result.data,
            taxonomy_path=tp,
            entity_id=self.company_code,
        )

    async def afetch_pdf(self) -> DownloadResult:
        """非同期で PDF をダウンロードする。

        TDnet で 403/404 の場合は JPX 永続 URL にフォールバックする。

        Raises:
            TdnetError: PDF が存在しない、または取得したデータが PDF でない場合。

        Returns:
            ダウンロード結果 (data, source_url)。
        """
        if not self.document_url:
            raise TdnetError("This filing has no PDF URL (document_url is empty)")

        from tdnet.api import adownload_file_with_fallback

        data, source_url = await adownload_file_with_fallback(
            self.document_url, self.company_code,
        )
        if data[:5] == b"%PDF-":
            return DownloadResult(data=data, source_url=source_url)

        # document_url が PDF でなかった場合、xbrl_url からPDF URLを推測
        if self.xbrl_url:
            pdf_url_guess = self.xbrl_url.rsplit(".", 1)[0] + ".pdf"
            if pdf_url_guess != self.document_url:
                try:
                    data2, source_url2 = await adownload_file_with_fallback(
                        pdf_url_guess, self.company_code,
                    )
                    if data2[:5] == b"%PDF-":
                        return DownloadResult(data=data2, source_url=source_url2)
                except TdnetError:
                    pass

        raise TdnetError(
            "PDF を取得できませんでした。"
            "document_url が PDF ではなく、代替 URL からも取得できません。"
        )

    def fetch_pdf(self) -> DownloadResult:
        """PDF をダウンロードする。

        TDnet で 403/404 の場合は JPX 永続 URL にフォールバックする。

        Raises:
            TdnetError: PDF が存在しない、または取得したデータが PDF でない場合。

        Returns:
            ダウンロード結果 (data, source_url)。
        """
        if not self.document_url:
            raise TdnetError("This filing has no PDF URL (document_url is empty)")

        from tdnet.api import download_file_with_fallback

        data, source_url = download_file_with_fallback(
            self.document_url, self.company_code,
        )
        if data[:5] == b"%PDF-":
            return DownloadResult(data=data, source_url=source_url)

        # document_url が PDF でなかった場合、xbrl_url からPDF URLを推測
        if self.xbrl_url:
            # xbrl_url の拡張子を .pdf に置換して試行
            pdf_url_guess = self.xbrl_url.rsplit(".", 1)[0] + ".pdf"
            if pdf_url_guess != self.document_url:
                try:
                    data2, source_url2 = download_file_with_fallback(
                        pdf_url_guess, self.company_code,
                    )
                    if data2[:5] == b"%PDF-":
                        return DownloadResult(data=data2, source_url=source_url2)
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
