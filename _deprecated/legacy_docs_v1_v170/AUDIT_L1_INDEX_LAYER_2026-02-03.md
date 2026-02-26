# L1 索引引擎审计简报
## [Genesis.L1Audit] Layer 1 Security Assessment

**日期**: 2026-02-03
**审计范围**: 索引层 (L1) - 负责扫描列表页和获取 Match ID 的组件
**审计目标**: 评估网络安全、反爬漏洞、与 BaseHarvestEngine 的兼容性

---

## 执行摘要

**审计状态**: ✅ SCAN COMPLETE

**发现的关键问题**:
- **5 个** L1 组件需要 NetworkShield 集成
- **3 个**高危反爬漏洞
- **0 个**组件具备随机脉冲伪装能力
- **22 节点** NetworkShield 代理池可用（平均健康分数 92.7）

**建议**: 立即创建 DiscoveryEngine 继承 BaseHarvestEngine，统一 L1 代理管理。

---

## 1. 资产清点：L1 组件地图

### 1.1 核心组件清单

| 组件名称 | 文件路径 | 版本 | 功能描述 | 当前代理系统 |
|---------|---------|------|----------|-------------|
| **Discovery Queue Engine** | `scripts/run_discovery.py` | V120.0 | 队列式 URL 发现引擎 | ❌ ProxyManager (旧) |
| **Harvester Service** | `src/api/services/harvester_service.py` | V142.0 | stage1_fixtures_scan 列表扫描 | ❌ ProxyPool V142.6 (旧) |
| **FotMob Historical ID Scanner** | `src/collectors/fotmob_historical_id_scanner.py` | V36.0 | 球队路径策略历史 ID 发现 | ⚠️ 部分 ProxyManager |
| **Discovery Cluster** | `scripts/run_discovery_cluster.py` | - | 集群并发发现 | ❌ ProxyManager |
| **League Sweep** | `scripts/run_league_sweep.py` | - | 联赛扫描 | ⚠️ 无明确代理 |
| **Season Discoverer** | `src/collectors/season_discoverer.py` | - | 赛季清单生成 | ❌ 裸连 (requests.get) |

### 1.2 调用关系图

```
┌─────────────────────────────────────────────────────────────────┐
│  L1 入口点                                                      │
│  main.py --mode cruise / scripts/run_discovery.py             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  发现引擎 (run_discovery.py)                                    │
│  • 使用 Queue: match_search_queue                              │
│  • Checkpoint/Resume 支持                                      │
│  • 调用 ProxyManager (旧)                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ID 采集层                                                      │
│  fotmob_historical_id_scanner.py  (Team Path Strategy)        │
│  harvest_league_urls.py            (URL Parsing)              │
│  season_discoverer.py              (Season Manifest)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  数据写入层                                                      │
│  • match_search_queue 表 (队列)                                 │
│  • matches 表 (去重)                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 网络安全审计：3 大高危反爬漏洞

### 漏洞 #1：裸连请求 (Critical)

**风险等级**: 🔴 **CRITICAL**

**位置**: `src/collectors/season_discoverer.py:36`

```python
# ❌ 当前代码 (裸连，暴露真实 IP)
response = requests.get(url, headers=headers, timeout=10)
```

**问题**:
- 完全不使用代理
- 直接暴露服务器真实 IP
- 容易被反爬系统标记

**影响**:
- 真实 IP 被封后，整个 L1 层瘫痪
- 无法获取新比赛 ID，L2/L3 无数据可处理

**修复方案**:
```python
# ✅ 修复后代码 (NetworkShield 集成)
from src.infrastructure.engines.match_engine.shared import NetworkGuardian

guardian = NetworkGuardian()
await guardian.initialize()
proxy = await guardian.get_next_healthy_proxy(session_id="season-discovery")

response = requests.get(
    url,
    headers=headers,
    proxies={'http': proxy.url, 'https': proxy.url},
    timeout=10
)

