from _typeshed import Incomplete

class TdnetWarning(UserWarning):
    """tdnet ライブラリが発行する warning の基底クラス。"""
class TdnetError(Exception):
    """tdnet ライブラリの基底例外。"""
class TdnetConfigError(TdnetError):
    """設定に関するエラー。"""

class TdnetAPIError(TdnetError):
    """TDnet からのエラー。"""
    status_code: Incomplete
    def __init__(self, status_code: int, message: str) -> None: ...

class TdnetParseError(TdnetError):
    """取得済みデータの解析に失敗した。"""
