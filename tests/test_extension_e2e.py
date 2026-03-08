"""Parquet 永続化の E2E テスト（実 API 使用）。

実際の TDnet API から Filing を取得し XBRL をパースした Statements と、
Parquet 永続化→復元後の Statements を網羅的に比較する。

ネットワーク接続が必要なため ``pytest -m e2e`` で実行する。
"""

from __future__ import annotations

from decimal import Decimal

import pytest

import tdnet
from tdnet import CK, extract_values, extracted_to_dict
from tdnet.extension import export_parquet, import_parquet
from tdnet.filing import Filing
from tdnet.mapper import dict_mapper, statement_mapper, summary_mapper
from tdnet.models.statements import Statements

pytestmark = pytest.mark.e2e


# ------------------------------------------------------------------
# テストデータ取得
# ------------------------------------------------------------------

def _fetch_filings_with_statements(
    n: int = 3,
) -> list[tuple[Filing, Statements]]:
    """API から XBRL 付き Filing を取得しパースする。"""
    filings = tdnet.documents(has_xbrl=True, limit=20)
    results: list[tuple[Filing, Statements]] = []
    for f in filings:
        if len(results) >= n:
            break
        try:
            stmts = f.xbrl()
            if len(stmts) > 0:
                results.append((f, stmts))
        except Exception:
            continue
    if not results:
        pytest.skip("XBRL 付きの Filing を取得できなかった")
    return results


@pytest.fixture(scope="module")
def e2e_data(tmp_path_factory):
    """モジュールスコープで取得・往復データを用意する。"""
    pairs = _fetch_filings_with_statements(3)
    tmp = tmp_path_factory.mktemp("parquet_e2e")

    data: list[tuple[Filing, Statements | None]] = [
        (f, s) for f, s in pairs
    ]

    export_parquet(data, tmp)
    restored = import_parquet(tmp)

    return {
        "originals": pairs,
        "restored": restored,
        "path": tmp,
    }


# ------------------------------------------------------------------
# ヘルパー
# ------------------------------------------------------------------

def _originals(e2e_data) -> list[tuple[Filing, Statements]]:
    return e2e_data["originals"]


def _restored(e2e_data) -> list[tuple[Filing, Statements | None]]:
    return e2e_data["restored"]


# ------------------------------------------------------------------
# Filing メタデータ
# ------------------------------------------------------------------

class TestFilingMetadata:
    """Filing のメタデータが復元されるか。"""

    def test_count(self, e2e_data):
        """Filing 件数が一致する。"""
        assert len(_originals(e2e_data)) == len(_restored(e2e_data))

    def test_doc_id(self, e2e_data):
        """全 Filing の doc_id が一致する。"""
        for (of, _), (rf, _) in zip(_originals(e2e_data), _restored(e2e_data)):
            assert of.doc_id == rf.doc_id, f"{of.company_code}"

    def test_company_code(self, e2e_data):
        """company_code が一致する。"""
        for (of, _), (rf, _) in zip(_originals(e2e_data), _restored(e2e_data)):
            assert of.company_code == rf.company_code

    def test_all_fields(self, e2e_data):
        """Filing の全フィールドが一致する。"""
        for (of, _), (rf, _) in zip(_originals(e2e_data), _restored(e2e_data)):
            assert of.pubdate == rf.pubdate
            assert of.company_name == rf.company_name
            assert of.title == rf.title
            assert of.document_url == rf.document_url
            assert of.xbrl_url == rf.xbrl_url
            assert of.markets_string == rf.markets_string
            assert of.has_xbrl == rf.has_xbrl


# ------------------------------------------------------------------
# LineItem 全フィールド比較
# ------------------------------------------------------------------