await guardian.mark_proxy_success(proxy.port)
```

---

### 漏洞 #2：硬编码延迟模式 (High)

**风险等级**: 🟠 **HIGH**

**位置**: 多处

| 文件 | 行号 | 当前代码 | 问题 |
|------|------|----------|------|
| `scripts/run_discovery.py` | 344, 373 | `await asyncio.sleep(2/3)` | 固定 2-3 秒延迟 |
| `src/collectors/season_discoverer.py` | 104 | `time.sleep(0.1)` | 固定 100ms |
| `src/api/services/harvester_service.py` | AGGRESSIVE_DELAY_CONFIG | `"pagination_min": 120` | 固定 2-4 分钟 |

**问题**:
- **机器人特征**: 真实用户不会每次请求都间隔完全相同的时间
- **可被机器学习检测**: 反爬系统可轻松识别这种规律性模式
- **无脉冲伪装**: 没有随机性模拟人类行为

**影响**:
- 被识别为自动化脚本
- IP 被标记后，后续请求全部 403

**修复方案**:
```python
# ✅ 使用 Ghost Protocol 的随机脉冲延迟
import random

# 替代固定 2 秒延迟
await asyncio.sleep(random.uniform(1.5, 3.5))

# 替代固定 100ms 延迟
await asyncio.sleep(random.uniform(0.05, 0.3))

# 更高级的脉冲模拟 (从 BaseExtractor V141.0)
from src.api.collectors.base_extractor import BaseExtractor

human_pulse = BaseExtractor.generate_human_pulse()
await asyncio.sleep(human_pulse)
```

---

### 漏洞 #3：旧代理系统孤岛 (High)

**风险等级**: 🟠 **HIGH**

**位置**: `scripts/run_discovery.py:442-449`

```python
# ❌ 当前代码 (旧 ProxyManager)
from src.bridge.adapters.proxy_manager import ProxyManager

pm = ProxyManager()
proxy = pm.get_random_proxy()
```

**问题**:
- **状态隔离**: ProxyManager 无法与 active_registry.json 同步
- **资源冲突**: L1 使用旧系统，L2/L3 使用 NetworkShield，可能导致 IP 重复使用
- **无跨语言同步**: Node.js QuantHarvester 无法感知 L1 的代理状态

**影响**:
- 同一 IP 被 L1 和 L2/L3 同时使用 → 触发反爬
- L1 失败 IP 无法被 L2/L3 感知 → 级联失败
- Node.js 端无法看到 L1 的代理健康状态

**修复方案**:
```python
# ✅ 迁移到 NetworkGuardian
from src.infrastructure.engines.match_engine.shared import NetworkGuardian

guardian = NetworkGuardian()
await guardian.initialize()

# Session 绑定 (一个发现会话 = 一个 IP)
session_id = f"discovery-{int(time.time())}"
proxy = await guardian.get_next_healthy_proxy(session_id)

# 失败上报
try:
    data = await fetch_with_proxy(proxy.url)
    await guardian.mark_proxy_success(proxy.port)
except Exception as e:
    await guardian.mark_proxy_failed(proxy.port, str(e))
```

---

## 3. 逻辑链路审计

### 3.1 去重逻辑分析

| 组件 | 去重策略 | 位置 | 问题 |
|------|---------|------|------|
| **run_discovery.py** | 数据库 ON CONFLICT DO UPDATE | matches 表 | ✅ 正确 |
| **fotmob_historical_id_scanner.py** | in-memory set | `self.discovered_ids` | ⚠️ 重启丢失 |
| **harvest_league_urls.py** | 数据库约束 | matches 表 | ✅ 正确 |

**评估**: 大部分组件使用数据库去重，但 `fotmob_historical_id_scanner.py` 使用内存去重，进程重启后会丢失已发现 ID。

### 3.2 容错能力分析

| 场景 | run_discovery.py | fotmob_historical_id_scanner.py | season_discoverer.py |
|------|------------------|--------------------------------|---------------------|
| **403 Forbidden** | ⚠️ 无明确处理 | ⚠️ 无明确处理 | ❌ 裸连直接失败 |
| **HTML 结构变化** | ⚠️ 无明确处理 | ⚠️ 无明确处理 | ❌ 直接解析崩溃 |
| **网络超时** | ✅ 有重试 | ✅ 有重试 | ❌ 单次请求 |

**评估**: L1 层整体容错能力较弱，缺少统一的 CircuitBreaker 保护。

---

## 4. BaseHarvestEngine 兼容性评估

### 4.1 接口适配性分析

**BaseHarvestEngine 抽象方法要求**:
```python
@abstractmethod
async def initialize(self) -> None: ...

