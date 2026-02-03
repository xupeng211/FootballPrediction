# [Genesis.Audit] ENGINE SYNC AUDIT REPORT

**审计日期**: 2026-02-03
**审计范围**: 双源收割引擎架构一致性与归口审计
**审计对象**: FotMob (Python L2) + OddsPortal (Node.js L3)

---

## 执行摘要

[Genesis.Audit] ENGINE SYNC AUDIT COMPLETE. Found **7 critical alignment issues**. Optimization plan ready for review.

### 关键发现

| 严重级别 | 问题 | 影响 |
|----------|------|------|
| 🔴 CRITICAL | 双代理系统并行运行 | 资源浪费 + 状态不一致 |
| 🔴 CRITICAL | Python 采集器未接入 NetworkShield | 无法跨语言故障同步 |
| 🟠 HIGH | 7 个不同的 CircuitBreaker 实现 | 维护成本高 + 行为不一致 |
| 🟡 MEDIUM | FotMob 采集器分散在多个目录 | 难以统一管理 |
| 🟡 MEDIUM | 无统一的引擎入口协议 | 启动方式不统一 |
| 🟢 LOW | 缺少统一的监控仪表板 | 可观测性不足 |

---

## 1. 现状穿透 (Current Mapping)

### 1.1 FotMob 数据采集核心脚本

| 文件路径 | 版本 | 功能 | 代理系统 |
|----------|------|------|----------|
| `src/collectors/fotmob_core.py` | V144.5 | 核心数据采集器 | **ProxyManager (V41.590)** |
| `src/collectors/base_extractor.py` | V150.0 | 反检测基础层 | **ProxyManager (V41.590)** |
| `src/api/fotmob_client.py` | V3.3 | API 客户端 | **独立 CircuitBreaker** |
| `src/api/services/harvester_service.py` | V144.2 | 统一收割服务 | **ProxyManager (V41.590)** |

### 1.2 代理系统使用情况

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    当前代理系统架构                                         │
│                                                                             │
│  Python 路径 (FotMob L2)              Node.js 路径 (OddsPortal L3)          │
│  ┌─────────────────────────────┐      ┌──────────────────────────────────┐  │
│  │ ProxyManager V41.590        │      │ NetworkShield V1.1.0             │  │
│  │ (src/core/proxy/)           │      │ (infrastructure/network/)       │  │
│  ├─────────────────────────────┤      ├──────────────────────────────────┤  │
│  │ • 失败计数器                │      │ • 22节点管理                    │  │
│  │ • 黑名单机制                │      │ • LRU 会话绑定                  │  │
│  │ • 冷却期 (300秒)            │      │ • 自愈熔断 (2次=15分钟)         │  │
│  │ • WSL2 自动探测             │      │ • 文件锁原子更新                │  │
│  └─────────────────────────────┘      │ • 健康分数排序                  │  │
│           ↓                          └──────────────────────────────────┘  │
│  [独立状态文件?]                                                              │
│           ↓                                                                      ↓
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ❌ 状态隔离 - 两系统完全独立，无法共享故障信息                             │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  共享文件 (仅 NetworkShield 使用):                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  config/active_registry.json                                             │  │
│  │  - 22 个节点状态                                                         │  │
│  │  - 健康分数 (0-100)                                                      │  │
│  │  - 冷却期时间戳                                                          │  │
│  │  - 会话绑定信息                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 NetworkShield Python 适配器状态

| 项目 | 状态 |
|------|------|
| **文件位置** | `src/infrastructure/network/python/network_shield.py` ✅ |
| **实现完整性** | 100% (包含所有核心接口) ✅ |
| **实际使用** | ❌ **未被任何 Python 代码导入或使用** |
| **原因分析** | 历史遗留 - Python 采集器先于 NetworkShield 开发 |

---

## 2. 架构债务评估 (Debt Assessment)

### 2.1 归口管理可行性分析

#### 当前 FotMob 采集器分布

```
src/
├── collectors/              # ⚠️ 分散的核心采集逻辑
│   ├── fotmob_core.py      # V144.5 主采集器
│   ├── base_extractor.py   # V150.0 反检测层
│   └── circuit_breaker.py  # V41.590 熔断器
├── api/
│   ├── fotmob_client.py    # V3.3 API 客户端
│   └── services/
│       └── harvester_service.py  # V144.2 统一服务
└── core/
    └── proxy/              # ⚠️ 旧的代理管理系统
        ├── proxy_manager.py      # V41.590
        ├── proxy_guardian.py     # V41.590
        └── proxy_health_checker.py

infrastructure/
└── engines/                # ✅ Node.js 引擎专用目录
    └── QuantHarvester.js  # V170.000 已集成 NetworkShield
```

