"""对逆向所得 API 的冒烟测试。

这些测试会真实请求线上接口。需要网络环境,且假设威海 (city=371000)
免授权通道 (h5Platform=2) 可用。
"""

import os
import sys

import pytest

from weihai_bus import BusClient

# 允许通过环境变量跳过在线测试
ONLINE = os.environ.get("WEIHAI_ONLINE", "1") == "1"


@pytest.fixture
def client():
    with BusClient() as c:
        yield c


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_find_route_by_name(client: BusClient):
    r = client.find_route_by_name("1路")
    assert r.total > 0
    assert len(r.items) > 0
    route = r.items[0].routes[0]
    assert route.route_id > 0
    assert route.route_name
    assert route.station_cnt > 0


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_find_stop_by_name(client: BusClient):
    r = client.find_stop_by_name("威海九中")
    assert r.total > 0
    stop = r.items[0].stops[0]
    assert stop.stop_id > 0
    assert stop.stop_name


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_find_nearby_stop(client: BusClient):
    r = client.find_nearby_stop(radius=2000)
    assert r.total > 0
    if r.items:
        entry = r.items[0].stops[0]
        assert entry.stop.stop_id > 0


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_get_bus_position(client: BusClient):
    route = client.find_route_by_name("1路").items[0].routes[0]
    pos = client.get_bus_position(route.route_id)
    assert pos is not None
    assert len(pos.stops) > 0
    assert pos.stops[0].route_stop.stop_id > 0


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_get_next_bus_by_stop(client: BusClient):
    stop = client.find_stop_by_name("威海九中").items[0].stops[0]
    nbs = client.get_next_bus_by_stop(stop.stop_id)
    assert isinstance(nbs, list)


@pytest.mark.skipif(not ONLINE, reason="offline mode")
def test_get_next_bus_by_route_stop(client: BusClient):
    route = client.find_route_by_name("1路").items[0].routes[0]
    stop = client.find_stop_by_name("威海九中").items[0].stops[0]
    r = client.get_next_bus_by_route_stop(route.route_id, stop.stop_id)
    # 可能无数据返回 None
    assert r is None or r.next_buses is not None