@abstractmethod
async def harvest_match(self, match_id: int | str) -> HarvestResult: ...

@abstractmethod
async def harvest_batch(self, match_ids: list[int]) -> list[HarvestResult]: ...

@abstractmethod
async def shutdown(self) -> None: ...
```

**L1 组件适配性**:

| 组件 | 初始化 | 单个处理 | 批量处理 | 关闭 | 评分 |
|------|--------|---------|---------|------|------|
| **run_discovery.py** | ✅ | ✅ | ✅ | ✅ | 🟢 90% |
| **fotmob_historical_id_scanner.py** | ✅ | ✅ | ✅ | ⚠️ | 🟡 75% |
| **season_discoverer.py** | ⚠️ | ✅ | ❌ | ❌ | 🔴 50% |

**结论**: L1 组件可以**平滑继承** BaseHarvestEngine，但需要进行适配改造。

### 4.2 建议的 DiscoveryEngine 接口

```python
from src.infrastructure.engines.match_engine.base.base_harvest_engine import BaseHarvestEngine

class DiscoveryEngine(BaseHarvestEngine):
    """
    L1 索引引擎 - 负责扫描列表页获取 Match ID

    核心功能:
    1. 扫描联赛列表页
    2. 提取比赛 ID
    3. 去重后写入队列
    4. 使用 NetworkShield 管理代理
    """

    async def discover_league(
        self,
        league_id: str,
        season: str
    ) -> HarvestResult[list[int]]:
        """
        发现指定联赛的比赛 ID

        Returns:
            HarvestResult: 包含发现的比赛 ID 列表
        """
        # 1. 获取代理 (NetworkShield)
        session_id = f"league-{league_id}-{season}"
        proxy = await self._get_proxy_for_session(session_id)

        # 2. 使用 CircuitBreaker 保护请求
        match_ids = await self._circuit_breaker.call(
            self._fetch_league_matches,
            league_id,
            season,
            proxy_port=proxy.port,
            proxy_url=proxy.url
        )

        # 3. 上报成功/失败
        if match_ids:
            await self._report_success(proxy.port)
        else:
            await self._report_failure(proxy.port, "No matches found")

        return HarvestResult(
            source="fotmob_discovery",
            match_id=f"{league_id}-{season}",
            status=HarvestStatus.SUCCESS,
            success=True,
            data={"match_ids": match_ids},
            proxy_port=proxy.port
        )
```

---

## 5. L1+L2+L3 全链路隐身方案

### 5.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│  统一代理层: NetworkShield (active_registry.json)               │
│  • 22 节点代理池 (7891-7912)                                     │
│  • Session 绑定 (一个会话 = 一个 IP)                            │
│  • 健康分数管理 (Python/Node.js 跨语言同步)                      │
└─────────────────────────────────────────────────────────────────┘
          ↓                    ↓                    ↓
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│  L1: DiscoveryEngine│ │  L2: FotMobEngine    │ │  L3: QuantHarvester │
│  • 列表页扫描       │ │  • 比赛详情采集      │ │  • 赔率数据提取     │
│  • ID 发现          │ │  • L2 数据提取       │ │  • OddsPortal RPA   │
│  • 随机脉冲延迟     │ │  • Ghost Protocol    │ │  • 双模提取         │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
          ↓                    ↓                    ↓
┌─────────────────────────────────────────────────────────────────┐
│  统一熔断保护: UnifiedCircuitBreaker                             │
│  • 自动故障上报                                                 │
│  • 冷却期管理                                                   │
│  • 跨层健康感知                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  数据持久层                                                      │
│  • match_search_queue (L1 输出)                                 │
│  • matches (主表)                                               │
│  • metrics_multi_source_data (L2/L3 输出)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 延迟策略分层

| 层级 | 延迟范围 | 策略 | 目的 |
|------|---------|------|------|
| **L1 列表扫描** | 2000-5000ms | 随机脉冲 | 模拟浏览多个联赛 |
| **L1 分页** | 120-240s | AGGRESSIVE_DELAY | 避免大规模扫描 |
| **L2 详情采集** | 1500-3000ms | 随机脉冲 | 模拟查看比赛详情 |
| **L3 赔率提取** | 3000-6000ms | 人类脉冲 | 模拟分析赔率 |

### 5.3 Session 管理策略

```
L1 Discovery Session:
  • 生命周期: 整个联赛扫描期间
  • 绑定粒度: 一个联赛 = 一个 IP
  • 释放时机: 联赛扫描完成

