"""实时公交 (timebus.ibuscloud.com) 非官方 Python SDK。

基本用法::

    from weihai_bus import BusClient

    client = BusClient()
    result = client.find_route_by_name("1路")
    print(result.items[0].name)
"""

from .client import BusClient
from .config import CITIES, City, get_city
from .exceptions import IbusCloudError, IbusCloudHTTPError
from . import models

__version__ = "0.1.0"

__all__ = [
    "BusClient",
    "City",
    "CITIES",
    "get_city",
    "IbusCloudError",
    "IbusCloudHTTPError",
    "models",
    "__version__",
]