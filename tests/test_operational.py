"""运营状态判断的纯逻辑测试 (不需要网络)。"""

import datetime

from typer.testing import CliRunner

from weihai_bus.cli import _operational_note

runner = CliRunner()


def _t(h: int, m: int = 0, s: int = 0) -> datetime.datetime:
    return datetime.datetime(2026, 9, 3, h, m, s)


# 2 路上行首末班: 06:00 / 21:40
FIRST, LAST = "06:00:00", "21:40:00"


def test_before_operation():
    """首班前应提示发车时间。"""
    assert _operational_note(FIRST, LAST, _t(5, 59)) == "非车辆运营时间（06:00 发车）"


def test_midnight():
    """凌晨(首班前)应提示发车时间。"""
    assert _operational_note(FIRST, LAST, _t(0, 30)) == "非车辆运营时间（06:00 发车）"


def test_in_operation():
    """运营时段内不误报。"""
    assert _operational_note(FIRST, LAST, _t(6, 0)) is None
    assert _operational_note(FIRST, LAST, _t(12, 0)) is None
    assert _operational_note(FIRST, LAST, _t(21, 39)) is None


def test_at_last_bus_is_over():
    """恰好到末班时间点视为已过。"""
    assert _operational_note(FIRST, LAST, _t(21, 40)) == "非车辆运营时间（已过末班）"


def test_malformed_times_are_silent():
    """首末班缺失或格式异常时不加提示。"""
    assert _operational_note("", "", _t(12, 0)) is None
    assert _operational_note(None, None, _t(12, 0)) is None
    assert _operational_note("abc", "def", _t(12, 0)) is None


def test_default_now_uses_current_time():
    """不传 now 时用系统当前时间(在此调用仅验证不抛异常)。"""
    r = _operational_note(FIRST, LAST)
    assert r is None or r.startswith("非车辆运营时间")