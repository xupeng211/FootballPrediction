# V41.257 "Optical Calibration" - 根因分析报告

**报告日期**: 2026-01-20
**版本**: V41.257 RC1
**分析师**: V41.257 Calibration Team

---

## 执行摘要 (Executive Summary)

V41.257 校准扫描发现 **90% 的赔率数据存在异常**，其中：
- **16 场比赛** (27%)：`closing[0] = 8.75` (固定异常值)
- **38 场比赛** (63%)：`MH_Closing ≈ Initial_Price` (结构异常)

这表明 `industrial_auditor.py` 的数据提取逻辑存在系统性错误。

---

## 1. 异常模式分类

### 1.1 ANOMALY_875 (固定值异常)

**特征**: `closing_price[0] = 8.75` (固定值)

**案例**: Arsenal vs Crystal Palace
```python
Initial_Price: [1.28, 6.8, 16.0]     # min at index 0 (Home Win)
Closing_Price: [8.75, 1.26, 6.11]     # min at index 1 (Draw) ← 异常!
MH_Opening:  [13.0, 1.24, 5.95]       # min at index 1 (Draw)
MH_Closing:  [1.27, 6.6, 15.5]        # min at index 0 (Home Win)
```

**问题分析**:
1. `closing[0] = 8.75` 不匹配任何合理的赔率值
2. `MH_Closing` (Home Win) ≠ `Closing_Price` (Draw)
3. `MH_Closing ≈ Initial_Price` (结构匹配)

**来源假设**:
- **假设 1**: 8.75 是 HTML 解析时的错误提取值
- **假设 2**: 8.75 是某个统计值 (max/avg) 的误识别
- **假设 3**: 8.75 是 `values[0]` 的直接提取，但 `values[0]` 本身就是错误的

**证据**:
| 比赛 | MH_Opening Max | 8.75 匹配? |
|------|----------------|------------|
| Atalanta vs Frosinone | 8.83 | ✓ 匹配 (±0.08) |
| Arsenal vs Crystal Palace | 13.0 | ✗ 不匹配 |
| Brentford vs Nottm Forest | 4.56 | ✗ 不匹配 |

**结论**: 8.75 **不是** MH_Opening max，而是解析阶段的系统性错误。

---

### 1.2 ANOMALY_STRUCTURE (结构异常)

**特征**: `MH_Closing ≈ Initial_Price` (但应该匹配 `Closing_Price`)

**案例**: Darmstadt vs Eintracht Frankfurt
```python
Initial_Price: [3.95, 3.65, 2.14]     # min at index 2 (Away Win)
Closing_Price: [3.92, 3.69, 1.98]     # min at index 2 (Away Win)
MH_Closing:  [3.9, 3.6, 2.12]         # ≈ Initial_Price
```

**问题分析**:
- `MH_Closing` 应该匹配 `Closing_Price`，但实际匹配 `Initial_Price`
- 这表明 `Movement_History` 的构建逻辑可能有问题

**假设**:
1. `Movement_History` 数组结构为 `[Closing, ..., Initial]` (反转)
2. `SequenceProcessor._process_standard()` 的切片逻辑错误

---

## 2. SequenceProcessor 逻辑审查

### 2.1 当前实现

```python
# src/core/scrapers/industrial_auditor.py:196-198
def _process_standard(values: list[float]) -> PriceVector:
    closing = values[:3]   # [0:3]  - 前 3 位
    initial = values[-3:]  # [-3:]  - 后 3 位
    movement = values[3:-3]  # 中间序列
```

**文档注释**:
```python
"""
标准逻辑：
- [0:3] → Closing_Price（当前状态）
- [-3:] → Initial_Price（初始状态）
- 中间序列 → Movement_History
"""
```

### 2.2 逻辑假设

当前假设 `values` 数组结构为：
```
[Closing, ..., Movement ..., Initial]
 [0:3]                    [-3:]
```

这意味着：
- **时间顺序**: Closing → ... → Initial (倒序)
- **数据来源**: 网页上的数据可能按 "最新数据在前" 的顺序排列

### 2.3 验证测试

**测试案例**: Bayern München vs Hoffenheim (consistent case)
```python
Initial_Price: [1.15, 12.0, 24.0]
Closing_Price: [1.14, 10.3, 18.4]
MH_Closing: [1.14, 10.3, 18.4]        # == Closing_Price ✓
```

**结论**: 对于 consistent cases，`MH_Closing == Closing_Price`，符合预期。

---

## 3. 根因分析 (Root Cause Analysis)

### 3.1 问题定位

**ANOMALY_875**:
- `closing[0] = 8.75` 是 HTML 解析阶段的错误
- 可能来源：
  1. 错误的 CSS 选择器
  2. 错误的表格行列定位
  3. 混淆了不同类型的数据 (如平均赔率、最大赔率等)

