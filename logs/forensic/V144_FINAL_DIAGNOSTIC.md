# V144.000 最终诊断报告 - 数据提取失败分析

**诊断日期**: 2026-01-27
**任务状态**: 🔴 FAILED - 系统性数据提取失败
**测试覆盖**: 60/100 场比赛（已终止）

---

## 执行摘要

V144.000 终极回填验证任务在测试过程中发现**系统性数据提取失败**：所有已处理的 60 场比赛（100%）均报告 `records=0`，即虽然成功检测到赔率单元格，但未提取到任何有效数据。

**关键发现**:
- ✅ V141.000 模块化架构工作正常
- ✅ V143.000 并发优化有效（13 路并发稳定）
- ✅ Signal Radar 成功检测到赔率单元格
- ❌ **悬停操作未触发数据加载** (根本原因)
- ❌ **100% 数据提取失败率**

---

## 测试结果统计

| 指标 | 结果 | 目标 | 状态 |
|------|------|------|------|
| **已处理比赛** | 60 | 100 | 终止 |
| **成功提取** | 0 | >90 | ❌ FAILED |
| **失败提取** | 60 | <10 | ❌ 100% |
| **成功率** | 0% | >90% | ❌ FAILED |
| **单元格检测率** | 100% | >95% | ✅ PASS |

---

## 数据流分析

### 成功的环节

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 数据库采样 ✅                                            │
│    - 成功采样 100 场黄金矿区比赛                            │
│    - URL 映射正确（从 matches_mapping 获取）                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 页面加载 ✅                                              │
│    - 成功导航到 OddsPortal 页面                             │
│    - 页面正常响应                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Signal Radar ✅                                          │
│    - 成功检测到 24-57 个赔率单元格                           │
│    - Adaptive Bypass 正常工作                               │
└─────────────────────────────────────────────────────────────┘
```

### 失败的环节

```
┌─────────────────────────────────────────────────────────────┐
│ 4. SurgicalInteraction ❌ (失效点)                         │
│    - 悬停操作未触发数据加载                                 │
│    - Modal/浮层可能未正确触发                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. TrajectoryParser ❌                                      │
│    - 未捕获到有效数据                                       │
│    - 返回 0 条记录                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Storage ❌                                               │
│    - 空数据跳过: records=0                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 根本原因分析

### 问题定位

**主要嫌疑**: SurgicalInteraction 的 `performReliableHover()` 方法未成功触发数据加载

**证据**:
1. Signal Radar 检测到 24-57 个赔率单元格（DOM 结构正常）
2. Adaptive Bypass 成功绕过 .dat 包检测
3. 但 TrajectoryParser 返回 0 条记录

**可能的子原因**:

#### 1. 悬停操作失效
- **概率**: 70%
- **分析**:
  - `scrollIntoView` 可能未正确定位元素
  - 悬停坐标可能偏移
  - Modal 触发可能需要更长的等待时间
- **验证方法**: 添加详细的悬停操作日志

#### 2. DOM 结构变化
- **概率**: 20%
- **分析**:
  - OddsPortal 可能更新了页面结构
  - CSS 选择器可能需要更新
  - 浮层/Modal 的 class 名称可能变化
- **验证方法**: 检查页面 DOM 快照

#### 3. 事件监听失效
- **概率**: 10%
- **分析**:
  - Playwright 的 hover() 事件可能被拦截
  - 页面可能使用了自定义事件处理
- **验证方法**: 尝试使用 JS 触发事件

---

## 日志证据分析

### 典型日志序列

```
[V138.000] ========== OVERLAY PURGE START ==========
[V138.000] forceRemoveOverlays config: false
[V136.000] ========== ADAPTIVE SIGNAL RADAR ==========
[V136.000] Adaptive timeout: 5000 ms
[V136.000] Fallback timeout: 15000 ms
[V136.000] 📡 Signal radar NOW MONITORING for .dat packets...
[V136.000] ⏱️  Adaptive timeout - checking if data is pre-loaded...
[V136.000] ✅ ADAPTIVE BYPASS: 27 odds cells visible, proceeding anyway
[V136.000] 📊 Adaptive bypass active, brief stabilization wait...
[V136.000] Signal result: BYPASS
[V136.000] ✅ Odds content found: 27 cells
[WARN] [storage] [V87.300] 空数据跳过: entityId=XXX, records=0
```

