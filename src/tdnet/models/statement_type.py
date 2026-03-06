"""財務諸表の種類。"""

import enum


class StatementType(enum.Enum):
    INCOME_STATEMENT = 'income_statement'
    BALANCE_SHEET = 'balance_sheet'
    CASH_FLOW_STATEMENT = 'cash_flow_statement'
    STATEMENT_OF_CHANGES_IN_EQUITY = 'statement_of_changes_in_equity'
    COMPREHENSIVE_INCOME = 'comprehensive_income'