class TestLineItemFields:
    """各 LineItem の全フィールドが復元されるか。"""

    def test_item_count(self, e2e_data):
        """全 Filing の LineItem 件数が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            assert rs is not None
            assert len(os) == len(rs), (
                f"orig={len(os)}, restored={len(rs)}"
            )

    def test_concept_match(self, e2e_data):
        """全 LineItem の concept が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.concept == r.concept, f"[{i}]"

    def test_local_name_match(self, e2e_data):
        """全 LineItem の local_name が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.local_name == r.local_name, f"[{i}]"

    def test_namespace_match(self, e2e_data):
        """全 LineItem の namespace_uri が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.namespace_uri == r.namespace_uri, f"[{i}]"

    def test_value_match(self, e2e_data):
        """全 LineItem の value が一致する（Decimal は float 比較）。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                if isinstance(o.value, Decimal):
                    assert isinstance(r.value, Decimal), f"[{i}] type"
                    assert float(o.value) == float(r.value), f"[{i}]"
                else:
                    assert o.value == r.value, f"[{i}]"

    def test_label_ja_match(self, e2e_data):
        """全 LineItem の label_ja が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.label_ja.text == r.label_ja.text, f"[{i}] text"
                assert o.label_ja.role == r.label_ja.role, f"[{i}] role"
                assert o.label_ja.source == r.label_ja.source, f"[{i}] source"
                assert o.label_ja.lang == r.label_ja.lang, f"[{i}] lang"

    def test_label_en_match(self, e2e_data):
        """全 LineItem の label_en が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.label_en.text == r.label_en.text, f"[{i}] text"
                assert o.label_en.source == r.label_en.source, f"[{i}] source"

    def test_decimals_match(self, e2e_data):
        """全 LineItem の decimals が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.decimals == r.decimals, f"[{i}] {o.local_name}"

    def test_period_match(self, e2e_data):
        """全 LineItem の period が一致する。"""
        from xbrl_core.periods import DurationPeriod, InstantPeriod

        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert type(o.period) is type(r.period), f"[{i}] type"
                if isinstance(o.period, DurationPeriod):
                    assert o.period.start_date == r.period.start_date, f"[{i}] start"
                    assert o.period.end_date == r.period.end_date, f"[{i}] end"
                elif isinstance(o.period, InstantPeriod):
                    assert o.period.instant == r.period.instant, f"[{i}] instant"

    def test_dimensions_match(self, e2e_data):
        """全 LineItem の dimensions が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert len(o.dimensions) == len(r.dimensions), f"[{i}] len"
                for j, (od, rd) in enumerate(zip(o.dimensions, r.dimensions)):
                    assert od.axis == rd.axis, f"[{i}][{j}] axis"
                    assert od.member == rd.member, f"[{i}][{j}] member"

    def test_context_id_match(self, e2e_data):
        """全 LineItem の context_id が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.context_id == r.context_id, f"[{i}]"

    def test_unit_ref_match(self, e2e_data):
        """全 LineItem の unit_ref が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.unit_ref == r.unit_ref, f"[{i}]"

    def test_is_nil_match(self, e2e_data):
        """全 LineItem の is_nil が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.is_nil == r.is_nil, f"[{i}]"

    def test_order_match(self, e2e_data):
        """全 LineItem の order が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.order == r.order, f"[{i}]"

    def test_source_line_match(self, e2e_data):
        """全 LineItem の source_line が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.source_line == r.source_line, f"[{i}]"

    def test_entity_id_match(self, e2e_data):
        """全 LineItem の entity_id が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for i, (o, r) in enumerate(zip(os, rs)):
                assert o.entity_id == r.entity_id, f"[{i}]"


# ------------------------------------------------------------------
# 財務諸表メソッド比較
# ------------------------------------------------------------------

class TestStatementMethods:
    """income_statement / balance_sheet 等の出力比較。"""

    def test_income_statement(self, e2e_data):
        """income_statement() のアイテム数・科目名が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_pl = os.income_statement()
            rest_pl = rs.income_statement()
            assert len(orig_pl) == len(rest_pl)
            for o, r in zip(orig_pl, rest_pl):
                assert o.local_name == r.local_name

    def test_balance_sheet(self, e2e_data):
        """balance_sheet() のアイテム数・科目名が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_bs = os.balance_sheet()
            rest_bs = rs.balance_sheet()
            assert len(orig_bs) == len(rest_bs)
            for o, r in zip(orig_bs, rest_bs):
                assert o.local_name == r.local_name

    def test_cash_flow_statement(self, e2e_data):
        """cash_flow_statement() のアイテム数・科目名が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_cf = os.cash_flow_statement()
            rest_cf = rs.cash_flow_statement()
            assert len(orig_cf) == len(rest_cf)

    def test_income_statement_period_current(self, e2e_data):
        """income_statement(period="current") が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_pl = os.income_statement(period="current")
            rest_pl = rs.income_statement(period="current")
            assert len(orig_pl) == len(rest_pl)

    def test_income_statement_period_prior(self, e2e_data):
        """income_statement(period="prior") が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_pl = os.income_statement(period="prior")
            rest_pl = rs.income_statement(period="prior")
            assert len(orig_pl) == len(rest_pl)

    def test_balance_sheet_period(self, e2e_data):
        """balance_sheet() の period が一致する。"""
        from xbrl_core.periods import InstantPeriod

        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_bs = os.balance_sheet()
            rest_bs = rs.balance_sheet()
            assert type(orig_bs.period) is type(rest_bs.period)
            if isinstance(orig_bs.period, InstantPeriod):
                assert orig_bs.period.instant == rest_bs.period.instant

    def test_statement_values(self, e2e_data):
        """各財務諸表の value が一致する（全科目）。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for method_name in ("income_statement", "balance_sheet"):
                orig_stmt = getattr(os, method_name)()
                rest_stmt = getattr(rs, method_name)()
                for o, r in zip(orig_stmt, rest_stmt):
                    if isinstance(o.value, Decimal):
                        assert float(o.value) == float(r.value), (
                            f"{method_name}: {o.local_name}"
                        )
                    else:
                        assert o.value == r.value, (
                            f"{method_name}: {o.local_name}"
                        )


# ------------------------------------------------------------------
# extract_values 比較
# ------------------------------------------------------------------

class TestExtractValues:
    """extract_values() の出力比較。"""

    def test_default_pipeline_keys_match(self, e2e_data):
        """デフォルトパイプラインで取得されるキーが一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os)
            rest_ev = extract_values(rs)
            assert set(orig_ev.keys()) == set(rest_ev.keys()), (
                f"orig_only={set(orig_ev) - set(rest_ev)}, "
                f"rest_only={set(rest_ev) - set(orig_ev)}"
            )

    def test_default_pipeline_values_match(self, e2e_data):
        """デフォルトパイプラインの全値が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os)
            rest_ev = extract_values(rs)
            for key in orig_ev:
                ov = orig_ev[key]
                rv = rest_ev[key]
                if ov is None:
                    assert rv is None, f"[{key}]"
                else:
                    assert rv is not None, f"[{key}]"
                    if isinstance(ov.value, Decimal) and isinstance(rv.value, Decimal):
                        assert float(ov.value) == float(rv.value), f"[{key}]"
                    else:
                        assert ov.value == rv.value, f"[{key}]"

    def test_specific_pl_keys(self, e2e_data):
        """PL 主要キーの抽出値が一致する。"""
        keys = [CK.REVENUE, CK.OPERATING_INCOME, CK.ORDINARY_INCOME,
                CK.NET_INCOME_PARENT, CK.EPS]
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, keys)
            rest_ev = extract_values(rs, keys)
            for key in keys:
                ov = orig_ev.get(key)
                rv = rest_ev.get(key)
                if ov is not None:
                    assert rv is not None, f"[{key}] None in restored"
                    if isinstance(ov.value, Decimal) and isinstance(rv.value, Decimal):
                        assert float(ov.value) == float(rv.value), f"[{key}]"

    def test_specific_bs_keys(self, e2e_data):
        """BS 主要キーの抽出値が一致する。"""
        keys = [CK.TOTAL_ASSETS, CK.NET_ASSETS, CK.SHAREHOLDERS_EQUITY]
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, keys)
            rest_ev = extract_values(rs, keys)
            for key in keys:
                ov = orig_ev.get(key)
                rv = rest_ev.get(key)
                if ov is not None:
                    assert rv is not None, f"[{key}]"
                    if isinstance(ov.value, Decimal) and isinstance(rv.value, Decimal):
                        assert float(ov.value) == float(rv.value), f"[{key}]"

    def test_dps_keys(self, e2e_data):
        """DPS 関連キーが一致する。"""
        keys = [CK.DPS, CK.INTERIM_DPS, CK.FORECAST_DPS]
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, keys)
            rest_ev = extract_values(rs, keys)
            for key in keys:
                ov = orig_ev.get(key)
                rv = rest_ev.get(key)
                if ov is not None:
                    assert rv is not None, f"[{key}]"

    def test_forecast_keys(self, e2e_data):
        """業績予想キーが一致する。"""
        keys = [CK.FORECAST_REVENUE, CK.FORECAST_OPERATING_INCOME,
                CK.FORECAST_ORDINARY_INCOME, CK.FORECAST_NET_INCOME_PARENT,
                CK.FORECAST_EPS]
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, keys)
            rest_ev = extract_values(rs, keys)
            for key in keys:
                ov = orig_ev.get(key)
                rv = rest_ev.get(key)
                if ov is not None:
                    assert rv is not None, f"[{key}]"
                    if isinstance(ov.value, Decimal) and isinstance(rv.value, Decimal):
                        assert float(ov.value) == float(rv.value), f"[{key}]"

    def test_period_current(self, e2e_data):
        """period="current" での抽出が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, period="current")
            rest_ev = extract_values(rs, period="current")
            assert set(orig_ev.keys()) == set(rest_ev.keys())

    def test_period_prior(self, e2e_data):
        """period="prior" での抽出が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, period="prior")
            rest_ev = extract_values(rs, period="prior")
            assert set(orig_ev.keys()) == set(rest_ev.keys())

    def test_extracted_to_dict(self, e2e_data):
        """extracted_to_dict() の結果が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_dict = extracted_to_dict(extract_values(os))
            rest_dict = extracted_to_dict(extract_values(rs))
            assert set(orig_dict.keys()) == set(rest_dict.keys())
            for key in orig_dict:
                ov = orig_dict[key]
                rv = rest_dict[key]
                if isinstance(ov, Decimal) and isinstance(rv, Decimal):
                    assert float(ov) == float(rv), f"[{key}]"
                else:
                    assert ov == rv, f"[{key}]"


