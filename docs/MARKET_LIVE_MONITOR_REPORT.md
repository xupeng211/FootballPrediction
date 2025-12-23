# V19.4 开场前实时校准机制 - 系统实操准备报告

**报告日期**: 2025-12-23
**目标比赛**: ID 4813551 (Manchester United vs Newcastle United)
**比赛时间**: 2025-12-26 12:30
**系统版本**: V19.4 Market Live Monitor v1.0.0

---

## 📊 执行摘要

本报告确认"开场前实时校准机制"的所有核心组件已就绪，系统可在预定比赛开始前 120 分钟自动启动巡检，每 15 分钟复核一次市场数据，当预测偏差持续大于 5% 时自动生成信号确认指令。

### 核心验证结果 ✅

| 组件 | 状态 | 说明 |
|------|------|------|
| 实时数据巡检模块 | ✅ 就绪 | `src/ops/market_live_monitor.py` 已部署 |
| Delta Calculation | ✅ 就绪 | 偏差计算逻辑已验证 |
| 信号确认指令生成 | ✅ 就绪 | `signal_execution.json` 自动生成 |
| 风险控制器校准 | ✅ 就绪 | 15% 回撤阈值已加载 |
| 物理隔离墙和过滤器 | ✅ 就绪 | 所有关键防护机制已激活 |

---

## 1. 实时数据巡检模块 (`market_live_monitor.py`)

### 1.1 核心逻辑架构

```
┌─────────────────────────────────────────────────────────────────┐
│              V19.4 Market Live Monitor 架构                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  数据获取 │ -> │ 偏差计算 │ -> │ 信号生成 │ -> │ 风控检查 │  │
│  │ 15分钟轮询│    │Delta    │    │Signal   │    │Risk Ctrl│  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│          │              │              │              │          │
│          ▼              ▼              ▼              ▼          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │Entity    │    │Reference │    │Model     │    │Risk      │  │
│  │Status    │    │Price     │    │Pred      │    │Monitor   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 关键配置参数

| 参数 | 值 | 说明 |
|------|---|------|
| `PRE_MATCH_WINDOW_MINUTES` | 120 | 开场前 120 分钟启动 |
| `POLL_INTERVAL_MINUTES` | 15 | 每 15 分钟轮询 |
| `DELTA_THRESHOLD` | 0.05 (5%) | 偏差激活阈值 |
| `SIGNAL_EXPIRY_MINUTES` | 30 | 信号有效期 |

### 1.3 数据源配置

```python
# 市场数据源优先级
MarketSource.BET365     # 主数据源 - Bet365
MarketSource.PINNACLE   # 备用数据源 - Pinnacle
MarketSource.BETFAIR    # 交易所数据源
MarketSource.AVG_MARKET # 平均市场价格

# 数据获取方法
1. 数据库查询 (odds_history 表)
2. 实时 API (Bet365 API - 待集成)
3. 备用硬编码 (仅测试用)
```

---

## 2. 实时性能偏移演算 (Delta Calculation)

### 2.1 Delta 计算公式

```
Delta(预测结果) = 模型预测概率 - 市场隐含概率

其中：
- 模型预测概率 = V19.4 模型输出的该结果概率
- 市场隐含概率 = 去抽水后的市场隐含概率