### 关键观察

1. **forceRemoveOverlays config: false** - 覆盖层移除未启用
2. **✅ ADAPTIVE BYPASS** - 绕过检测成功
3. **✅ Odds content found: 27 cells** - 检测到单元格
4. **⚠️ 空数据跳过: records=0** - 无数据存储

**缺失的日志**:
- 没有 "Hovering on cell..." 日志
- 没有 "Modal detected..." 日志
- 没有 "Trajectory points extracted..." 日志

这表明 **SurgicalInteraction 的悬停操作可能根本未执行**。

---

## V141.000 模块验证结果

| 模块 | 状态 | 说明 |
|------|------|------|
| **TelemetryService** | ✅ Working | 遥测数据收集正常 |
| **SignalRadar** | ✅ Working | 信号检测正常 |
| **SurgicalInteraction** | ❌ Failed | 悬停操作失效 |

---

## V143.000 并发优化验证

| 配置 | 值 | 验证结果 |
|------|-----|----------|
| **HARVEST_MAX_CONCURRENT** | 13 | ✅ 稳定运行 |
| **处理速度** | ~15-20 秒/场 | ✅ 符合预期 |
| **批次处理** | 13 场/批 | ✅ 正常 |
| **超时问题** | 无超时 | ✅ 已解决 |

**结论**: V143.000 的 13 路并发配置有效，未出现 137 超时问题。

---

## 修复建议

### 立即行动 (P0)

1. **启用强制覆盖层移除**
   ```javascript
   forceRemoveOverlays: true  // 从 false 改为 true
   ```

2. **增加悬停等待时间**
   ```javascript
   hoverStabilizeMs: 3000  // 从 1500 增加到 3000
   ```

3. **添加详细日志**
   ```javascript
   console.log('[SurgicalInteraction] Hovering on cell:', cellIndex);
   console.log('[SurgicalInteraction] Modal detected:', modalDetected);
   ```

### 进一步调查 (P1)

4. **检查 DOM 结构变化**
   - 使用 `page.content()` 获取页面 HTML
   - 对比历史 DOM 快照
   - 更新 CSS 选择器

5. **尝试替代悬停方法**
   ```javascript
   // 方法 1: JS 模拟悬停
   await page.evaluate((el) => {
     el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
   }, cell);

   // 方法 2: 强制点击
   await cell.click({ force: true });
   ```

---

## 数据纯度验证 (V140.000)

由于所有比赛数据提取失败，无法验证：
- ❌ Initial 标签覆盖率
- ❌ 时间戳正确性
- ❌ UTC 格式强制

**需要**: 修复后重新运行 100 场测试以验证 V140.000 修复。

---

## 结论

**V144.000 任务状态**: 🔴 FAILED

**根本原因**: SurgicalInteraction 的悬停操作未触发 OddsPortal 的数据加载浮层

**影响**:
- 100% 数据提取失败率
- 无法验证 V140.000 数据纯度修复
- 无法验证 V141.000 完整功能

**下一步**:
1. 修复悬停操作逻辑
2. 重新运行 100 场测试
3. 验证 V140.000 数据纯度

---

## 技术债务

1. **SurgicalInteraction 需要增强**
   - 添加更详细的错误日志
   - 实现多种悬停策略（降级机制）
   - 添加 DOM 快照保存用于调试

2. **测试覆盖不足**
   - 缺少端到端集成测试
   - 缺少悬停操作单元测试

3. **文档缺失**
   - 缺少 SurgicalInteraction 故障排除指南
   - 缺少 OddsPortal DOM 结构文档

---

*Generated by V144.000 Final Diagnostic Report*
*Senior Site Reliability Engineer (Data Purity Specialist)*
*Date: 2026-01-27*

