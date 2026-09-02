"""实时公交 API 的 pydantic 数据模型。

字段严格按照逆向得到的接口响应建模,大部分字段为可选,以便在接口
字段微调时保持兼容。所有模型 ``extra`` 默认忽略多余字段。
"""

from __future__ import annotations

import re
from typing import Any, List, Optional

from pydantic import (
    AliasGenerator,
    BaseModel,
    ConfigDict,
    Field,
)

#: 把 snake_case 字段名自动转成平台使用的 camelCase 别名。
#: 例如 ``route_id`` -> 别名 ``routeId``。
_ALIAS_GEN = AliasGenerator(
    serialization_alias=lambda name: re.sub(r"_(\w)", lambda m: m.group(1).upper(), name),
    validation_alias=lambda name: re.sub(r"_(\w)", lambda m: m.group(1).upper(), name),
)


class _Strict(BaseModel):
    """通用配置:字段名自动映射 camelCase 别名,宽松解析,忽略未知字段。"""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        alias_generator=_ALIAS_GEN,
    )


class RouteTags(_Strict):
    metro_trans_line: int = 0
    stop_on_demand: int = 0
    night_route: int = 0


class Route(_Strict):
    """一条线路。

    注意:搜索接口 (findRouteByName) 返回的 route 比实时位置接口
    (getBusPositionByRouteId) 简略,缺少部分字段。故除核心标识符外
    全部给默认值,以兼容两种形态。
    """

    route_id: int
    opposite_id: Optional[int] = None
    route_name: str = ""
    amap_id: Optional[int] = None
    opposite_amap_id: Optional[int] = None
    amap_name: str = ""
    city_code: str = ""
    city_name: str = ""
    direction: Optional[int] = None
    origin: str = ""
    origin_id: Optional[int] = None
    terminal: str = ""
    air_price: Optional[float] = None
    carfare: str = ""
    first_bus: str = ""
    last_bus: str = ""
    station_cnt: Optional[int] = None
    distance: Optional[float] = None
    regular: bool = False
    has_gps: bool = False
    favorite: bool = False
    route_no: Optional[int] = None
    subsidiary: Optional[int] = None
    rout_name_tag: str = ""
    route_no_name_tag: str = ""
    route_tags: RouteTags = Field(default_factory=RouteTags)


class Stop(_Strict):
    stop_id: int
    stop_name: str
    city_code: str
    city_name: str
    lng: float
    lat: float
    metro_trans: bool = False
    district_code: str = ""
    favorite: bool = False

    #: 途经该站点的线路 (findStopByName / findNearbyStop 时存在)
    route_infos: List[Route] = Field(default_factory=list)


class RouteSearchItem(_Strict):
    """按线路名搜索返回的一项：一个线路名下的所有方向。"""

    name: str
    routes: List[Route]


class StopSearchItem(_Strict):
    """按站点名搜索返回的一项：一个站点名下的所有站点。"""

    name: str
    stops: List[Stop]


class Bus(_Strict):
    """一辆车的一次进站预报。

    车辆字段在夜间 (非运营时段) 返回空数组,逐字段命名未经完整实测,
    故全部宽松建模 (Optional),以兼容线上实际字段。
    """

    route_id: Optional[int] = None
    stop_id: Optional[int] = None
    seq_no: Optional[int] = None
    stop_name: Optional[str] = None
    target_distance: Optional[Any] = None
    plate_no: Optional[str] = None
    bus_no: Optional[str] = None
    direction: Optional[int] = None
    distance: Optional[float] = None
    arrive_time: Optional[str] = None
    data_status: Optional[int] = None


class NextBus(_Strict):
    """一个站点/线路的下一班车预报。"""

    route_id: Optional[int] = None
    seq_no: Optional[int] = None
    stop_id: Optional[int] = None
    amap_route_id: Optional[int] = None
    stop_name: str = ""
    alert: bool = False
    no_bus_desc: str = ""
    type: int = 0
    buses: List[Bus] = Field(default_factory=list)


class StopOnRoute(_Strict):
    """线路途经的一个站点 (getNextBusByRouteStopId 返回)。"""

    route_id: int
    stop_id: int
    stop_name: str
    seq_no: int
    buses: List[Bus] = Field(default_factory=list)


class RouteStop(_Strict):
    """车辆实时位置响应里的一个站点 (getBusPositionByRouteId)。"""

    sta_id: int
    route_id: int
    seq_no: int
    type: int
    direction: int
    stop_id: int
    stop_name: str
    city_code: str
    city_name: str
    lng: float
    lat: float
    metro_trans: bool = False
    favorite: bool = False
    metro_lines: str = ""
    rout_name_tag: str = ""
    route_no_name_tag: str = ""
    route_tags: RouteTags = Field(default_factory=RouteTags)


class PositionedBus(_Strict):
    """实时位置里的一辆车。"""

    bus_id: Optional[int] = None
    plate_no: Optional[str] = None
    lng: Optional[float] = None
    lat: Optional[float] = None
    direction: Optional[int] = None
    speed: Optional[float] = None
    seq_no: Optional[int] = None
    stop_id: Optional[int] = None
    status: Optional[int] = None
    route_id: Optional[int] = None


class RouteStopEntry(_Strict):
    """实时位置里一个站点条目,包含站点信息与到达该站的车辆。"""

    route_stop: RouteStop = Field(default_factory=RouteStop)
    buses: List[Bus] = Field(default_factory=list)


class NearbyStopEntry(_Strict):
    """附近站点搜索 (findNearbyStop) 里的一个站点条目。"""

    stop: Stop = Field(default_factory=Stop)
    route_count: int = 0
    routes: List[Any] = Field(default_factory=list)


class NearbyStopItem(_Strict):
    """附近站点搜索返回的一项。"""

    stop_name: str = ""
    stops: List[NearbyStopEntry] = Field(default_factory=list)


class RouteRealTime(_Strict):
    """一条线路方向的实时信息 (getBusPositionByRouteId 的 route detail)。"""

    route: Route = Field(default_factory=Route)
    next_buses: NextBus = Field(default_factory=NextBus)
    stops: List[RouteStopEntry] = Field(default_factory=list)
    maas_route_flag: bool = False


class RouteRealTimeItem(_Strict):
    """线路实时位置的一个 item,含线路名与若干方向。"""

    route_name: str = ""
    routes: List[RouteRealTime] = Field(default_factory=list)

    @property
    def first(self) -> Optional[RouteRealTime]:
        """取第一个方向的实时信息。"""
        return self.routes[0] if self.routes else None


class BusPositionResult(_Strict):
    """实时位置的完整 item 包装。"""

    items: List[RouteRealTimeItem] = Field(default_factory=list)

    @property
    def first(self) -> Optional[RouteRealTime]:
        """取第一个线路方向的实时信息。"""
        for item in self.items:
            if item.first is not None:
                return item.first
        return None


class RouteStopNextBusResult(_Strict):
    """getNextBusByRouteStopId 返回的 single-item。"""

    route_id: int
    next_buses: NextBus
    stops: List[StopOnRoute] = Field(default_factory=list)


#: 通用列表/分页响应 (findRouteByName / findStopByName / findNearbyStop)
class ListResult(_Strict):
    result: int
    message: str = ""
    total: int = 0
    page_count: int = 0
    items: List[Any] = Field(default_factory=list)


#: 汽车位置/下一班车等返回 items 数据的响应
class QueryListResult(ListResult):
    items: List[Any] = Field(default_factory=list)