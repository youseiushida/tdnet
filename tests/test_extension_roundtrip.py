"""Parquet 永続化の網羅的な往復比較テスト。

元の Statements と永続化→復元後の Statements を様々な操作で比較し、
情報が失われていないことを検証する。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from xbrl_core import DimensionMember
from xbrl_core.periods import DurationPeriod, InstantPeriod

from tdnet.extension import from_parquet, to_parquet
from tdnet.filing import Filing
from tdnet.mapper import dict_mapper, summary_mapper, statement_mapper
from tdnet.models.ck import CK
from tdnet.models.extract import extract_values, extracted_to_dict
from tdnet.models.statements import Statements
from tdnet.models.types import LabelInfo, LabelSource, LineItem

from tests.helpers import (
    CURRENT_DURATION,
    CURRENT_INSTANT,
    PRIOR_DURATION,
    PRIOR_INSTANT,
    make_consolidated_dim,
    make_current_dim,
    make_dividend_schedule_dim,
    make_forecast_dim,
    make_item,
    make_label,
    make_prior_dim,
)

_TSE_ED_NS = "http://www.xbrl.tdnet.info/taxonomy/jp/tse/tdnet/ed/t/2014-01-12"
_JPPFS_NS = "http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-12-01/jppfs_cor"
_IFRS_NS = "http://disclosure.edinet-fsa.go.jp/taxonomy/ifrs/2023-12-01/ifrs"
_LABEL_ROLE = "http://www.xbrl.org/2003/role/label"


def _make_filing(
    company_code: str = "7203",
    title: str = "決算短信",
) -> Filing:
    return Filing(
        pubdate="2025-03-31 15:00",
        company_code=company_code,
        company_name="テスト株式会社",
        title=title,
        document_url=f"https://example.com/tdnet140120250331{company_code}0.pdf",
        xbrl_url=f"https://example.com/tdnet140120250331{company_code}0.zip",
        markets_string="東証",
    )


def _build_rich_items() -> tuple[LineItem, ...]:
    """多様なエッジケースを含む LineItem 群を生成する。"""
    cons_dim = make_consolidated_dim(True)
    noncons_dim = make_consolidated_dim(False)
    cur_dim = make_current_dim()
    prior_dim = make_prior_dim()

    return (
        # --- PL 科目（当期・連結・DurationPeriod）---
        make_item(
            "NetSales", Decimal("100000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="売上高", label_en="Net sales",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            decimals=-6,
            order=0,
        ),
        make_item(
            "OperatingIncome", Decimal("15000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="営業利益", label_en="Operating income",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            decimals=-6,
            order=1,
        ),
        make_item(
            "OrdinaryIncome", Decimal("16000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="経常利益", label_en="Ordinary income",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            decimals=-6,
            order=2,
        ),
        make_item(
            "ProfitLossAttributableToOwnersOfParent", Decimal("10000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="親会社株主に帰属する当期純利益",
            label_en="Profit attributable to owners of parent",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            decimals=-6,
            order=3,
        ),
        # --- PL 前期 ---
        make_item(
            "NetSales", Decimal("95000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="売上高", label_en="Net sales",
            context_id="PriorYearDuration_ConsolidatedMember",
            dimensions=(cons_dim, prior_dim),
            period=PRIOR_DURATION,
            decimals=-6,
            order=4,
        ),
        # --- BS 科目（当期・連結・InstantPeriod）---
        make_item(
            "TotalAssets", Decimal("500000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="総資産", label_en="Total assets",
            dimensions=(cons_dim,),
            period=CURRENT_INSTANT,
            context_id="CurrentYearInstant_ConsolidatedMember",
            decimals=-6,
            order=5,
        ),
        make_item(
            "NetAssets", Decimal("200000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="純資産", label_en="Net assets",
            dimensions=(cons_dim,),
            period=CURRENT_INSTANT,
            context_id="CurrentYearInstant_ConsolidatedMember",
            decimals=-6,
            order=6,
        ),
        # --- BS 前期 ---
        make_item(
            "TotalAssets", Decimal("480000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="総資産", label_en="Total assets",
            dimensions=(cons_dim,),
            period=PRIOR_INSTANT,
            context_id="PriorYearInstant_ConsolidatedMember",
            decimals=-6,
            order=7,
        ),
        # --- CF 科目 ---
        make_item(
            "NetCashProvidedByUsedInOperatingActivities", Decimal("20000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="営業活動によるキャッシュ・フロー",
            label_en="Cash flows from operating activities",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            decimals=-6,
            order=8,
        ),
        # --- サマリー科目（tse-ed-t） ---
        make_item(
            "NetSales", Decimal("100000000000"),
            namespace_uri=_TSE_ED_NS,
            label_ja="売上高", label_en="Net sales",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            order=9,
        ),
        make_item(
            "OperatingIncome", Decimal("15000000000"),
            namespace_uri=_TSE_ED_NS,
            label_ja="営業利益", label_en="Operating income",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            order=10,
        ),
        # --- KPI 科目（tse-ed-t） ---
        make_item(
            "EarningsPerShare", Decimal("350.50"),
            namespace_uri=_TSE_ED_NS,
            label_ja="1株当たり当期純利益", label_en="EPS",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            unit_ref="JPYPerShares",
            order=11,
        ),
        make_item(
            "BookValuePerShareOfEquityAttributableToOwnersOfParent",
            Decimal("2500.00"),
            namespace_uri=_TSE_ED_NS,
            label_ja="1株当たり純資産", label_en="BPS",
            dimensions=(cons_dim,),
            period=CURRENT_INSTANT,
            context_id="CurrentYearInstant_ConsolidatedMember",
            unit_ref="JPYPerShares",
            order=12,
        ),
        # --- DPS（配当）→ 常に NonConsolidated ---
        make_item(
            "DividendPerShare", Decimal("80"),
            namespace_uri=_TSE_ED_NS,
            label_ja="1株当たり配当金", label_en="Dividend per share",
            dimensions=(noncons_dim, make_dividend_schedule_dim("AnnualMember")),
            period=CURRENT_DURATION,
            unit_ref="JPYPerShares",
            order=13,
        ),
        make_item(
            "DividendPerShare", Decimal("40"),
            namespace_uri=_TSE_ED_NS,
            label_ja="1株当たり中間配当金", label_en="Interim DPS",
            dimensions=(noncons_dim, make_dividend_schedule_dim("SecondQuarterMember")),
            period=CURRENT_DURATION,
            unit_ref="JPYPerShares",
            order=14,
        ),
        # --- 業績予想（ForecastMember）---
        make_item(
            "NetSales", Decimal("110000000000"),
            namespace_uri=_TSE_ED_NS,
            label_ja="売上高（予想）", label_en="Net sales (forecast)",
            dimensions=(cons_dim, make_forecast_dim()),
            period=DurationPeriod(start_date=date(2025, 4, 1), end_date=date(2026, 3, 31)),
            context_id="NextYearDuration_ConsolidatedMember",
            order=15,
        ),
        make_item(
            "OperatingIncome", Decimal("18000000000"),
            namespace_uri=_TSE_ED_NS,
            label_ja="営業利益（予想）", label_en="Operating income (forecast)",
            dimensions=(cons_dim, make_forecast_dim()),
            period=DurationPeriod(start_date=date(2025, 4, 1), end_date=date(2026, 3, 31)),
            context_id="NextYearDuration_ConsolidatedMember",
            order=16,
        ),
        # --- 文字列値 ---
        make_item(
            "NoteToOperatingResults", "増収増益",
            namespace_uri=_TSE_ED_NS,
            label_ja="経営成績に関する注記", label_en="Note",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            unit_ref=None,
            decimals=None,
            order=17,
        ),
        # --- None 値 + is_nil ---
        make_item(
            "ExtraordinaryIncome", None,
            namespace_uri=_JPPFS_NS,
            label_ja="特別利益", label_en="Extraordinary income",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            is_nil=True,
            unit_ref="JPY",
            decimals=None,
            order=18,
        ),
        # --- decimals="INF" ---
        replace(
            make_item(
                "EquityToAssetRatio", Decimal("0.401"),
                namespace_uri=_TSE_ED_NS,
                label_ja="自己資本比率", label_en="Equity ratio",
                dimensions=(cons_dim,),
                period=CURRENT_INSTANT,
                context_id="CurrentYearInstant_ConsolidatedMember",
                unit_ref="pure",
                order=19,
            ),
            decimals="INF",
        ),
        # --- source_line 付き ---
        make_item(
            "CostOfSales", Decimal("70000000000"),
            namespace_uri=_JPPFS_NS,
            label_ja="売上原価", label_en="Cost of sales",
            dimensions=(cons_dim, cur_dim),
            period=CURRENT_DURATION,
            decimals=-6,
            order=20,
        ),
        # --- FILER ラベルソース ---
        LineItem(
            concept=f"{{{_JPPFS_NS}}}GrossProfit",
            namespace_uri=_JPPFS_NS,
            local_name="GrossProfit",
            label_ja=LabelInfo(text="売上総利益", role=_LABEL_ROLE, lang="ja", source=LabelSource.FILER),
            label_en=LabelInfo(text="Gross profit", role=_LABEL_ROLE, lang="en", source=LabelSource.FILER),
            value=Decimal("30000000000"),
            unit_ref="JPY",
            decimals=-6,
            context_id="CurrentYearDuration_ConsolidatedMember",
            period=CURRENT_DURATION,
            entity_id="7203",
            dimensions=(cons_dim, cur_dim),
            is_nil=False,
            source_line=42,
            order=21,
        ),
        # --- FALLBACK ラベルソース ---
        LineItem(
            concept=f"{{{_JPPFS_NS}}}CustomConcept",
            namespace_uri=_JPPFS_NS,
            local_name="CustomConcept",
            label_ja=LabelInfo(text="カスタム", role=_LABEL_ROLE, lang="ja", source=LabelSource.FALLBACK),
            label_en=LabelInfo(text="Custom", role=_LABEL_ROLE, lang="en", source=LabelSource.FALLBACK),
            value=Decimal("999"),
            unit_ref="JPY",
            decimals=0,
            context_id="CurrentYearDuration_ConsolidatedMember",
            period=CURRENT_DURATION,
            entity_id="7203",
            dimensions=(cons_dim, cur_dim),
            is_nil=False,
            source_line=None,
            order=22,
        ),
        # --- 空ディメンション ---
        make_item(
            "NumberOfIssuedSharesTotalNumberOfIssuedShares",
            Decimal("1000000000"),
            namespace_uri=_TSE_ED_NS,
            label_ja="発行済株式総数", label_en="Total shares issued",
            dimensions=(),
            period=CURRENT_INSTANT,
            context_id="CurrentYearInstant",
            unit_ref="shares",
            decimals=0,
            order=23,
        ),
    )


def _roundtrip(
    filing: Filing,
    stmts: Statements | None,
    tmp_path: object,
) -> tuple[Filing, Statements | None]:
    """to_parquet → from_parquet の往復を行い復元結果を返す。"""
    to_parquet([(filing, stmts)], tmp_path)  # type: ignore[arg-type]
    result = from_parquet(tmp_path)  # type: ignore[arg-type]
    assert len(result) == 1
    return result[0]


def _compare_items(
    original: tuple[LineItem, ...],
    restored: tuple[LineItem, ...],
) -> None:
    """2つの LineItem タプルを全フィールド比較する。"""
    assert len(original) == len(restored), (
        f"アイテム数が異なる: {len(original)} vs {len(restored)}"
    )
    for i, (orig, rest) in enumerate(zip(original, restored)):
        assert orig.concept == rest.concept, f"[{i}] concept"
        assert orig.namespace_uri == rest.namespace_uri, f"[{i}] namespace_uri"
        assert orig.local_name == rest.local_name, f"[{i}] local_name"
        # ラベル
        assert orig.label_ja.text == rest.label_ja.text, f"[{i}] label_ja.text"
        assert orig.label_ja.role == rest.label_ja.role, f"[{i}] label_ja.role"
        assert orig.label_ja.lang == rest.label_ja.lang, f"[{i}] label_ja.lang"
        assert orig.label_ja.source == rest.label_ja.source, f"[{i}] label_ja.source"
        assert orig.label_en.text == rest.label_en.text, f"[{i}] label_en.text"
        assert orig.label_en.role == rest.label_en.role, f"[{i}] label_en.role"
        assert orig.label_en.lang == rest.label_en.lang, f"[{i}] label_en.lang"
        assert orig.label_en.source == rest.label_en.source, f"[{i}] label_en.source"
        # value
        if isinstance(orig.value, Decimal):
            assert isinstance(rest.value, Decimal), f"[{i}] value type"
            assert float(orig.value) == float(rest.value), f"[{i}] value"
        else:
            assert orig.value == rest.value, f"[{i}] value"
        assert orig.unit_ref == rest.unit_ref, f"[{i}] unit_ref"
        assert orig.decimals == rest.decimals, f"[{i}] decimals"
        assert orig.context_id == rest.context_id, f"[{i}] context_id"
        # period
        assert type(orig.period) is type(rest.period), f"[{i}] period type"
        if isinstance(orig.period, DurationPeriod):
            assert orig.period.start_date == rest.period.start_date, f"[{i}] period.start_date"  # type: ignore[union-attr]
            assert orig.period.end_date == rest.period.end_date, f"[{i}] period.end_date"  # type: ignore[union-attr]
        elif isinstance(orig.period, InstantPeriod):
            assert orig.period.instant == rest.period.instant, f"[{i}] period.instant"  # type: ignore[union-attr]
        assert orig.entity_id == rest.entity_id, f"[{i}] entity_id"
        # dimensions
        assert len(orig.dimensions) == len(rest.dimensions), f"[{i}] dimensions len"
        for j, (od, rd) in enumerate(zip(orig.dimensions, rest.dimensions)):
            assert od.axis == rd.axis, f"[{i}] dim[{j}].axis"
            assert od.member == rd.member, f"[{i}] dim[{j}].member"
        assert orig.is_nil == rest.is_nil, f"[{i}] is_nil"
        assert orig.source_line == rest.source_line, f"[{i}] source_line"
        assert orig.order == rest.order, f"[{i}] order"


class TestFullFieldComparison:
    """全フィールドの1対1比較。"""

    def test_all_fields_survive_roundtrip(self, tmp_path):
        """全 LineItem の全フィールドが往復で保存される。"""
        filing = _make_filing()
        items = _build_rich_items()
        stmts = Statements(items=items, entity_id="7203")

        _, restored = _roundtrip(filing, stmts, tmp_path)
        assert restored is not None
        _compare_items(items, tuple(restored))


class TestStatementMethods:
    """income_statement / balance_sheet / cash_flow_statement の比較。"""

    def _setup(self, tmp_path):
        filing = _make_filing()
        items = _build_rich_items()
        original = Statements(items=items, entity_id="7203")
        _, restored = _roundtrip(filing, original, tmp_path)
        return original, restored

    def test_income_statement_items_match(self, tmp_path):
        """income_statement() の科目が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_pl = original.income_statement()
        rest_pl = restored.income_statement()  # type: ignore[union-attr]
        assert len(orig_pl) == len(rest_pl)
        for o, r in zip(orig_pl, rest_pl):
            assert o.local_name == r.local_name
            assert o.value == r.value

    def test_income_statement_prior(self, tmp_path):
        """income_statement(period="prior") の科目が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_pl = original.income_statement(period="prior")
        rest_pl = restored.income_statement(period="prior")  # type: ignore[union-attr]
        assert len(orig_pl) == len(rest_pl)
        for o, r in zip(orig_pl, rest_pl):
            assert o.local_name == r.local_name

    def test_balance_sheet_items_match(self, tmp_path):
        """balance_sheet() の科目が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_bs = original.balance_sheet()
        rest_bs = restored.balance_sheet()  # type: ignore[union-attr]
        assert len(orig_bs) == len(rest_bs)
        for o, r in zip(orig_bs, rest_bs):
            assert o.local_name == r.local_name
            assert o.value == r.value

    def test_balance_sheet_period_match(self, tmp_path):
        """balance_sheet() の period が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_bs = original.balance_sheet()
        rest_bs = restored.balance_sheet()  # type: ignore[union-attr]
        assert type(orig_bs.period) is type(rest_bs.period)
        if isinstance(orig_bs.period, InstantPeriod):
            assert orig_bs.period.instant == rest_bs.period.instant  # type: ignore[union-attr]

    def test_cash_flow_statement_items_match(self, tmp_path):
        """cash_flow_statement() の科目が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_cf = original.cash_flow_statement()
        rest_cf = restored.cash_flow_statement()  # type: ignore[union-attr]
        assert len(orig_cf) == len(rest_cf)


