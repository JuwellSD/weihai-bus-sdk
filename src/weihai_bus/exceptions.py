"""实时公交 API 的自定义异常。"""

from __future__ import annotations

from typing import Optional


class IbusCloudError(Exception):
    """API 返回的已知业务错误。

    携带 ``result`` 错误码与 ``message`` 描述。
    """

    def __init__(self, result: int, message: str):
        self.result = result
        super().__init__(f"[{result}] {message}")


class IbusCloudHTTPError(Exception):
    """HTTP 层错误 (非 2xx / 网络异常 / 超时)。"""

    def __init__(self, msg: str, status_code: Optional[int] = None):
        self.status_code = status_code
        tail = f" (HTTP {status_code})" if status_code else ""
        super().__init__(msg + tail)