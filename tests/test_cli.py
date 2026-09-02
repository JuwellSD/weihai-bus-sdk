"""CLI 的冒烟测试 (需要网络,复用 weihai_bus.cli.app)。"""

import os

import pytest
from typer.testing import CliRunner

from weihai_bus.cli import app

ONLINE = os.environ.get("WEIHAI_ONLINE", "1") == "1"
runner = CliRunner()


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_cli_routes():
    r = runner.invoke(app, ["routes", "1路"])
    assert r.exit_code == 0
    assert "routeId" in r.stdout


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_cli_stops():
    r = runner.invoke(app, ["stops", "威海九中"])
    assert r.exit_code == 0
    assert "威海九中" in r.stdout


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_cli_routes_json():
    r = runner.invoke(app, ["routes", "1路", "--json"])
    assert r.exit_code == 0
    assert "route_id" in r.stdout


def test_cli_vehicles_requires_arg():
    r = runner.invoke(app, ["vehicles"])
    assert r.exit_code == 2  # BadParameter 触发退出 2