# ------------------------------------------------------------------
# カスタムマッパー比較
# ------------------------------------------------------------------

class TestCustomMapper:
    """カスタムマッパーの結果比較。"""

    def test_dict_mapper(self, e2e_data):
        """dict_mapper でカスタムキー抽出結果が一致する。"""
        custom = dict_mapper({
            "NetSales": "MY_REVENUE",
            "OperatingIncome": "MY_OP",
            "TotalAssets": "MY_ASSETS",
            "OrdinaryIncome": "MY_ORDINARY",
        }, name="e2e_custom")

        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, mapper=[custom])
            rest_ev = extract_values(rs, mapper=[custom])
            assert set(orig_ev.keys()) == set(rest_ev.keys())
            for key in orig_ev:
                ov = orig_ev[key]
                rv = rest_ev[key]
                if ov is not None and rv is not None:
                    if isinstance(ov.value, Decimal) and isinstance(rv.value, Decimal):
                        assert float(ov.value) == float(rv.value), f"[{key}]"

    def test_mixed_pipeline(self, e2e_data):
        """カスタム + 標準の混合パイプラインが一致する。"""
        custom = dict_mapper({"NetSales": "OVERRIDE_SALES"}, name="override")
        pipeline = [custom, summary_mapper, statement_mapper]

        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, mapper=pipeline)
            rest_ev = extract_values(rs, mapper=pipeline)
            assert set(orig_ev.keys()) == set(rest_ev.keys())
            # カスタムキーが存在するか
            if "OVERRIDE_SALES" in orig_ev:
                assert "OVERRIDE_SALES" in rest_ev

    def test_summary_mapper_only(self, e2e_data):
        """summary_mapper 単独で結果が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, mapper=[summary_mapper])
            rest_ev = extract_values(rs, mapper=[summary_mapper])
            assert set(orig_ev.keys()) == set(rest_ev.keys())

    def test_statement_mapper_only(self, e2e_data):
        """statement_mapper 単独で結果が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, mapper=[statement_mapper])
            rest_ev = extract_values(rs, mapper=[statement_mapper])
            assert set(orig_ev.keys()) == set(rest_ev.keys())


