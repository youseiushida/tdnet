__all__ = ['lookup_statement', 'lookup_statement_exact', 'lookup_statement_normalized']

def lookup_statement_exact(concept: str) -> str | None:
    """辞書完全一致のみで CK を返す。"""
def lookup_statement_normalized(concept: str) -> str | None:
    """正規化フォールバック: IFRS / REIT サフィックスを除去して再検索。

    TDnet の IFRS 添付財務諸表では概念名に ``IFRS`` サフィックスが付く
    (例: ``FinanceIncomeIFRS``, ``CostOfSalesIFRS``)。
    サフィックスを除去して基底辞書を再検索する。
    """
def lookup_statement(concept: str) -> str | None:
    """PL/BS/CF の concept から CK を返す。完全一致 → サフィックス除去の順。"""