class TestExtractValues:
    """extract_values() の比較。"""

    def _setup(self, tmp_path):
        filing = _make_filing()
        items = _build_rich_items()
        original = Statements(items=items, entity_id="7203")
        _, restored = _roundtrip(filing, original, tmp_path)
        return original, restored

    def test_default_pipeline_all_keys(self, tmp_path):
        """デフォルトパイプラインで全キー抽出結果が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_ev = extract_values(original)
        rest_ev = extract_values(restored)  # type: ignore[arg-type]

        assert set(orig_ev.keys()) == set(rest_ev.keys()), (
            f"キー差分: "
            f"orig_only={set(orig_ev) - set(rest_ev)}, "
            f"rest_only={set(rest_ev) - set(orig_ev)}"
        )
        for key in orig_ev:
            ov = orig_ev[key]
            rv = rest_ev[key]
            if ov is None:
                assert rv is None, f"[{key}] orig=None but rest={rv}"
            else:
                assert rv is not None, f"[{key}] orig={ov} but rest=None"
                if isinstance(ov.value, Decimal):
                    assert float(ov.value) == float(rv.value), f"[{key}] value mismatch"  # type: ignore[arg-type]
                else:
                    assert ov.value == rv.value, f"[{key}] value mismatch"

    def test_specific_keys(self, tmp_path):
        """特定キーの抽出結果が一致する。"""
        original, restored = self._setup(tmp_path)
        keys = [
            CK.REVENUE, CK.OPERATING_INCOME, CK.ORDINARY_INCOME,
            CK.NET_INCOME_PARENT, CK.TOTAL_ASSETS, CK.NET_ASSETS,
            CK.EPS, CK.DPS, CK.INTERIM_DPS, CK.EQUITY_RATIO,
            CK.FORECAST_REVENUE, CK.FORECAST_OPERATING_INCOME,
        ]
        orig_ev = extract_values(original, keys)
        rest_ev = extract_values(restored, keys)  # type: ignore[arg-type]

        for key in keys:
            ov = orig_ev.get(key)
            rv = rest_ev.get(key)
            if ov is None:
                assert rv is None, f"[{key}]"
            else:
                assert rv is not None, f"[{key}] None in restored"
                if isinstance(ov.value, Decimal) and isinstance(rv.value, Decimal):
                    assert float(ov.value) == float(rv.value), f"[{key}]"
                else:
                    assert ov.value == rv.value, f"[{key}]"

    def test_extracted_to_dict(self, tmp_path):
        """extracted_to_dict() 結果が一致する。"""
        original, restored = self._setup(tmp_path)
        keys = [CK.REVENUE, CK.OPERATING_INCOME, CK.EPS, CK.DPS]
        orig_dict = extracted_to_dict(extract_values(original, keys))
        rest_dict = extracted_to_dict(extract_values(restored, keys))  # type: ignore[arg-type]

        assert set(orig_dict.keys()) == set(rest_dict.keys())
        for key in orig_dict:
            ov = orig_dict[key]
            rv = rest_dict[key]
            if isinstance(ov, Decimal) and isinstance(rv, Decimal):
                assert float(ov) == float(rv), f"[{key}]"
            else:
                assert ov == rv, f"[{key}]"

    def test_period_current(self, tmp_path):
        """period="current" の抽出結果が一致する。"""
        original, restored = self._setup(tmp_path)
        keys = [CK.REVENUE, CK.OPERATING_INCOME]
        orig_ev = extract_values(original, keys, period="current")
        rest_ev = extract_values(restored, keys, period="current")  # type: ignore[arg-type]

        for key in keys:
            ov = orig_ev.get(key)
            rv = rest_ev.get(key)
            if ov is not None:
                assert rv is not None, f"[{key}]"
                assert float(ov.value) == float(rv.value), f"[{key}]"  # type: ignore[arg-type]

    def test_period_prior(self, tmp_path):
        """period="prior" の抽出結果が一致する。"""
        original, restored = self._setup(tmp_path)
        keys = [CK.REVENUE]
        orig_ev = extract_values(original, keys, period="prior")
        rest_ev = extract_values(restored, keys, period="prior")  # type: ignore[arg-type]

        ov = orig_ev.get(CK.REVENUE)
        rv = rest_ev.get(CK.REVENUE)
        if ov is not None:
            assert rv is not None
            assert float(ov.value) == float(rv.value)  # type: ignore[arg-type]


class TestCustomMapper:
    """カスタムマッパーの動作比較。"""

    def _setup(self, tmp_path):
        filing = _make_filing()
        items = _build_rich_items()
        original = Statements(items=items, entity_id="7203")
        _, restored = _roundtrip(filing, original, tmp_path)
        return original, restored

    def test_dict_mapper(self, tmp_path):
        """dict_mapper でカスタムキーが一致する。"""
        original, restored = self._setup(tmp_path)
        custom = dict_mapper({
            "NetSales": "MY_REVENUE",
            "OperatingIncome": "MY_OP_INCOME",
            "TotalAssets": "MY_TOTAL_ASSETS",
            "GrossProfit": "MY_GROSS",
        }, name="custom_test")

        orig_ev = extract_values(original, mapper=[custom])
        rest_ev = extract_values(restored, mapper=[custom])  # type: ignore[arg-type]

        assert set(orig_ev.keys()) == set(rest_ev.keys())
        for key in orig_ev:
            ov = orig_ev[key]
            rv = rest_ev[key]
            assert ov is not None
            assert rv is not None
            if isinstance(ov.value, Decimal) and isinstance(rv.value, Decimal):
                assert float(ov.value) == float(rv.value), f"[{key}]"
            else:
                assert ov.value == rv.value, f"[{key}]"

    def test_mixed_pipeline(self, tmp_path):
        """カスタム + 標準マッパーの混合パイプラインが一致する。"""
        original, restored = self._setup(tmp_path)
        custom = dict_mapper({"NetSales": "CUSTOM_SALES"}, name="override")
        pipeline = [custom, summary_mapper, statement_mapper]

        orig_ev = extract_values(original, mapper=pipeline)
        rest_ev = extract_values(restored, mapper=pipeline)  # type: ignore[arg-type]

        assert set(orig_ev.keys()) == set(rest_ev.keys())
        # カスタムキーが優先されているか
        assert "CUSTOM_SALES" in orig_ev
        assert "CUSTOM_SALES" in rest_ev


class TestSearchAndLookup:
    """search / __getitem__ / __contains__ の比較。"""

    def _setup(self, tmp_path):
        filing = _make_filing()
        items = _build_rich_items()
        original = Statements(items=items, entity_id="7203")
        _, restored = _roundtrip(filing, original, tmp_path)
        return original, restored

    def test_search_ja(self, tmp_path):
        """日本語キーワード検索結果が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_results = original.search("売上")
        rest_results = restored.search("売上")  # type: ignore[union-attr]

        assert len(orig_results) == len(rest_results)
        for o, r in zip(orig_results, rest_results):
            assert o.local_name == r.local_name
            assert o.label_ja.text == r.label_ja.text

    def test_search_en(self, tmp_path):
        """英語キーワード検索結果が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_results = original.search("Operating")
        rest_results = restored.search("Operating")  # type: ignore[union-attr]

        assert len(orig_results) == len(rest_results)

    def test_getitem_by_ja_label(self, tmp_path):
        """日本語ラベルで __getitem__ が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_item = original["営業利益"]
        rest_item = restored["営業利益"]  # type: ignore[index]

        assert orig_item.local_name == rest_item.local_name
        assert orig_item.value == rest_item.value

    def test_getitem_by_local_name(self, tmp_path):
        """local_name で __getitem__ が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_item = original["TotalAssets"]
        rest_item = restored["TotalAssets"]  # type: ignore[index]

        assert orig_item.value == rest_item.value

    def test_contains(self, tmp_path):
        """__contains__ が一致する。"""
        original, restored = self._setup(tmp_path)
        for key in ["営業利益", "TotalAssets", "存在しない科目"]:
            assert (key in original) == (key in restored), f"[{key}]"  # type: ignore[operator]

    def test_len(self, tmp_path):
        """__len__ が一致する。"""
        original, restored = self._setup(tmp_path)
        assert len(original) == len(restored)  # type: ignore[arg-type]


class TestToDataframe:
    """to_dataframe() の比較。"""

    def _setup(self, tmp_path):
        filing = _make_filing()
        items = _build_rich_items()
        original = Statements(items=items, entity_id="7203")
        _, restored = _roundtrip(filing, original, tmp_path)
        return original, restored

    def test_dataframe_shape(self, tmp_path):
        """DataFrame の shape が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_df = original.to_dataframe()
        rest_df = restored.to_dataframe()  # type: ignore[union-attr]

        assert orig_df.shape == rest_df.shape

    def test_dataframe_columns(self, tmp_path):
        """DataFrame のカラムが一致する。"""
        original, restored = self._setup(tmp_path)
        orig_df = original.to_dataframe()
        rest_df = restored.to_dataframe()  # type: ignore[union-attr]

        assert list(orig_df.columns) == list(rest_df.columns)

    def test_dataframe_label_ja(self, tmp_path):
        """DataFrame の label_ja が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_df = original.to_dataframe()
        rest_df = restored.to_dataframe()  # type: ignore[union-attr]

        assert list(orig_df["label_ja"]) == list(rest_df["label_ja"])

    def test_dataframe_local_name(self, tmp_path):
        """DataFrame の local_name が一致する。"""
        original, restored = self._setup(tmp_path)
        orig_df = original.to_dataframe()
        rest_df = restored.to_dataframe()  # type: ignore[union-attr]

        assert list(orig_df["local_name"]) == list(rest_df["local_name"])


class TestMultipleFilings:
    """複数 Filing の往復で結合キーが混ざらないことを検証する。"""

    def test_two_companies_isolated(self, tmp_path):
        """2社分のデータが混ざらない。"""
        f1 = _make_filing(company_code="7203")
        f2 = _make_filing(company_code="6758", title="ソニー決算")
        s1 = Statements(
            items=(
                make_item("NetSales", Decimal("100"), entity_id="7203",
                          namespace_uri=_JPPFS_NS, label_ja="売上高"),
                make_item("OperatingIncome", Decimal("20"), entity_id="7203",
                          namespace_uri=_JPPFS_NS, label_ja="営業利益"),
            ),
            entity_id="7203",
        )
        s2 = Statements(
            items=(
                make_item("NetSales", Decimal("999"), entity_id="6758",
                          namespace_uri=_JPPFS_NS, label_ja="売上高"),
            ),
            entity_id="6758",
        )

        to_parquet([(f1, s1), (f2, s2)], tmp_path)
        result = from_parquet(tmp_path)

        assert len(result) == 2
        r1_filing, r1_stmts = result[0]
        r2_filing, r2_stmts = result[1]

        assert r1_filing.company_code == "7203"
        assert r2_filing.company_code == "6758"
        assert len(r1_stmts) == 2  # type: ignore[arg-type]
        assert len(r2_stmts) == 1  # type: ignore[arg-type]
        assert list(r1_stmts)[0].entity_id == "7203"  # type: ignore[arg-type]
        assert list(r2_stmts)[0].entity_id == "6758"  # type: ignore[arg-type]

    def test_mixed_none_and_statements(self, tmp_path):
        """Statements=None と Statements 混在が正しく復元される。"""
        f1 = _make_filing(company_code="0001")
        f2 = _make_filing(company_code="0002")
        f3 = _make_filing(company_code="0003")
        s2 = Statements(
            items=(make_item("NetSales", Decimal("500"), entity_id="0002"),),
            entity_id="0002",
        )

        to_parquet([(f1, None), (f2, s2), (f3, None)], tmp_path)
        result = from_parquet(tmp_path)

        assert len(result) == 3
        assert result[0][1] is None
        assert result[1][1] is not None
        assert len(result[1][1]) == 1
        assert result[2][1] is None


class TestEdgeCasesDetailed:
    """個別エッジケースの詳細検証。"""

    def test_large_decimal(self, tmp_path):
        """大きい Decimal 値が往復する。"""
        filing = _make_filing()
        item = make_item("TotalAssets", Decimal("999999999999999"))
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert isinstance(r_item.value, Decimal)
        assert float(r_item.value) == float(Decimal("999999999999999"))

    def test_negative_decimal(self, tmp_path):
        """負の Decimal 値が往復する。"""
        filing = _make_filing()
        item = make_item("ExtraordinaryLoss", Decimal("-500000000"))
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert isinstance(r_item.value, Decimal)
        assert float(r_item.value) == float(Decimal("-500000000"))

    def test_zero_decimal(self, tmp_path):
        """ゼロ Decimal 値が往復する。"""
        filing = _make_filing()
        item = make_item("ExtraordinaryIncome", Decimal("0"))
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert isinstance(r_item.value, Decimal)
        assert r_item.value == Decimal("0")

    def test_fractional_decimal(self, tmp_path):
        """小数点付き Decimal 値が往復する。"""
        filing = _make_filing()
        item = make_item("EarningsPerShare", Decimal("123.456"))
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert isinstance(r_item.value, Decimal)
        assert float(r_item.value) == float(Decimal("123.456"))

    def test_unicode_text_value(self, tmp_path):
        """Unicode 文字列値が往復する。"""
        filing = _make_filing()
        item = make_item(
            "Note", "増収増益。前年比+10%。\n改行あり",
            unit_ref=None, decimals=None,
        )
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert r_item.value == "増収増益。前年比+10%。\n改行あり"

    def test_empty_string_value(self, tmp_path):
        """空文字列値が往復する。"""
        filing = _make_filing()
        item = make_item("EmptyNote", "", unit_ref=None, decimals=None)
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert r_item.value == ""

    def test_many_dimensions(self, tmp_path):
        """3つ以上のディメンションが往復する。"""
        filing = _make_filing()
        dims = (
            make_consolidated_dim(True),
            make_current_dim(),
            make_forecast_dim(),
        )
        item = make_item("NetSales", Decimal("100"), dimensions=dims)
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert len(r_item.dimensions) == 3
        for o, r in zip(dims, r_item.dimensions):
            assert o.axis == r.axis
            assert o.member == r.member

    def test_negative_decimals_int(self, tmp_path):
        """負の decimals（-6 等）が往復する。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"), decimals=-6)
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert r_item.decimals == -6

    def test_zero_decimals(self, tmp_path):
        """decimals=0 が往復する。"""
        filing = _make_filing()
        item = make_item("Shares", Decimal("1000000"), decimals=0)
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert r_item.decimals == 0

    def test_source_line_preserved(self, tmp_path):
        """source_line が保存される。"""
        filing = _make_filing()
        item = LineItem(
            concept=f"{{{_JPPFS_NS}}}NetSales",
            namespace_uri=_JPPFS_NS,
            local_name="NetSales",
            label_ja=make_label("売上高", "ja"),
            label_en=make_label("Net sales", "en"),
            value=Decimal("100"),
            unit_ref="JPY",
            decimals=-6,
            context_id="ctx",
            period=CURRENT_DURATION,
            entity_id="7203",
            dimensions=(),
            is_nil=False,
            source_line=123,
            order=0,
        )
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert r_item.source_line == 123

    def test_source_line_none(self, tmp_path):
        """source_line=None が保存される。"""
        filing = _make_filing()
        item = make_item("NetSales", Decimal("100"))
        assert item.source_line is None
        stmts = Statements(items=(item,), entity_id="7203")
        _, restored = _roundtrip(filing, stmts, tmp_path)
        r_item = list(restored)[0]  # type: ignore[arg-type]
        assert r_item.source_line is None

    def test_filing_doc_id(self, tmp_path):
        """Filing.doc_id が一致する。"""
        filing = _make_filing()
        restored_filing, _ = _roundtrip(filing, None, tmp_path)
        assert restored_filing.doc_id == filing.doc_id

    def test_filing_has_xbrl(self, tmp_path):
        """Filing.has_xbrl が一致する。"""
        filing = _make_filing()
        restored_filing, _ = _roundtrip(filing, None, tmp_path)
        assert restored_filing.has_xbrl == filing.has_xbrl

    def test_filing_without_xbrl(self, tmp_path):
        """xbrl_url 空の Filing が往復する。"""
        filing = Filing(
            pubdate="2025-01-01",
            company_code="9999",
            company_name="テスト",
            title="PR",
            document_url="https://example.com/doc.pdf",
            xbrl_url="",
            markets_string="",
        )
        restored_filing, _ = _roundtrip(filing, None, tmp_path)
        assert restored_filing.xbrl_url == ""
        assert restored_filing.has_xbrl is False
