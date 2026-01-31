# 足球赛果预测系统｜项目愿景

```
████████╗██╗   ██╗██████╗ ███████╗████████╗██╗   ██╗██████╗ ███████╗
╚══██╔══╝██║   ██║██╔══██╗██╔════╝╚══██╔══╝██║   ██║██╔══██╗██╔════╝
   ██║   ██║   ██║██████╔╝█████╗     ██║   ██║   ██║██████╔╝█████╗
   ██║   ██║   ██║██╔══██╗██╔══╝     ██║   ██║   ██║██╔══██╗██╔══╝
   ██║   ╚██████╔╝██████╔╝███████╗   ██║   ╚██████╔╝██████╔╝███████╗
   ╚═╝    ╚═════╝ ╚═════╝ ╚══════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚══════╝
```

> **版本**: V1.0.0
> **生效日期**: 2025-12-24
> **作者**: V19.4.1 架构团队
> **状态**: **ACTIVE - 所有技术决策必须符合本愿景**

---

## 📌 一句话愿景

> **"以年化 25% 的真实收益率为北极星指标，构建一个可验证、可复制、可持续的体育预测系统，在无杠杆、不赌心态的前提下，通过数据科学实现长期价值。"**

---

## 🎯 核心目标 (North Star Metrics)

### 1. 财务目标

| 指标 | 目标值 | 测量方式 | 状态 |
|------|--------|----------|------|
| **年化收益率 (CAGR)** | **25%** | `(最终净值 / 初始本金)^(1/年数) - 1` | 🎯 北极星指标 |
| **月平均收益率** | ~2.0% | 复利计算月度平均值 | 🟡 追踪中 |
| **最大回撤 (Max DD)** | < 15% | `max((峰值 - 当前) / 峰值)` | 🔴 硬约束 |
| **夏普比率** | > 1.5 | `(年化收益 - 无风险利率) / 年化波动率` | 🟢 质量指标 |
| **盈亏比** | > 1.8 | `平均盈利 / 平均亏损` | 🟢 质量指标 |

### 2. 风险约束（硬红线）

| 约束类型 | 限制值 | 违规后果 | 代码级检查 |
|----------|--------|----------|------------|
| **单笔下注比例** | **≤ 5%** | 拒绝执行 | `RiskMonitor._check_stake_limit()` |
| **杠杆使用** | **0% (严禁)** | 系统抛出异常 | `RiskMonitor._verify_no_leverage()` |
| **连续亏损熔断** | 5 次 | 暂停交易 24h | `RiskMonitor._check_circuit_breaker()` |
| **单日最大亏损** | 10% | 暂停交易 | `RiskMonitor._check_daily_loss_limit()` |

---

## 🛡️ 核心原则

### 原则一：无杠杆 (No Leverage)

> **"杠杆是一把双刃剑，而本项目只使用单刃——本金。"**

- **定义**: 严禁使用任何形式的杠杆（融资融券、配资、杠杆倍数等）
- **理由**: 杠杆放大波动，与"长期价值"的愿景背道而驰
- **代码强制**: `leverage_enabled == True` 会触发 `VisionViolationException`

### 原则二：EV 区间纪律 (Expected Value Discipline)

> **"只在 EV 落在 6%-10% 的区间内出手，这是数学给我们的护城河。"**

- **定义**: 只在期望收益率 (Expected Value) 落在 `[6%, 10%]` 区间时执行交易
- **下限 6%**: 过滤掉噪音交易，确保每次出手有足够的正期望
- **上限 10%**: 防止"看起来太美"的陷阱（通常意味着数据问题或市场误解）
- **代码强制**: `ExecutionFilter._check_ev_range()`

### 原则三：执行纪律 (Execution Discipline)

> **"模型预测是科学，执行决策是艺术。95% 的时间我们等待，5% 的时间我们出击。"**

- **执行率**: 理想状态 < 5% (100 场比赛只出手 ≤ 5 次)
- **耐心**: 等待市场犯错，而不是强迫交易
- **纪律**: 一旦触发"三不原则"，无条件跳过

### 原则四：可验证性 (Verifiability)

> **"没有审计，就没有信任。每一笔交易必须有完整的记录链。"**

- **审计链**: 市场价格 → 模型预测 → EV 计算 → 执行决策 → 结果记录
- **日志**: 所有决策必须记录到 `logs/boxing_day/signal_execution.json`
- **回测**: 严格样本外回测，严禁未来数据泄露

---

