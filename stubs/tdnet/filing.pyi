from _typeshed import Incomplete
from dataclasses import dataclass
from pathlib import Path
from tdnet._config import get_config as get_config
from tdnet.exceptions import TdnetError as TdnetError
from tdnet.models.statements import Statements as Statements

logger: Incomplete

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
    @property
    def doc_id(self) -> str:
        """文書 ID（URL から抽出）。"""
    def fetch_xbrl(self, *, refresh: bool = False) -> DownloadResult:
        """XBRL ZIP をダウンロードする。キャッシュがあればそれを使う。

        TDnet で 403/404 の場合は JPX 永続 URL にフォールバックする。

        Returns:
            ダウンロード結果 (data, source_url)。
        """
    def xbrl(self, *, taxonomy_path: str | Path | None = None, refresh: bool = False) -> Statements:
        """XBRL を解析し財務諸表コンテナを返す。

        Returns:
            Statements コンテナ。income_statement() / balance_sheet() /
            cash_flow_statement() でアクセスする。
        """
    async def afetch_xbrl(self, *, refresh: bool = False) -> DownloadResult:
        """非同期で XBRL ZIP をダウンロードする。キャッシュがあればそれを使う。

        TDnet で 403/404 の場合は JPX 永続 URL にフォールバックする。

        Returns:
            ダウンロード結果 (data, source_url)。
        """
    async def axbrl(self, *, taxonomy_path: str | Path | None = None, refresh: bool = False) -> Statements:
        """非同期で XBRL を解析し財務諸表コンテナを返す。

        Returns:
            Statements コンテナ。
        """
    async def afetch_pdf(self) -> DownloadResult:
        """非同期で PDF をダウンロードする。

        TDnet で 403/404 の場合は JPX 永続 URL にフォールバックする。

        Raises:
            TdnetError: PDF が存在しない、または取得したデータが PDF でない場合。

        Returns:
            ダウンロード結果 (data, source_url)。
        """
    def fetch_pdf(self) -> DownloadResult:
        """PDF をダウンロードする。

        TDnet で 403/404 の場合は JPX 永続 URL にフォールバックする。

        Raises:
            TdnetError: PDF が存在しない、または取得したデータが PDF でない場合。

        Returns:
            ダウンロード結果 (data, source_url)。
        """
    @classmethod
    def from_yanoshin(cls, item: dict) -> Filing:
        """やのしんWEB-API のレスポンスから Filing を生成する。"""
    @classmethod
    def from_scrape(cls, item: dict) -> Filing:
        """スクレイピング結果から Filing を生成する。"""