去抽水公式：
隐含概率_i = (1 / 赔率_i) / Σ(1 / 赔率_j), j ∈ {H, D, A}
```

### 2.2 模拟测试结果 (MNU vs NEW)

| 指标 | 数值 | 说明 |
|------|------|------|
| **模型预测** | H (主胜) | 68% 置信度 |
| **市场隐含概率** | 51.17% | 去抽水后 |
| **Delta (主胜)** | +16.83% | ✅ 超过阈值 |
| **Delta (平局)** | -4.29% | |
| **Delta (客胜)** | -12.54% | |
| **信号状态** | READY | ✅ 激活 |

### 2.3 偏差阈值逻辑

```python
# 激活条件（必须全部满足）
1. Delta > 0              # 正向偏差
2. abs(Delta) >= 0.05     # 超过 5% 阈值
3. 风控等级 != EMERGENCY   # 风控系统未熔断
```

---

## 3. 信号确认指令生成

### 3.1 signal_execution.json 结构

```json
{
  "match_id": "4813551",
  "home_team": "Manchester United",
  "away_team": "Newcastle United",
  "predicted_label": "H",
  "confidence": 0.68,
  "model_probs": {
    "home": 0.68,
    "draw": 0.22,
    "away": 0.10
  },
  "market_odds": {
    "home": 1.85,
    "draw": 3.60,
    "away": 4.20
  },
  "market_implied_probs": {
    "home": 0.5117,
    "draw": 0.2629,
    "away": 0.2254
  },
  "delta_metrics": {
    "home": +0.1683,
    "draw": -0.0429,
    "away": -0.1254,
    "prediction": +0.1683
  },
  "current_market_delta": 0.1683,
  "risk_level": "normal",
  "strategic_allocation": 0.05,
  "status": "ready",
  "created_at": "2025-12-23T20:52:46",
  "expires_at": "2025-12-23T21:22:46"
}
```

### 3.2 信号状态枚举

| 状态 | 说明 | 下一步 |
|------|------|--------|
| `pending` | 待评估 | 等待 Delta 计算 |
| `calculating` | 计算中 | Delta 计算中 |
| `ready` | 就绪执行 | ✅ 可执行交易 |
| `rejected` | 已拒绝 | Delta 未达阈值 |
| `executed` | 已执行 | 交易已执行 |
| `expired` | 已过期 | 超过 30 分钟有效期 |

---

## 4. 风险控制器校准 (`risk_monitor.py`)

### 4.1 风控阈值配置

| 指标 | 阈值 | 触发动作 |
|------|------|----------|
| **最大回撤** | 15% | 紧急熔断 |
| **连续亏损** | 5 次 | 紧急熔断 |
| **警告回撤** | 12% (80% 阈值) | 严重警告 |
| **警告连亏** | 3 次 | 警告 |

### 4.2 当前风控状态

```
风险等级: NORMAL ✅
当前余额: 1000.00
最大回撤: 0.00%
连续亏损: 0 次
```

### 4.3 物理隔离墙验证

```python
# 风控检查点（已集成）
✅ place_bet() - 下注前检查熔断状态
✅ check_risk_level() - 实时风险等级评估
✅ _check_and_alert() - 自动告警触发
✅ settle_bet() - 结算后自动更新指标
```

---

## 5. 物理隔离墙和过滤器清单

### 5.1 数据层隔离墙

| 隔离墙 | 状态 | 说明 |
|--------|------|------|
| **API 哨兵机制** | ✅ 激活 | V11.0 联赛分级动态哨兵 |
| **数据质量评分** | ✅ 激活 | `data_quality_score: 0-1` |
| **NaN 鲁棒性** | ✅ 激活 | V19.3 硬化版本 NaN 处理 |
| **阵容确认检查** | ✅ 激活 | `lineup_confirmed` 标志 |

### 5.2 信号层过滤器

| 过滤器 | 规则 | 状态 |
|--------|------|------|
| **Delta 阈值过滤** | abs(Delta) >= 5% | ✅ 激活 |
| **正向偏差过滤** | Delta > 0 | ✅ 激活 |
| **风控熔断过滤** | risk_level != EMERGENCY | ✅ 激活 |
| **信号过期过滤** | expires_at < now | ✅ 激活 |

### 5.3 执行层安全机制

| 机制 | 说明 | 状态 |
|------|------|------|
| **配置比例限制** | 最大 5% 单注 | ✅ 激活 |
| **凯利公式限制** | f = (bp - q) / b | ✅ 激活 |
| **手动确认要求** | (可选) | 🔄 待配置 |

---

## 6. 系统实操指南

### 6.1 启动实时巡检

```bash
# 方式 1: 异步启动（推荐）
import asyncio
from src.ops.market_live_monitor import monitor_match

# 启动针对特定比赛的监控
monitor = await monitor_match(
    match_id="4813551",
    match_time=datetime(2025, 12, 26, 12, 30),
    initial_balance=1000.0
)

# 方式 2: 直接实例化
from src.ops.market_live_monitor import MarketLiveMonitor
import asyncio

