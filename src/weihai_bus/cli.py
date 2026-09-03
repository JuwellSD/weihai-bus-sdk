"""weihai-bus 的命令行接口 (CLI)。

在终端直接查询威海实时公交:

.. code-block:: text

    $ weihai routes 1路
    $ weihai vehicles 3710000100128319 --name
    $ weihai stops 威海九中
    $ weihai nearby --radius 2000
    $ weihai next-at-stop 3710000100094159
    $ weihai next 3710000100564252 3710000100564252

所有命令默认输出人读文本;加 ``--json`` 输出机器可解析的 JSON。
"""

from __future__ import annotations

import json
from typing import Optional

import typer

from .client import BusClient

app = typer.Typer(
    name="weihai",
    help="威海 (timebus.ibuscloud.com) 实时公交查询 CLI",
    no_args_is_help=True,
)


def _mk_client(
    city: str,
    platform: str,
    timeout: float,
) -> BusClient:
    return BusClient(city=city, h5_platform=platform, timeout=timeout)


def _print(data: object, as_json: bool) -> None:
    """按 --json 与否打印结果。"""
    if as_json:
        print(json.dumps(data, ensure_ascii=False, default=str))
        return
    print(data)


# ---------------------------------------------------------------------- #
# 线路
# ---------------------------------------------------------------------- #


def _format_route_list(r, verbose: bool) -> str:
    lines = []
    for item in r.items:
        for rt in item.routes:
            head = f"{rt.route_name}  routeId={rt.route_id}"
            if verbose:
                head += (
                    f"  {rt.origin} -> {rt.terminal}"
                    f"  站数={rt.station_cnt}"
                    f"  首/末={rt.first_bus}/{rt.last_bus}"
                )
            lines.append(head)
    if not lines:
        return "(无结果)"
    return "\n".join(lines)


def _operational_note(
    first_bus: str,
    last_bus: str,
    now: Optional["datetime.datetime"] = None,
) -> Optional[str]:
    """根据首末班时间与当前时刻,生成运营状态提示。

    若当前时刻在运营时段内,返回 ``None``(由车辆数据本身反映运行)。
    若在时段外(未发车或已收班),返回与官方 App 一致的中文文案。
    """
    from datetime import datetime

    now = now or datetime.now()
    try:
        ft = datetime.strptime(first_bus, "%H:%M:%S").time()
        lt = datetime.strptime(last_bus, "%H:%M:%S").time()
    except (ValueError, TypeError):
        return None  # 首末班缺失或格式异常,无法判断则不加提示

    t = now.time()
    if t < ft:
        return f"非车辆运营时间（{first_bus[:5]} 发车）"
    if t >= lt:
        return "非车辆运营时间（已过末班）"
    return None