#### 建议的归口结构

```
src/infrastructure/engines/
├── match_engine/          # 🆕 统一收割机入口 (Python)
│   ├── __init__.py
│   ├── fotmob_engine.py          # FotMob L2 数据引擎
│   ├── oddsportal_engine.py      # OddsPortal L3 数据引擎 (Python 版本)
│   └── base_engine.py            # 基础引擎类
│
├── services/              # 共享服务层
│   ├── NetworkShield.js          # V1.1.0 代理管理
│   └── network_shield.py         # V1.0.0 Python 适配器
│
└── config/               # 引擎配置
    └── engine_config.yaml        # 统一配置文件
```

### 2.2 协议一致性审计

#### NetworkShield vs ProxyManager 对比

| 功能 | NetworkShield (Node.js) | ProxyManager (Python) | 一致性 |
|------|-------------------------|----------------------|--------|
| **节点数量** | 22 (固定) | 动态配置 | ❌ |
| **失败阈值** | 2 次 | 3 次 | ❌ |
| **冷却时间** | 15 分钟 | 5 分钟 | ❌ |
| **健康分数** | 0-100 动态 | 计数器 | ❌ |
| **Session 绑定** | ✅ 支持 | ❌ 不支持 | ❌ |
| **LRU 淘汰** | ✅ 支持 (500) | ❌ 不支持 | ❌ |
| **文件锁** | ✅ 原子锁 | ❌ threading.Lock | ❌ |
| **跨语言同步** | ✅ active_registry.json | ❌ 独立状态 | ❌ |

#### 自愈熔断能力对比

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NetworkShield (QuantHarvester V170.000)                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  状态机: CLOSED → OPEN → HALF_OPEN → CLOSED                          │  │
│  │  触发条件: 2 次连续失败                                               │  │
│  │  冷却时间: 15 分钟                                                    │  │
│  │  恢复机制: 测试请求成功后自动恢复                                      │  │
│  │  Session 绑定: ✅ 确保一个会话始终使用同一 IP                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  vs.                                                                          │
│                                                                             │
│  ProxyManager (FotMob V144.5)                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  失败处理: 计数器 + 黑名单                                              │  │
│  │  触发条件: 3 次连续失败                                                │  │
│  │  冷却时间: 5 分钟 (300 秒)                                             │  │
│  │  恢复机制: 时间到期后自动恢复                                          │  │
│  │  Session 绑定: ❌ 不支持                                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 网络层冲突分析

#### 潜在锁冲突场景

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  并发访问 active_registry.json 场景分析                                    │
│                                                                             │
│  场景 1: Node.js QuantHarvester 运行中                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  1. 获取文件锁 (.registry.lock)                                      │  │
│  │  2. 读取 active_registry.json                                        │  │
│  │  3. 更新节点状态                                                      │  │
│  │  4. 原子写入 registry                                                 │  │
│  │  5. 释放锁                                                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    │ 并发                                   │
│                                    ↓                                       │
│  场景 2: Python FotMob 启动 (未接入 NetworkShield)                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ❌ 不访问 active_registry.json                                      │  │
│  │  ✅ 使用 ProxyManager 独立状态                                       │  │
│  │  ✅ 无锁冲突                                                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  结论: 当前无冲突，但状态隔离导致无法共享故障信息                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 最严重的 3 个"逻辑脱节"点

### 🔴 脱节点 #1: 双代理系统并行运行 (DEBT-001)

**问题描述**:
- Python 使用 ProxyManager V41.590 (src/core/proxy/)
- Node.js 使用 NetworkShield V1.1.0 (infrastructure/network/)
- 两套系统完全独立，无法共享故障信息

**影响**:
- Node.js 检测到的 IP 失效，Python 端不知情，继续使用失效 IP
- Python 端的失败计数无法影响 Node.js 的节点选择
- 资源浪费：维护两套健康检查、轮换、冷却逻辑

**严重程度**: 🔴 CRITICAL - 数据采集质量风险

---

### 🔴 脱节点 #2: FotMob 采集失败不计入 NetworkShield (DEBT-002)

