"""实时公交 (timebus.ibuscloud.com) 非官方 Python SDK。

用法示例::

    from weihai_bus import BusClient

    client = BusClient()  # 默认威海 city + 免授权 h5Platform=2

    # 按线路名搜索 (返回该线路名的所有方向)
    result = client.find_route_by_name("1路")
    for item in result.items:
        print(item.name, [r.route_name for r in item.routes])

    # 按站点名搜索
    stops = client.find_stop_by_name("威海九中")

    # 某线路车辆实时位置
    route = client.find_route_by_name("1路").items[0].routes[0]
    pos = client.get_bus_position(route.route_id)

    # 某站点下一班车
    next_bus = client.get_next_bus_by_stop(stops.items[0].stops[0].stop_id)
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, Union

import httpx
from pydantic import TypeAdapter

from .config import DEFAULT_H5_PLATFORM, City, get_city
from .exceptions import IbusCloudError, IbusCloudHTTPError
from .models import (
    BusPositionResult,
    ListResult,
    NextBus,
    NearbyStopItem,
    RouteRealTime,
    RouteSearchItem,
    RouteStopNextBusResult,
    StopSearchItem,
)

_BASE_URL = "https://app.ibuscloud.com"

#: pydantic v2 类型适配器
_route_search_adapter: TypeAdapter[List[RouteSearchItem]] = TypeAdapter(
    List[RouteSearchItem]
)



class BusClient:
    """实时公交 API 客户端。

    :param city: 城市配置。可以是 ``type`` 参数值 (如 ``"weihai"``)、
        城市行政区划码 (如 ``"371000"``) 或 :class:`~weihai_bus.config.City`。
        默认 ``"371000"`` (威海)。
    :param h5_platform: 客户端平台码。默认 ``"2"`` —— 实测免授权可访问,
        无需微信 OAuth。若要模拟官网 (威海为 ``"12"``) 可显式传入。
    :param timeout: 请求超时秒数,默认 10。
    :param base_url: API 根地址,一般无需修改。
    :param http_client: 自定义 httpx 客户端 (如带代理/重试)。
    """

    def __init__(
        self,
        city: Union[str, City] = "371000",
        h5_platform: str = DEFAULT_H5_PLATFORM,
        timeout: float = 10.0,
        base_url: str = _BASE_URL,
        http_client: Optional[httpx.Client] = None,
    ):
        if isinstance(city, City):
            self._city = city
        else:
            found = get_city(city)
            if found is None:
                # 未识别的城市码也允许透传,由服务端决定
                self._city = City(
                    key=city,
                    name=city,
                    city_code=city,
                    h5_platform=h5_platform,
                    lat=0.0,
                    lng=0.0,
                )
            else:
                self._city = found

        self.h5_platform = h5_platform
        self.base_url = base_url.rstrip("/")
        self._client = http_client or httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"},
        )

    # ------------------------------------------------------------------ #
    # 基础设施
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """释放底层 httpx 客户端。"""
        self._client.close()

    def __enter__(self) -> "BusClient":
        return self

    def __exit__(self, *exc) -> None:  # type: ignore[no-untyped-def]
        self.close()

    def _request(
        self,
        path: str,
        *,
        params: Optional[dict] = None,
        method: str = "GET",
    ) -> dict:
        """发起一次请求,处理重定向 / 错误 / 业务响应包装。"""
        params = dict(params or {})
        params.setdefault("city", self._city.city_code)
        params.setdefault("h5Platform", self.h5_platform)

        url = f"{self.base_url}{path}"
        try:
            resp = self._client.request(method, url, params=params)
        except httpx.HTTPError as exc:
            raise IbusCloudHTTPError(f"网络请求失败: {exc}") from exc

        # 服务端在缺少合法会话时返回微信 OAuth 302 重定向而非 JSON
        if resp.is_redirect or resp.status_code >= 300:
            loc = resp.headers.get("location", "")
            raise IbusCloudHTTPError(
                f"服务端要求重定向 (缺少会话/token): {loc or resp.status_code}",
                status_code=resp.status_code,
            )

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise IbusCloudHTTPError("HTTP 状态异常", status_code=exc.response.status_code) from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise IbusCloudHTTPError("响应不是合法 JSON") from exc

        if not isinstance(data, dict):
            raise IbusCloudHTTPError(f"响应格式异常: {type(data)}")

        # 业务错误码
        result = data.get("result", 0)
        if result != 0:
            raise IbusCloudError(result, data.get("message", ""))
        return data

    # ------------------------------------------------------------------ #
    # 通用列表响应解析
    # ------------------------------------------------------------------ #
    @staticmethod
    def _as_item_list(data: dict, item_type: type) -> ListResult:
        """把 ``{items:[...]}`` 包装响应转成 :class:`~weihai_bus.models.ListResult`。

        仅转换 ``items`` 字段,返回 :class:`ListResult`,其 ``items`` 为已映射对象。
        """
        adapter = TypeAdapter(List[item_type])
        raw_items = data.get("items", [])
        mapped = adapter.validate_python(raw_items) if raw_items else []
        return ListResult(
            result=data.get("result", 0),
            message=data.get("message", ""),
            total=data.get("total", 0),
            page_count=data.get("pageCount", 0),
            items=mapped,
        )

    # ------------------------------------------------------------------ #
    # 查询接口
    # ------------------------------------------------------------------ #
    def find_route_by_name(self, route_name: str) -> ListResult:
        """按线路名搜索线路 (返回该线路名的所有方向/班次)。"""
        data = self._request(
            "/v1/bus/findRouteByName", params={"routeName": route_name}
        )
        return self._as_item_list(data, RouteSearchItem)

    def find_stop_by_name(self, stop_name: str) -> ListResult:
        """按站点名搜索站点。"""
        data = self._request(
            "/v1/bus/findStopByName", params={"stopName": stop_name}
        )
        return self._as_item_list(data, StopSearchItem)

    def find_nearby_stop(
        self,
        *,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius: int = 1000,
    ) -> ListResult:
        """搜索附近的站点。

        :param lat: 纬度,缺省用城市默认坐标。
        :param lng: 经度,缺省用城市默认坐标。
        :param radius: 搜索半径(米),必须提供,默认 1000。
        """
        if lat is None:
            lat = self._city.lat
        if lng is None:
            lng = self._city.lng
        data = self._request(
            "/v1/bus/findNearbyStop",
            params={"lat": lat, "lng": lng, "radius": radius},
        )
        return self._as_item_list(data, NearbyStopItem)

    # ------------------------------------------------------------------ #
    # 实时信息接口
    # ------------------------------------------------------------------ #
    def get_bus_position(self, route_id: int) -> Optional[RouteRealTime]:
        """查询一条线路的车辆实时位置。

        :param route_id: 线路 id (来自 :meth:`find_route_by_name`)。
        :return: 线路方向的实时信息,无数据返回 ``None``。
        """
        data = self._request(
            "/v1/bus/getBusPositionByRouteId", params={"routeId": route_id}
        )
        return BusPositionResult.model_validate(data).first

    def get_next_bus_by_stop(self, stop_id: int) -> List[NextBus]:
        """查询经过某站点的所有线路的下一班车。

        :param stop_id: 站点 id (来自 :meth:`find_stop_by_name`)。
        :return: 每个途经线路的下一班车预报列表。
        """
        data = self._request(
            "/v1/bus/getNextBusByStopId", params={"stopId": stop_id}
        )
        adapter = TypeAdapter(List[NextBus])
        raw = data.get("items", data.get("item", []))
        if isinstance(raw, dict):
            raw = [raw]
        return adapter.validate_python(raw) if raw else []

    def get_next_bus_by_route_stop(
        self, route_id: int, stop_id: int
    ) -> Optional[RouteStopNextBusResult]:
        """查询某条线路在某站点的下一班车。

        :return: 站序与下一班预报,无数据返回 ``None``。
        """
        data = self._request(
            "/v1/bus/getNextBusByRouteStopId",
            params={"routeId": route_id, "stopId": stop_id},
        )
        if "item" not in data:
            return None
        return RouteStopNextBusResult.model_validate(data["item"])

    # ------------------------------------------------------------------ #
    # 便捷组合
    # ------------------------------------------------------------------ #
    def route_real_time(self, route_key: str) -> Optional[RouteRealTime]:
        """按线路名直接查实时位置 (跳过自行拼 routeId)。

        :param route_key: 线路名关键字,如 ``"1路"``。
        :return: 取匹配的第一条线路实时位置,无则 ``None``。
        """
        found = self.find_route_by_name(route_key)
        if not found.items:
            return None
        first_route = found.items[0].routes[0]
        return self.get_bus_position(first_route.route_id)


__all__ = [
    "BusClient",
    "IbusCloudError",
    "IbusCloudHTTPError",
    "City",
    "CITIES",
]