L2 Harvest Session:
  • 生命周期: 单场比赛采集期间
  • 绑定粒度: 一个比赛 = 一个 IP
  • 释放时机: 比赛数据写入完成

L3 Odds Session:
  • 生命周期: OddsPortal 页面加载期间
  • 绑定粒度: 一个浏览器 = 一个 IP
  • 释放时机: 赔率数据提取完成
```

---

## 6. 迁移路线图

### Phase 1: NetworkShield 集成 (Week 1)

**目标**: 所有 L1 组件迁移到 NetworkGuardian

**任务**:
1. ✅ 创建 `src/infrastructure/engines/match_engine/discovery/`
2. ⬜ 实现 `DiscoveryEngine` 继承 `BaseHarvestEngine`
3. ⬜ 迁移 `run_discovery.py` 到新架构
4. ⬜ 修复 `season_discoverer.py` 裸连问题

**验收标准**:
- [ ] 所有 L1 请求通过 active_registry.json 获取代理
- [ ] 代理失败状态能被 Node.js 端感知
- [ ] hot_swap_validation.py 测试通过

### Phase 2: 反爬增强 (Week 2)

**目标**: 添加随机脉冲伪装能力

**任务**:
1. ⬜ 替换所有硬编码 `time.sleep()` 为随机延迟
2. ⬜ 集成 Ghost Protocol (30+ 浏览器指纹池)
3. ⬜ 添加请求头随机化

**验收标准**:
- [ ] 90%+ 延迟使用随机脉冲
- [ ] User-Agent 池化
- [ ] 指纹随机化

### Phase 3: 熔断保护 (Week 3)

**目标**: 统一 CircuitBreaker 保护

**任务**:
1. ⬜ 集成 UnifiedCircuitBreaker 到所有 L1 组件
2. ⬜ 实现故障自动上报
3. ⬜ 添加冷却期管理

**验收标准**:
- [ ] 连续 2 次失败自动进入冷却期
- [ ] 冷却期间 L1 自动跳过该 IP
- [ ] 冷却结束自动恢复

---

## 7. 总结

### 关键发现

1. **高危漏洞**: 3 个 (裸连、硬编码延迟、代理系统孤岛)
2. **兼容性**: L1 可以平滑继承 BaseHarvestEngine (需要适配)
3. **代理池状态**: 22 节点可用，平均健康分数 92.7

### 优先级建议

| 优先级 | 任务 | 预计工作量 | 风险 |
|--------|------|-----------|------|
| **P0** | 修复 season_discoverer.py 裸连 | 2 小时 | 高 |
| **P0** | 创建 DiscoveryEngine 集成 NetworkShield | 1 天 | 中 |
| **P1** | 替换硬编码延迟为随机脉冲 | 4 小时 | 低 |
| **P1** | 迁移 run_discovery.py 到新架构 | 2 天 | 中 |
| **P2** | 集成 UnifiedCircuitBreaker | 1 天 | 低 |

### 下一步行动

1. **立即执行**: 修复 `season_discoverer.py:36` 裸连漏洞
2. **本周完成**: 创建 DiscoveryEngine 并集成 NetworkShield
3. **下周目标**: 完成 Phase 2 反爬增强

---

**审计人员**: [Genesis.L1Audit]
**审计日期**: 2026-02-03
**下次审计**: Phase 1 完成后
