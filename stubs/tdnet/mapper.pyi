from _typeshed import Incomplete
from collections.abc import Callable
from dataclasses import dataclass, field
from tdnet.models.types import LineItem
from xbrl_core import CalculationLinkbase, DefinitionTree

__all__ = ['ConceptMapper', 'MapperContext', 'build_parent_index', 'calc_mapper', 'definition_mapper', 'dict_mapper', 'dividend_mapper', 'forecast_mapper', 'statement_mapper', 'summary_mapper']

ConceptMapper: Incomplete

@dataclass(frozen=True, slots=True)
class MapperContext:
    """マッパーに渡されるコンテキスト情報。

    ``extract_values()`` が ``Statements`` から自動構築する。
    ユニットテスト時は直接構築可能。

    Attributes:
        entity_id: 証券コード等のエンティティ識別子。
        has_consolidated: 連結財務諸表の有無。
        definition_parent_index: Definition Linkbase の general-special arcrole
            による逆引きインデックス。``{独自科目local_name: 標準祖先local_name}``。
            ``definition_mapper`` が使用する。空辞書の場合は
            ``definition_mapper`` は常に ``None`` を返す。
        calculation_linkbase: 提出者の Calculation Linkbase。
            ``calc_mapper`` が ``ancestors_of()`` で祖先を辿る。
            ``None`` の場合は ``calc_mapper`` は常に ``None`` を返す。
    """
    entity_id: str = ...
    has_consolidated: bool | None = ...
    definition_parent_index: dict[str, str] = field(default_factory=dict)
    calculation_linkbase: CalculationLinkbase | None = ...

def dividend_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """配当科目を AnnualDividendPaymentScheduleAxis 対応で名寄せするマッパー。

    - AnnualMember → CK.DPS（年間配当）
    - FirstQuarter/SecondQuarter/ThirdQuarter/YearEndMember → CK.INTERIM_DPS
    - Schedule axis なしの DividendPerShare → CK.DPS（フォールバック）
    """
def forecast_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """業績予想（ForecastMember ディメンション付き）を FORECAST_* CK に名寄せ。

    ResultForecastAxis = ForecastMember を持つアイテムのみ処理。
    基礎概念の CK を取得し、FORECAST_* CK に変換する。
    """
def summary_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """tse-ed-t サマリー科目（経営成績の概況）から名寄せするマッパー。

    ForecastMember ディメンション付きアイテムはスキップ（forecast_mapper に委譲）。
    DividendPerShare は dividend_mapper に委譲。
    """
def statement_mapper(item: LineItem, ctx: MapperContext) -> str | None:
    """財務諸表本体（PL/BS/CF）から名寄せするマッパー。

    jppfs_cor / IFRS / US-GAAP タクソノミの科目を対象とする。
    summary_mapper で取得できなかった項目を補完する。
    """
def dict_mapper(mapping: dict[str, str], *, name: str | None = None) -> ConceptMapper:
    """辞書ベースのマッパーを生成する。

    Args:
        mapping: ``{concept_local_name: canonical_key}`` の辞書。
        name: マッパー名。未指定の場合は自動生成。

    Returns:
        ``ConceptMapper`` として使える callable。
    """
def build_parent_index(definition_linkbase: dict[str, DefinitionTree] | None) -> dict[str, str]:
    """Definition Linkbase の general-special arcrole から逆引きインデックスを構築する。

    general-special arc は from_concept（general/親）→ to_concept（special/子）の
    方向で定義される。これを逆引きし、to_concept → 最も近い標準タクソノミ親概念の
    マッピングを返す。

    Args:
        definition_linkbase: ``parse_definition_linkbase()`` の戻り値。
            None の場合は空辞書を返す。

    Returns:
        ``{独自科目local_name: 標準祖先local_name}`` の辞書。
    """
def definition_mapper(lookup: Callable[[str], str | None] | None = None) -> ConceptMapper:
    """Definition Linkbase の general-special で標準概念に遡上し CK を返すマッパーを生成する。

    提出者独自の科目名を Definition Linkbase の general-special arcrole を
    辿り、最も近い標準タクソノミの祖先概念を見つけて CK に変換する。

    事前に ``build_parent_index()`` で構築した逆引きインデックスを使用するため、
    マッパー呼び出し時のコストは O(1) の辞書参照 + lookup のみ。

    Args:
        lookup: 祖先 concept 名 → canonical key の名寄せ関数。
            ``None`` の場合は組み込み statement_mappings を使用する。

    Returns:
        ``ConceptMapper`` として使える callable。
    """
def calc_mapper(lookup: Callable[[str], str | None] | None = None) -> ConceptMapper:
    """Calculation Linkbase の summation-item で親標準概念に遡上し CK を返すマッパーを生成する。

    提出者独自の科目名を Calculation Linkbase の親子関係（summation-item
    arcrole）を辿り、祖先に標準概念が見つかれば CK に変換する。

    全 role_uri を走査し、最初に CK が見つかった時点で返す。

    Args:
        lookup: 祖先 concept 名 → canonical key の名寄せ関数。
            ``None`` の場合は組み込み statement_mappings を使用する。

    Returns:
        ``ConceptMapper`` として使える callable。
    """