**问题描述**:
- FotMob 采集器使用 ProxyManager.mark_failure()
- NetworkShield.shield.markProxyFailed() 未被调用
- active_registry.json 中节点状态不反映 FotMob 采集失败

**影响**:
- OddsPortal 采集可能选择已被 FotMob 判定为失效的 IP
- 跨引擎的 IP 劣化无法被及时发现

**严重程度**: 🔴 CRITICAL - IP 资源利用率低下

---

### 🟠 脱节点 #3: CircuitBreaker 实现碎片化 (DEBT-003)

**问题描述**:
- 项目中存在 **7 个不同的 CircuitBreaker 实现**:
  1. `src/core/circuit_breaker.py` - 核心熔断器
  2. `src/collectors/circuit_breaker.py` - 采集器熔断器
  3. `src/api/services/circuit_breaker.py` - API 熔断器
  4. `src/api/fotmob_client.py` - FotMob 客户端熔断器
  5. `src/ml/fault_tolerance.py` - ML 容错熔断器
  6. `src/services/collection_service.py` - 收集服务熔断器
  7. `src/infrastructure/network/core/CircuitBreaker.js` - NetworkShield 熔断器

**影响**:
- 行为不一致（失败阈值、恢复时间各异）
- 维护成本高（7 处修改）
- 测试复杂度增加

**严重程度**: 🟠 HIGH - 技术债务累积

---

## 4. 优化方案 (Optimization Plan)

### 4.1 建议的目录结构

```
src/infrastructure/engines/
│
├── match_engine/                    # 🆕 统一收割机目录
│   ├── __init__.py
│   │
│   ├── base/                        # 基础引擎抽象
│   │   ├── __init__.py
│   │   └── base_harvest_engine.py   # V1.0.0 基础引擎类
│   │
│   ├── fotmob/                      # FotMob L2 引擎
│   │   ├── __init__.py
│   │   ├── fotmob_engine.py         # V145.0 主引擎
│   │   ├── fotmob_collector.py      # V144.6 采集器
│   │   └── fotmob_config.py         # 配置
│   │
│   ├── oddsportal/                  # OddsPortal L3 引擎
│   │   ├── __init__.py
│   │   ├── oddsportal_engine.py     # V171.0 Python 版本
│   │   └── oddsportal_config.py     # 配置
│   │
│   └── shared/                      # 共享组件
│       ├── __init__.py
│       ├── network_guardian.py      # NetworkShield 统一接口
│       └── circuit_breaker.py      # 统一熔断器实现
│
├── services/                        # Node.js 服务
│   ├── NetworkShield.js             # V1.2.0 增强版
│   ├── SignalRadar.js               # V168.002 网络雷达
│   └── SurgicalInteraction.js       # V165.000 精确交互
│
└── config/                          # 统一配置
    ├── engine_config.yaml           # 引擎配置
    └── proxy_map.yaml               # 代理映射
```

### 4.2 统一引擎入口协议

```python
# src/infrastructure/engines/match_engine/base/base_harvest_engine.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

@dataclass
class HarvestResult:
    """统一的收割结果"""
    source: str              # "fotmob" or "oddsportal"
    match_id: str
    success: bool
    data: Dict[str, Any]
    errors: List[str]
    latency_ms: int
    proxy_port: int          # 使用的代理端口

class BaseHarvestEngine(ABC):
    """基础收割机抽象类 - 所有引擎必须实现此接口"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.network_shield = None  # NetworkShield 实例

    @abstractmethod
    async def initialize(self) -> None:
        """初始化引擎 - 必须通过 NetworkShield 认证"""
        pass

    @abstractmethod
    async def harvest_match(self, match_id: str) -> HarvestResult:
        """收割单场比赛数据"""
        pass

    @abstractmethod
    async def harvest_batch(self, match_ids: List[str]) -> List[HarvestResult]:
        """批量收割"""
        pass

    async def _get_proxy_for_session(self, session_id: str) -> Dict[str, Any]:
        """通过 NetworkShield 获取代理"""
        if not self.network_shield:
            raise RuntimeError("NetworkShield not initialized")

        proxy = await self.network_shield.get_next_healthy_proxy(session_id)

        if not proxy:
            raise RuntimeError("No available proxies")

        return {
            'host': '172.25.16.1',
            'port': proxy.port,
            'url': proxy.url
        }

    async def _report_success(self, port: int, latency_ms: int) -> None:
        """上报成功到 NetworkShield"""
        await self.network_shield.mark_proxy_success(port, latency_ms)

    async def _report_failure(self, port: int, reason: str) -> None:
        """上报失败到 NetworkShield"""
        await self.network_shield.mark_proxy_failed(port, reason)
```