# ------------------------------------------------------------------
# search / __getitem__ / __contains__ / __len__
# ------------------------------------------------------------------

class TestSearchAndLookup:
    """検索・参照系メソッドの比較。"""

    def test_len(self, e2e_data):
        """__len__ が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            assert len(os) == len(rs)

    def test_search_results_match(self, e2e_data):
        """代表的なキーワードで search() 結果が一致する。"""
        keywords = ["売上", "利益", "資産", "Operating", "Assets", "Net"]
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for kw in keywords:
                orig_results = os.search(kw)
                rest_results = rs.search(kw)
                assert len(orig_results) == len(rest_results), f"search('{kw}')"
                for o, r in zip(orig_results, rest_results):
                    assert o.local_name == r.local_name

    def test_getitem_by_local_name(self, e2e_data):
        """実在する local_name で __getitem__ が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            # 最初の5科目で比較
            for item in list(os)[:5]:
                orig_item = os[item.local_name]
                rest_item = rs[item.local_name]
                assert orig_item.local_name == rest_item.local_name
                if isinstance(orig_item.value, Decimal):
                    assert float(orig_item.value) == float(rest_item.value)
                else:
                    assert orig_item.value == rest_item.value

    def test_contains(self, e2e_data):
        """__contains__ が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for item in list(os)[:10]:
                assert (item.local_name in os) == (item.local_name in rs)
            assert ("NonExistentConcept12345" in os) == ("NonExistentConcept12345" in rs)


# ------------------------------------------------------------------
# to_dataframe 比較
# ------------------------------------------------------------------

class TestToDataframe:
    """to_dataframe() の出力比較。"""

    def test_shape(self, e2e_data):
        """DataFrame の shape が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            assert os.to_dataframe().shape == rs.to_dataframe().shape

    def test_columns(self, e2e_data):
        """DataFrame のカラムが一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            assert list(os.to_dataframe().columns) == list(rs.to_dataframe().columns)

    def test_label_ja_column(self, e2e_data):
        """label_ja カラムが一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_df = os.to_dataframe()
            rest_df = rs.to_dataframe()
            assert list(orig_df["label_ja"]) == list(rest_df["label_ja"])

    def test_local_name_column(self, e2e_data):
        """local_name カラムが一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_df = os.to_dataframe()
            rest_df = rs.to_dataframe()
            assert list(orig_df["local_name"]) == list(rest_df["local_name"])

    def test_value_column(self, e2e_data):
        """value カラムが一致する（NaN 含む）。"""
        import math

        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_df = os.to_dataframe()
            rest_df = rs.to_dataframe()
            for i, (ov, rv) in enumerate(
                zip(orig_df["value"], rest_df["value"])
            ):
                if isinstance(ov, float) and math.isnan(ov):
                    assert isinstance(rv, float) and math.isnan(rv), f"[{i}]"
                else:
                    assert ov == rv, f"[{i}]"

    def test_financial_statement_dataframe(self, e2e_data):
        """FinancialStatement.to_dataframe() の shape が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            for method in ("income_statement", "balance_sheet"):
                orig_stmt = getattr(os, method)()
                rest_stmt = getattr(rs, method)()
                orig_df = orig_stmt.to_dataframe()
                rest_df = rest_stmt.to_dataframe()
                assert orig_df.shape == rest_df.shape, method

    def test_financial_statement_to_dict(self, e2e_data):
        """FinancialStatement.to_dict() の件数が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_dicts = os.income_statement().to_dict()
            rest_dicts = rs.income_statement().to_dict()
            assert len(orig_dicts) == len(rest_dicts)
            for od, rd in zip(orig_dicts, rest_dicts):
                assert od["concept"] == rd["concept"]
                assert od["label_ja"] == rd["label_ja"]


# ------------------------------------------------------------------
# サマリー出力（目視用情報を構造比較）
# ------------------------------------------------------------------

class TestSummaryDisplay:
    """人間が見るようなサマリー情報が一致するか。"""

    def test_extract_summary_current(self, e2e_data):
        """当期サマリー（主要 CK）の表示用辞書が一致する。"""
        keys = [
            CK.REVENUE, CK.OPERATING_INCOME, CK.ORDINARY_INCOME,
            CK.NET_INCOME_PARENT, CK.EPS, CK.DPS,
            CK.TOTAL_ASSETS, CK.NET_ASSETS, CK.EQUITY_RATIO, CK.BPS,
        ]
        for (of, os), (rf, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os, keys, period="current")
            rest_ev = extract_values(rs, keys, period="current")
            orig_summary = {
                k: (float(v.value) if v and isinstance(v.value, Decimal) else
                    v.value if v else None)
                for k, v in orig_ev.items()
            }
            rest_summary = {
                k: (float(v.value) if v and isinstance(v.value, Decimal) else
                    v.value if v else None)
                for k, v in rest_ev.items()
            }
            assert orig_summary == rest_summary, (
                f"{of.company_code}: {orig_summary} != {rest_summary}"
            )

    def test_mapper_name_match(self, e2e_data):
        """extract_values() の mapper_name が一致する。"""
        for (_, os), (_, rs) in zip(_originals(e2e_data), _restored(e2e_data)):
            orig_ev = extract_values(os)
            rest_ev = extract_values(rs)
            for key in orig_ev:
                ov = orig_ev[key]
                rv = rest_ev[key]
                if ov is not None and rv is not None:
                    assert ov.mapper_name == rv.mapper_name, f"[{key}]"