**ANOMALY_STRUCTURE**:
- `MH_Closing ≈ Initial_Price` 表明 `movement_history` 构建错误
- 可能原因：
  1. `values` 数组本身的结构假设错误
  2. `SequenceProcessor` 的切片逻辑需要调整

### 3.2 核心假设

**假设 A**: `values` 数组结构正确，但 HTML 解析提取了错误的值
- 8.75 是某个无关数据的误提取
- 修复方案：修正 HTML 解析逻辑

**假设 B**: `values` 数组结构假设错误
- 实际结构可能是 `[Initial, ..., Closing]` (正序)
- 修复方案：交换 `closing` 和 `initial` 的切片逻辑

**假设 C**: 不同联赛/不同页面的 HTML 结构不同
- 某些页面数据顺序是 `[Closing, ..., Initial]`
- 其他页面是 `[Initial, ..., Closing]`
- 修复方案：添加自动检测逻辑

---

## 4. 数据一致性检查

### 4.1 Consistent Cases (10%)

**特征**:
- `MH_Closing == Closing_Price` (或非常接近)
- 列顺序一致 (min position 相同)

**示例**: Bayern München vs Hoffenheim
```python
Initial_Price: [1.15, 12.0, 24.0]
Closing_Price: [1.14, 10.3, 18.4]
MH_Closing: [1.14, 10.3, 18.4]        # == Closing_Price ✓
```

**结论**: 这些比赛的数据提取是正确的。

### 4.2 Inconsistent Cases (90%)

**特征**:
- `MH_Closing ≠ Closing_Price`
- `closing[0] = 8.75` 或 `MH_Closing ≈ Initial_Price`

**结论**: 这些比赛的数据提取存在错误，需要重新采集。

---

## 5. 修复建议

### 5.1 短期方案 (数据修复)

1. **标记异常数据**:
   ```sql
   UPDATE match_odds_intelligence
   SET quality_rating = 'anomaly_detected'
   WHERE closing_price[0] = 8.75
      OR movement_history IS NOT NULL
      AND ABS(movement_history[1] - initial_price[1]) < 0.5
   ```

2. **重新采集异常数据**:
   - 使用 V41.255 harvester 重新采集 54 场异常比赛
   - 验证新数据的列顺序一致性

### 5.2 长期方案 (代码修复)

1. **修正 HTML 解析逻辑**:
   - 检查 `industrial_auditor.py` 的 `_extract_from_tables()` 方法
   - 添加列顺序自动检测
   - 验证 CSS 选择器的准确性

2. **增强 SequenceProcessor**:
   - 添加列顺序验证逻辑
   - 检测 `values[0]` 是否为合理赔率值 (1.01 - 1000.0)
   - 添加异常值熔断机制

3. **添加数据质量检查**:
   - 存储前验证 `MH_Closing ≈ Closing_Price`
   - 检测固定异常值 (如 8.75)
   - 记录详细的 extraction metadata

---

## 6. 下一步行动

1. **立即执行**:
   - [ ] 使用 V41.255 harvester 重新采集 54 场异常比赛
   - [ ] 验证新数据的列顺序一致性
   - [ ] 生成修复前后对比报告

2. **短期优化**:
   - [ ] 修正 `industrial_auditor.py` 的 HTML 解析逻辑
   - [ ] 添加列顺序自动检测
   - [ ] 实施异常值熔断机制

3. **长期改进**:
   - [ ] 建立数据质量监控看板
   - [ ] 实施 V41.258 "Data Sentinel" 持续监控
   - [ ] 完善单元测试覆盖

---

## 7. 附录

### 7.1 异常案例清单

| Match ID | Teams | Anomaly Type | Confidence |
|----------|-------|--------------|------------|
| 4193732 | Arsenal vs Crystal Palace | ANOMALY_875 | 0.95 |
| 4205543 | Celta Vigo vs Real Sociedad | ANOMALY_875 | 0.95 |
| 4193733 | Brentford vs Nottingham Forest | ANOMALY_875 | 0.95 |
| 4230724 | Atalanta vs Frosinone | ANOMALY_875 | 0.95 |
| 4221901 | Darmstadt vs Eintracht Frankfurt | ANOMALY_STRUCTURE | 0.85 |
| ... | ... | ... | ... |

### 7.2 技术术语表

- **MH**: Movement History (价格变动历史)
- **MH_Opening**: Movement_History[:3] (历史开盘价)
- **MH_Closing**: Movement_History[-3:] (历史终盘价)
- **ANOMALY_875**: closing[0] = 8.75 固定值异常
- **ANOMALY_STRUCTURE**: MH_Closing ≈ Initial_Price 结构异常

---

**报告结束**

*V41.257 Calibration Team*
*2026-01-20*
