# weihai-bus (实时公交 SDK)

非官方 [timebus.ibuscloud.com](https://timebus.ibuscloud.com/?type=weihai#/) 实时公交平台的 Python SDK。
提供线路/站点搜索、车辆实时位置、下一班车预报等只读接口的简洁封装。

> ⚠️ **免责声明**:本项目仅用于个人学习与研究,与官方无任何关联。接口与字段可能随平台变动,
> 请勿用于高频抓取或任何商业用途。

## 特性

- ✅ 多城市支持,默认威海(`city=371000`),内置城市映射表可扩展
- ✅ 默认**免授权模式**(`h5Platform=2`),实测无需微信 OAuth 即可访问
- ✅ 基于 `httpx` + `pydantic v2`,类型安全、可 `async` 扩展
- ✅ 全部 6 个只读接口 + 便捷组合方法,异常分类清晰
- ✅ 自带 `weihai` CLI 与 Claude Code skill,agent 可直接对话查询实时公交

## 安装

```bash
uv add weihai-bus   # 或
pip install .
```

需要 Python >= 3.9。

## 快速开始

```python
from weihai_bus import BusClient, get_city

client = BusClient()          # 默认威海

# 1. 按线路名搜索
r = client.find_route_by_name("1路")
print(r.items[0].name, [x.route_name for x in r.items[0].routes])
# '1路' ['1路', '1路']  # 两个方向

# 2. 取某方向的 routeId,查车辆实时位置
route = r.items[0].routes[0]
pos = client.get_bus_position(route.route_id)
print(pos.route.route_name, len(pos.stops), "个站点")

# 3. 按站点名搜索
stops = client.find_stop_by_name("威海九中")
stop = stops.items[0].stops[0]
print(stop.stop_name, stop.lat, stop.lng)

# 4. 站点下一班车
next_buses = client.get_next_bus_by_stop(stop.stop_id)

# 5. 附近站点
nearby = client.find_nearby_stop(radius=2000)

# 6. 线路在某站点的下一班
rt = client.get_next_bus_by_route_stop(route.route_id, stop.stop_id)
```

### 其他城市

```python
from weihai_bus import BusClient, get_city

c = get_city("wenzhou")       # 温州
client = BusClient(city=c.city_code, h5_platform=c.h5_platform)
```

## API 一览

| 方法 | 说明 |
|---|---|
| `find_route_by_name(route_name)` | 按线路名搜索 |
| `find_stop_by_name(stop_name)` | 按站点名搜索 |
| `find_nearby_stop(lat, lng, radius)` | 附近站点 (radius 必填) |
| `get_bus_position(route_id)` | 线路车辆实时位置 |
| `get_next_bus_by_stop(stop_id)` | 站点下一班车 |
| `get_next_bus_by_route_stop(route_id, stop_id)` | 线路某站点下一班车 |
| `route_real_time(route_key)` | 便捷:按线路名直达实时位置 |

## 异常

- `IbusCloudError`: 业务错误 (携带 `result` 错误码、`message`)
- `IbusCloudHTTPError`: HTTP / 网络 / 重定向 (如缺少会话被服务端要求 OAuth) 错误

## 命令行 (CLI)

安装后可直接在终端使用 `weihai` 命令:

```bash
# 按线路名搜索 (默认威海, h5Platform=2 免授权)
weihai routes 1路
weihai routes 1路 --verbose        # 显示站数/首末班

# 车辆实时位置: 按线路名 或 直接给 routeId
weihai vehicles --name 1路
weihai vehicles 3710000100128319

# 按站点名搜索 / 附近站点
weihai stops 威海九中
weihai stops 威海九中 --routes     # 同时列出途经线路
weihai nearby --radius 2000

# 下一班车
weihai next-at-stop 3710000100094159         # 站点全部线路
weihai next 3710000100564252 3710000100564252 # 指定线路+站点

# 所有命令支持 --json (机器可解析) 与其他城市
weihai routes 1路 --json
weihai routes 1路 --city 330300 --platform 5   # 温州
```

## Claude Code Skill

本仓库附带一份 **Vercel 风格** 的 Claude Code skill,让 AI agent 能直接通过 `weihai` 命令查询实时公交,
而不必从零读文档或手写调用。skill 采用每条命令一组 reference 文档的结构化描述
(`input` / `action` / `output` / `side_effect` / 失败处理),并声明了可执行依赖 `weihai`。

### 位置与安装

skill 已安装在**用户级全局**目录:

```
~/.claude/skills/weihai-bus/
├── SKILL.md                       # frontmatter(含 metadata.requires.bins) + 命令索引
└── references/
    ├── weihai-routes.md           # routes
    ├── weihai-vehicles.md         # vehicles
    ├── weihai-stops.md            # stops + nearby
    └── weihai-next.md             # next-at-stop + next
```

全局安装后,任何 Claude Code 会话(不限于本仓库目录)都能识别 `weihai-bus` 技能。
重开/新开会话后生效,可出现在 `/skills` 列表中。

**前提**:skill 需要 `weihai` 命令行可用。缺省时:

```bash
uv tool install weihai-bus          # 全局安装,提供 weihai 命令
# 或在本仓库内
uv sync && .venv\Scripts\weihai.exe
```

### skill 使用示例

在 Claude Code 中直接以自然语言触发即可,agent 会自动调用 `weihai` 子命令:

> 「威海 1 路公交现在在哪,经过哪些站?」
> → agent 运行 `weihai vehicles --name 1路`

> 「威海九中附近 2 公里有哪些公交站?」
> → agent 运行 `weihai nearby --radius 2000`

### 维护说明

- 若 `weihai` CLI 新增/改动了子命令,需同步更新 `references/*.md` 中对应的
  `input` 参数表、示例与 `output` 说明。
- skill 中的 `metadata.requires.bins: ["weihai"]` 是 Claude Code 判定技能可运行的关键声明,
  改动命令集时注意保持一致。
- 本项目源码不包含该 skill;如需随仓库分发,可加个 `docs/skill.md` 或后续迁移到 `skill/src/weihai-bus/`。

## 开发

```bash
uv sync
uv run python -m pytest
uv run weihai --help
```