### 4.3 "黄金数据"拼接协作伪代码

```python
# src/infrastructure/engines/match_engine/orchestration/golden_merger.py

"""
黄金数据拼接器 - 融合 L2 (FotMob) 和 L3 (OddsPortal) 数据
"""

from typing import Dict, Any, Optional
from datetime import datetime

class GoldenDataMerger:
    """黄金数据拼接器"""

    def __init__(self, fotmob_engine, oddsportal_engine):
        self.fotmob = fotmob_engine      # L2: 赛况/高阶数据
        self.oddsportal = oddsportal_engine  # L3: 赔率轨迹
        self.network_shield = fotmob_engine.network_shield  # 共享 NetworkShield

    async def harvest_golden_match(self, match_id: str) -> Dict[str, Any]:
        """
        收割黄金数据 (L2 + L3 融合)

        工作流:
        1. 通过 NetworkShield 获取会话绑定代理
        2. 并发收割 L2 和 L3 数据
        3. 拼接为黄金数据
        4. 统一上报代理状态
        """

        # 创建联合会话
        session_id = f"GOLDEN-{match_id}-{datetime.now().timestamp()}"

        # 获取代理 (Session 绑定)
        proxy = await self.network_shield.get_next_healthy_proxy(session_id)

        if not proxy:
            return {
                'match_id': match_id,
                'success': False,
                'error': 'NS_NO_PROXY_AVAILABLE',
                'data': None
            }

        try:
            # 并发收割 L2 和 L3
            import asyncio

            l2_task = self.fotmob.harvest_match(match_id, proxy)
            l3_task = self.oddsportal.harvest_match(match_id, proxy)

            l2_result, l3_result = await asyncio.gather(
                l2_task, l3_task, return_exceptions=True
            )

            # 评估结果
            l2_success = not isinstance(l2_result, Exception) and l2_result.get('success')
            l3_success = not isinstance(l3_result, Exception) and l3_result.get('success')

            # 拼接黄金数据
            golden_data = {
                'match_id': match_id,
                'fetched_at': datetime.now().isoformat(),
                'proxy_port': proxy.port,

                # L2: FotMob 数据
                'l2_fotmob': l2_result.get('data') if l2_success else None,
                'fotmob_status': 'success' if l2_success else 'failed',
                'fotmob_latency': l2_result.get('latency_ms') if l2_success else None,

                # L3: OddsPortal 数据
                'l3_oddsportal': l3_result.get('data') if l3_success else None,
                'oddsportal_status': 'success' if l3_success else 'failed',
                'oddsportal_latency': l3_result.get('latency_ms') if l3_success else None,

                # 融合质量评分
                'integrity_score': self._calculate_integrity(l2_success, l3_success),
                'data_quality': self._assess_quality(l2_result, l3_result)
            }

            # 上报代理状态
            if l2_success and l3_success:
                await self.network_shield.mark_proxy_success(
                    proxy.port,
                    max(l2_result.get('latency_ms', 0), l3_result.get('latency_ms', 0))
                )
            else:
                failure_reasons = []
                if not l2_success:
                    failure_reasons.append(f"FotMob: {l2_result if isinstance(l2_result, str) else 'Unknown'}")
                if not l3_success:
                    failure_reasons.append(f"OddsPortal: {l3_result if isinstance(l3_result, str) else 'Unknown'}")

                await self.network_shield.mark_proxy_failed(
                    proxy.port,
                    '; '.join(failure_reasons)
                )

            return {
                'success': l2_success or l3_success,  # 部分成功也算成功
                'data': golden_data
            }

        finally:
            # 释放会话
            self.network_shield.release_session(session_id)

    def _calculate_integrity(self, l2_success: bool, l3_success: bool) -> float:
        """计算数据完整性分数"""
        if l2_success and l3_success:
            return 1.0  # 完美
        elif l2_success or l3_success:
            return 0.5  # 部分
        else:
            return 0.0  # 失败

    def _assess_quality(self, l2_result, l3_result) -> str:
        """评估数据质量"""
        # 实现质量评估逻辑
        return "unknown"
```

---

