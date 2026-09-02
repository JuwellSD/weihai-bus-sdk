"""实时公交 (timebus.ibuscloud.com) 平台配置。

该平台实际服务多个城市,通过 ``city`` (行政区划码) 与 ``h5Platform``
(客户端平台码) 两个参数在请求中区分。

已确认的平台取值 (type 参数对应如下):
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class City:
    """一个城市的访问配置。"""

    key: str
    """URL 里的 type 参数值 (如 ``weihai``)。"""
    name: str
    """中文城市名。"""
    city_code: str
    """请求参数 ``city`` 使用的行政区划码。"""
    h5_platform: str
    """官网 URL 使用的 ``h5Platform`` 取值。"""
    lat: float
    lng: float
    """默认中心坐标 (用于附近站点搜索兜底)。"""


#: 官网 URL 中识别出的城市映射。
CITIES: dict[str, City] = {
    "weihai": City(
        key="weihai",
        name="威海",
        city_code="371000",
        h5_platform="12",
        lat=37.509691,
        lng=122.116394,
    ),
    "wenzhou": City(
        key="wenzhou",
        name="温州",
        city_code="330300",
        h5_platform="5",
        lat=28.0,
        lng=120.67,
    ),
    "hangzhou": City(
        key="hangzhou",
        name="杭州",
        city_code="330100",
        h5_platform="6",
        lat=30.26,
        lng=120.19,
    ),
    "hangzhoubus": City(
        key="hangzhoubus",
        name="杭州公交",
        city_code="330100",
        h5_platform="5",
        lat=30.26,
        lng=120.19,
    ),
    "pingdu": City(
        key="pingdu",
        name="平度",
        city_code="370283",
        h5_platform="11",
        lat=36.787,
        lng=119.955,
    ),
    "pujiang": City(
        key="pujiang",
        name="浦江",
        city_code="330726",
        h5_platform="2",
        lat=29.452476,
        lng=119.892222,
    ),
    "wuyi": City(
        key="wuyi",
        name="武义",
        city_code="330723",
        h5_platform="3",
        lat=28.892683,
        lng=119.816575,
    ),
}

#: 默认免授权平台值，无需微信 OAuth 即可访问。
DEFAULT_H5_PLATFORM = "2"


def get_city(key_or_code: str) -> Optional[City]:
    """按 type 参数或城市码查找 :class:`City`。

    :param key_or_code: ``type`` 参数值 (如 ``"weihai"``) 或城市行政区划码
        (如 ``"371000"``)。后者会与所有城市双向匹配。
    :return: 命中的城市配置，未找到返回 ``None``。
    """
    c = CITIES.get(key_or_code)
    if c is not None:
        return c
    for city in CITIES.values():
        if city.city_code == key_or_code or city.name == key_or_code:
            return city
    return None