## 🚫 三不原则 (Execution Guardrails)

当 `signal_execution.json` 生成后，手动执行前的最后三道防线：

### ⛔ 原则一：价格贬值不投

```python
IF market_price_now < market_price_signal THEN
    SKIP_EXECUTION
    REASON = "价格已贬值，Edge 已消失"
END IF
```

### ⛔ 原则二：风控熔断不投

```python
IF risk_check.is_circuit_breaker == true OR consecutive_losses >= 5 THEN
    SKIP_EXECUTION
    REASON = "熔断已触发或连续亏损超限"
END IF
```

### ⛔ 原则三：信心不足不投

```python
IF model_prediction.confidence < 45.0 THEN
    SKIP_EXECUTION
    REASON = "模型信心不足，Edge 不稳定"
END IF
```

---

## 📊 愿景契合度评分系统

每次 `yield_audit_v19.py` 运行时，系统会自动计算"愿景契合度评分"：

### 评分维度

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| **EV 区间契合度** | 30% | EV 落在 6%-10% 区间的交易占比 |
| **执行纪律** | 20% | 实际执行率是否 < 5% |
| **风险控制** | 25% | 单笔下注 ≤ 5%，无杠杆违规 |
| **回撤控制** | 15% | 最大回撤 < 15% |
| **审计完整性** | 10% | 所有交易有完整日志记录 |

### 总分计算

```python
vision_score = (
    ev_range_compliance * 0.30 +
    execution_discipline * 0.20 +
    risk_control * 0.25 +
    drawdown_control * 0.15 +
    audit_completeness * 0.10
)

# 愿景契合度等级
if vision_score >= 90:
    grade = "EXCELLENT - 完全符合愿景"
elif vision_score >= 75:
    grade = "GOOD - 基本符合愿景"
elif vision_score >= 60:
    grade = "WARNING - 需要调整"
else:
    grade = "CRITICAL - 严重偏离愿景"
```

---

## 🧬 技术架构与愿景对齐

### V19.4.1 架构决策

| 组件 | 愿景对齐 | 实现方式 |
|------|----------|----------|
| **5% Delta 过滤** | EV 纪律 | `MarketLiveMonitor.DELTA_THRESHOLD = 5.0` |
| **单笔下注限制** | 风险约束 | `RiskMonitor.MAX_STAKE_PCT = 0.05` |
| **连续亏损熔断** | 风险约束 | `RiskMonitor.CIRCUIT_BREAKER_LIMIT = 5` |
| **DataValidator** | 可验证性 | 100/100 质量分数确保数据可信 |
| **概率校准** | EV 精度 | Isotonic 回归提升预测可信度 |

---

## 📈 发展路线图

### Phase 1: 验证期 (2025-2026)
- **目标**: 在 500 场比赛中验证系统可行性
- **成功标准**: 年化收益率达到 20%+，最大回撤 < 15%

### Phase 2: 优化期 (2026-2027)
- **目标**: 优化特征工程，提升 EV 精度
- **成功标准**: 年化收益率稳定在 25%+，执行率 < 5%

### Phase 3: 扩张期 (2027+)
- **目标**: 扩展到其他联赛，构建投资组合
- **成功标准**: 多联赛融合，夏普比率 > 2.0

---

## 🔄 Changelog (愿景迭代记录)

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| **V1.0.0** | 2025-12-24 | 初始愿景定义 | V19.4.1 架构团队 |

---

## ⚖️ 愿景违背处理流程

如果系统检测到任何违背愿景的行为：

### 1. 轻微违背 (Score: 60-75)
```
ACTION: 记录警告日志
OUTPUT: logger.warning("VISION DEVIATION: {reason}")
REVIEW: 每周人工审核
```

### 2. 中度违背 (Score: 45-60)
```
ACTION: 暂停交易，发送告警
OUTPUT: logger.critical("VISION VIOLATION: {reason}")
REVIEW: 立即人工介入
```

### 3. 严重违背 (Score: < 45)
```
ACTION: 系统熔断，强制停止
OUTPUT: raise VisionViolationException("CRITICAL: {reason}")
REVIEW: 紧急架构审查
```

---

## 📝 引用

> "The goal is not to predict the future, but to identify situations where the market is mispricing the probability of outcomes, and to exploit those edge cases systematically."
>
> — **Project Philosophy**

---

**最后更新**: 2025-12-24
**下次审查**: 2026-01-01 (每季度审查)
**所有权**: V19.4.1 架构团队