## 5. 实施路线图 (Implementation Roadmap)

### Phase 1: 基础设施统一 (1-2 周)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| 1.1 创建 `src/infrastructure/engines/match_engine/` 目录 | P0 | 1 天 |
| 1.2 实现 `BaseHarvestEngine` 抽象类 | P0 | 2 天 |
| 1.3 实现 `NetworkGuardian` 统一接口 | P0 | 2 天 |
| 1.4 更新 NetworkShield Python 适配器 | P1 | 1 天 |

### Phase 2: FotMob 引擎迁移 (1 周)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| 2.1 创建 `FotMobEngine` 类 (继承 BaseHarvestEngine) | P0 | 2 天 |
| 2.2 迁移 `fotmob_core.py` 到新架构 | P0 | 2 天 |
| 2.3 接入 NetworkShield 替换 ProxyManager | P0 | 2 天 |
| 2.4 单元测试和集成测试 | P0 | 1 天 |

### Phase 3: 黄金数据拼接 (1 周)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| 3.1 实现 `GoldenDataMerger` | P0 | 3 天 |
| 3.2 L2 + L3 数据融合逻辑 | P0 | 2 天 |
| 3.3 质量评估和完整性计算 | P1 | 1 天 |
| 3.4 端到端测试 | P0 | 1 天 |

### Phase 4: CircuitBreaker 统一 (3-5 天)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| 4.1 评估并选择最优 CircuitBreaker 实现 | P1 | 1 天 |
| 4.2 迁移所有代码到统一实现 | P1 | 2 天 |
| 4.3 更新测试用例 | P1 | 1 天 |
| 4.4 文档更新 | P2 | 1 天 |

---

## 6. 风险评估 (Risk Assessment)

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 迁移期间数据采集中断 | HIGH | 分阶段迁移，保持旧系统可用 |
| NetworkShield 性能瓶颈 | MEDIUM | 压力测试，必要时扩展锁机制 |
| Python/Node.js 状态不一致 | MEDIUM | 增加状态同步验证 |
| 回归测试覆盖不足 | HIGH | 全面测试套件 |

---

## 7. 成功指标 (Success Metrics)

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 代理系统数量 | 2 | 1 |
| CircuitBreaker 实现 | 7 | 1 |
| FotMob 与 NetworkShield 集成 | ❌ | ✅ |
| 跨语言故障同步 | ❌ | ✅ |
| 代码重复率 | ~30% | <10% |

---

## 8. 结论与建议

### 核心建议

1. **立即行动**: 将 FotMob 采集器迁移到 NetworkShield
2. **归口管理**: 创建 `src/infrastructure/engines/match_engine/` 统一目录
3. **协议统一**: 所有引擎必须实现 `BaseHarvestEngine` 接口
4. **熔断器整合**: 废弃多余实现，统一使用 NetworkShield 熔断器

### 长期愿景

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    未来统一引擎架构                                         │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    NetworkShield V2.0                                │  │
│  │                    (跨语言代理管理中枢)                               │  │
│  │  • 22 节点健康监控                                                    │  │
│  │  • 统一故障计数 (Python + Node.js)                                   │  │
│  │  • 自愈熔断 (2次=15分钟)                                              │  │
│  │  • LRU 会话管理                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                    ┌───────────────┴───────────────┐                       │
│                    ↓                               ↓                       │
│  ┌─────────────────────────────┐   ┌───────────────────────────────────┐  │
│  │  FotMobEngine (Python)      │   │  QuantHarvester (Node.js)         │  │
│  │  • L2 赛况数据               │   │  • L3 赔率轨迹                   │  │
│  │  • 通过 NetworkShield 获取代理│   │  • 通过 NetworkShield 获取代理    │  │
│  │  • 失败上报到 active_registry │   │  • 失败上报到 active_registry     │  │
│  └─────────────────────────────┘   └───────────────────────────────────┘  │
│                    │                               │                       │
│                    └───────────────┬───────────────┘                       │
│                                    ↓                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    GoldenDataMerger                                  │  │
│  │                    (L2 + L3 → 黄金数据)                              │  │
│  │  • 数据融合                                                          │  │
│  │  • 质量评估                                                          │  │
│  │  • 完整性计算                                                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**报告生成时间**: 2026-02-03
**审计执行人**: [Genesis.Audit] Infrastructure Architect Team
**下次审计建议**: Phase 1 完成后进行中期审计