@app.command("routes")
def routes_cmd(
    name: str = typer.Argument(..., help="线路名关键字，如 1路"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示站点数、首末班等详情"),
    city: str = typer.Option("371000", help="城市码或 type 值，默认威海"),
    platform: str = typer.Option("2", help="h5Platform，默认2(免授权)"),
    timeout: float = typer.Option(10.0, help="请求超时(秒)"),
    json_out: bool = typer.Option(False, "--json", help="输出 JSON"),
):
    """按线路名搜索线路。"""
    r = _mk_client(city, platform, timeout).find_route_by_name(name)
    if json_out:
        _print([i.model_dump() for i in r.items], True)
        return
    print(_format_route_list(r, verbose))


# ---------------------------------------------------------------------- #
# 车辆实时位置
# ---------------------------------------------------------------------- #


@app.command("vehicles")
def vehicles_cmd(
    route_id: Optional[int] = typer.Argument(None, help="线路 routeId"),
    name: str = typer.Option(None, "--name", help="按线路名直接定位(无需 routeId)"),
    city: str = typer.Option("371000"),
    platform: str = typer.Option("2"),
    timeout: float = typer.Option(10.0),
    json_out: bool = typer.Option(False, "--json"),
):
    """查询一条线路的车辆实时位置。"""
    if route_id is None and name is not None:
        c = _mk_client(city, platform, timeout)
        rt = c.route_real_time(name)
        if rt is None:
            print("(未找到该线路实时数据)")
            raise typer.Exit(2)
        route_id = rt.route.route_id
    elif route_id is None:
        raise typer.BadParameter("需提供 routeId 或 --name")

    c = _mk_client(city, platform, timeout)
    pos = c.get_bus_position(route_id)
    if pos is None:
        print("(该线路实时数据不可用)")
        raise typer.Exit(1)

    if json_out:
        _print(pos.model_dump(), True)
        return

    print(f"{pos.route.route_name}  ({pos.route.origin} -> {pos.route.terminal})")
    for entry in pos.stops:
        s = entry.route_stop
        n = len(entry.buses)
        mark = f"  [{n}车] " if n else ""
        print(f"  {s.seq_no:>3}. {s.stop_name}{mark}")
    nb = pos.next_buses
    has_bus = any(len(e.buses) for e in pos.stops) or bool(nb.buses)
    if nb.stop_id:
        desc = nb.no_bus_desc or (f"{len(nb.buses)} 车" if nb.buses else " ")
        print(f"末/途经站点预报: {nb.stop_name}  {desc}")

    # 无在线车辆时,按首末班时间给出与官方 App 一致的运营状态提示
    if not has_bus and not json_out:
        note = _operational_note(pos.route.first_bus, pos.route.last_bus)
        if note:
            print(f"状态: {note}")


# ---------------------------------------------------------------------- #
# 站点
# ---------------------------------------------------------------------- #


@app.command("stops")
def stops_cmd(
    name: str = typer.Argument(..., help="站点名，如 威海九中"),
    routes: bool = typer.Option(False, "--routes", "-r", help="列出途经线路"),
    city: str = typer.Option("371000"),
    platform: str = typer.Option("2"),
    timeout: float = typer.Option(10.0),
    json_out: bool = typer.Option(False, "--json"),
):
    """按站点名搜索站点。"""
    r = _mk_client(city, platform, timeout).find_stop_by_name(name)
    if json_out:
        _print(
            [
                {
                    "name": item.name,
                    "stops": [s.model_dump() for s in item.stops],
                }
                for item in r.items
            ],
            True,
        )
        return
    for item in r.items:
        for s in item.stops:
            line = f"{s.stop_name}  stopId={s.stop_id}  ({s.lat:.4f}, {s.lng:.4f})"
            print(line)
            if routes:
                for rinfo in s.route_infos:
                    print(f"    {rinfo.route_name}  routeId={rinfo.route_id}")
    if not r.items:
        print("(无结果)")


@app.command("nearby")
def nearby_cmd(
    radius: int = typer.Option(1000, help="搜索半径(米)"),
    lat: Optional[float] = typer.Option(None, help="纬度，缺省用城市中心"),
    lng: Optional[float] = typer.Option(None, help="经度，缺省用城市中心"),
    routes: bool = typer.Option(False, "--routes", "-r"),
    city: str = typer.Option("371000"),
    platform: str = typer.Option("2"),
    timeout: float = typer.Option(10.0),
    json_out: bool = typer.Option(False, "--json"),
):
    """搜索附近的站点。"""
    r = _mk_client(city, platform, timeout).find_nearby_stop(
        lat=lat, lng=lng, radius=radius
    )
    if json_out:
        _print(
            [{"name": i.stop_name, "stops": [e.model_dump() for e in i.stops]} for i in r.items],
            True,
        )
        return
    for item in r.items:
        print(f"📍 {item.stop_name}")
        for e in item.stops:
            s = e.stop
            extra = f"  routes={e.route_count}" if routes else ""
            print(f"    {s.stop_name}  stopId={s.stop_id}{extra}")
    if not r.items:
        print("(附近无站点)")


# ---------------------------------------------------------------------- #
# 下一班车
# ---------------------------------------------------------------------- #


@app.command("next-at-stop")
def next_at_stop_cmd(
    stop_id: int = typer.Argument(..., help="站点 stopId"),
    city: str = typer.Option("371000"),
    platform: str = typer.Option("2"),
    timeout: float = typer.Option(10.0),
    json_out: bool = typer.Option(False, "--json"),
):
    """查询经过某站点的各线路下一班车。"""
    nbs = _mk_client(city, platform, timeout).get_next_bus_by_stop(stop_id)
    if json_out:
        _print([nb.model_dump() for nb in nbs], True)
        return
    for nb in nbs:
        desc = nb.no_bus_desc or (f"{len(nb.buses)} 车" if nb.buses else "-")
        print(f"{nb.stop_name or stop_id}:  {desc}")
    if not nbs:
        print("(该站点无线路数据)")


@app.command("next")
def next_cmd(
    route_id: int = typer.Argument(..., help="线路 routeId"),
    stop_id: int = typer.Argument(..., help="站点 stopId"),
    city: str = typer.Option("371000"),
    platform: str = typer.Option("2"),
    timeout: float = typer.Option(10.0),
    json_out: bool = typer.Option(False, "--json"),
):
    """查询某条线路在某个站点的下一班车。"""
    r = _mk_client(city, platform, timeout).get_next_bus_by_route_stop(
        route_id, stop_id
    )
    if json_out:
        _print(r.model_dump() if r else None, True)
        return
    if r is None:
        print("(无数据)")
        return
    nb = r.next_buses
    print(f"站点: {nb.stop_name or stop_id}")
    print(f"预报: {nb.no_bus_desc or (str(len(nb.buses))+' 车' if nb.buses else '-')}")


if __name__ == "__main__":
    app()