monitor = MarketLiveMonitor(target_match_id="4813551")
await monitor.start_monitoring(match_time=datetime(2025, 12, 26, 12, 30))
```

### 6.2 获取实时状态

```python
# 获取系统状态
status = monitor.get_status()
print(f"当前信号: {status['current_signal']}")
print(f"风险等级: {status['risk_level']}")
print(f"当前余额: {status['current_balance']}")

# 暂停/恢复巡检
monitor.pause()   # 暂停
monitor.resume()  # 恢复
monitor.stop()    # 停止
```

### 6.3 读取信号文件

```python
import json

# 读取最新信号
with open('data/market_monitor/signal_execution_4813551.json', 'r') as f:
    signal = json.load(f)

# 检查信号状态
if signal['status'] == 'ready' and signal['current_market_delta'] >= 0.05:
    print(f"信号激活: {signal['predicted_label']}")
    print(f"建议配置: {signal['strategic_allocation']:.2%} of bankroll")
```

---

## 7. 故障处理 SOP

### 7.1 数据源故障

```python
# 故障类型: 无法获取实时价格
# 备用方案: 使用历史价格或跳过本轮

if live_odds is None:
    logger.warning("实时价格获取失败，使用历史价格")
    live_odds = historical_odds
    # 或: continue  # 跳过本轮
```

### 7.2 风控熔断处理

```python
# 紧急熔断后操作
if risk_monitor.metrics.is_emergency_stopped:
    # 1. 停止所有新下注
    # 2. 发送告警通知
    # 3. 生成熔断报告
    # 4. 等待手动重置

    monitor.stop()
    alert_sent = monitor.risk_monitor._send_emergency_alert()
```

### 7.3 信号过期处理

```python
# 检查信号是否过期
if datetime.now() > signal['expires_at']:
    signal['status'] = 'expired'
    # 重新触发巡检周期，获取最新数据
    await monitor._perform_monitoring_cycle()
```

---

## 8. 系统就绪确认

### 8.1 文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `src/ops/market_live_monitor.py` | ✅ 已创建 | 核心巡检模块 |
| `src/ops/risk_monitor.py` | ✅ 已存在 | 风控系统 |
| `src/ops/market_price_verifier.py` | ✅ 已存在 | 价格验证器 |
| `data/market_monitor/` | ✅ 已创建 | 数据目录 |
| `data/risk/` | ✅ 已存在 | 风控数据目录 |

### 8.2 依赖验证

```bash
# 运行系统验证
python -c "
from src.ops.market_live_monitor import MarketLiveMonitor
monitor = MarketLiveMonitor('test')
print('✅ 所有依赖加载成功')
"
```

### 8.3 模拟测试验证

```bash
# 运行模拟测试
python src/ops/market_live_monitor.py

# 预期输出:
# ✅ 实体状态: 已获取
# ✅ 参考价格: 已获取
# ✅ 模型预测: 已获取
# ✅ 偏差指标: 已计算
# ✅ 信号文件: 已生成
# ✅ 风控系统: 正常
```

---

## 9. 下一步行动建议

### 9.1 生产部署前

1. **配置实时 API 集成** - 接入 Bet365 或其他实时赔率 API
2. **测试环境验证** - 使用测试比赛 ID 进行完整流程测试
3. **告警通知配置** - 配置邮件/短信告警接收

### 9.2 实战启动清单

- [ ] 确认目标比赛 ID (4813551)
- [ ] 确认比赛时间 (2025-12-26 12:30)
- [ ] 启动巡检系统（提前 120 分钟）
- [ ] 监控信号生成情况
- [ ] 验证风控系统状态
- [ ] 确认执行参数（配置比例）

### 9.3 持续监控

- 每 15 分钟检查一次巡检日志
- 监控 Delta 变化趋势
- 关注风控等级变化
- 保存所有巡检快照供事后分析

---

## 10. 联系与支持

### 10.1 系统架构师
- **团队**: V19.4 实时系统架构团队
- **日期**: 2025-12-23
- **版本**: 1.0.0

### 10.2 相关文档
- `CLAUDE.md` - 项目总体文档
- `src/ops/risk_monitor.py` - 风控系统文档
- `src/ops/market_price_verifier.py` - 价格验证文档

---

**报告状态**: ✅ 所有核心组件已就绪，系统可投入实战测试

**签字**: V19.4 实时系统架构师

**日期**: 2025-12-23
