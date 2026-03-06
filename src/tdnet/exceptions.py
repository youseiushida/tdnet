"""tdnet ライブラリの例外・警告クラス。"""

from __future__ import annotations


class TdnetWarning(UserWarning):
    """tdnet ライブラリが発行する warning の基底クラス。"""


class TdnetError(Exception):
    """tdnet ライブラリの基底例外。"""


class TdnetConfigError(TdnetError):
    """設定に関するエラー。"""


class TdnetAPIError(TdnetError):
    """TDnet からのエラー。"""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class TdnetParseError(TdnetError):
    """取得済みデータの解析に失敗した。"""
