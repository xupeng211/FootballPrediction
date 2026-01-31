# V150.19 数据映射校准 - 准入报告

**日期**: 2026-01-09
**状态**: ⚠️ **部分准入 - 映射校准完成，提取策略需优化**

---

## 📋 执行摘要

### ✅ 已完成任务

| 任务 | 状态 | 结果 |
|------|------|------|
| **代理验证** | ✅ 完成 | 7890 端口通畅 |
| **数据库扫描** | ✅ 完成 | 388 场记录扫描完成 |
| **映射校准** | ✅ 完成 | 69 场正确对齐 (17.8%) |
| **URL 提取** | ✅ 完成 | 成功提取队名信息 |
| **页面访问** | ✅ 完成 | 成功加载目标页面 |
| **数据提取** | ⚠️ 部分完成 | 页面加载成功，但选择器需优化 |

---

## 📊 映射校准清单（前 10 场）

| # | 比赛 ID | 主队 | 客队 | URL 中的队名 | 对齐状态 | 匹配分数 |
|---|---------|------|------|-------------|----------|----------|
| 1 | 4193450 | Burnley | **Manchester City** ❌ | burnley - newcastle | ❌ 错误 | 0.5 |
| 2 | 4193453 | Brighton & Hove Albion | **Luton Town** ❌ | tottenham - town | ❌ 错误 | 0.0 |
| 3 | **4193454** | **Everton** ✅ | **Fulham** ✅ | everton - fulham | ✅ **正确** | **1.0** |
| 4 | 4193456 | **Newcastle United** ❌ | Aston Villa | brentford - villa | ❌ 错误 | 0.0 |
| 5 | 4193451 | **Arsenal** ❌ | **Nottingham Forest** ❌ | nottingham - forest | ❌ 错误 | 0.0 |
| 6 | 4193452 | **AFC Bournemouth** ❌ | **West Ham United** ❌ | bournemouth - sheffield | ❌ 错误 | 0.0 |
| 7 | 4193455 | **Sheffield United** ❌ | **Crystal Palace** ❌ | sheffield - crystal | ❌ 错误 | 0.0 |
| 8 | 4193457 | **Brentford** ❌ | **Tottenham Hotspur** ❌ | brentford - arsenal | ❌ 错误 | 0.5 |
| 9 | **4193458** | **Chelsea** ✅ | **Liverpool** ✅ | chelsea - liverpool | ✅ **正确** | **1.0** |
| 10 | 4193459 | **Manchester United** ❌ | **Wolverhampton** ❌ | manchester - brighton | ❌ 错误 | 0.5 |

### 关键发现

**正确对齐**: 69 / 388 (17.8%)
**错误对齐**: 319 / 388 (82.2%)

**Burnley vs Manchester City 问题**:
- 数据库记录: Burnley vs Manchester City
- URL 实际指向: burnley-newcastle (Newcastle United)
- **映射偏差**: URL 与球队信息不匹配

---

## 🎯 选中比赛：Everton vs Fulham（揭幕战）

**正确对齐证明**:

| 属性 | 数据库值 | URL 值 | 匹配状态 |
|------|----------|--------|----------|
| **比赛 ID** | 4193454 | - | - |
| **日期** | 2023-08-12 | - | - |
| **主队** | Everton | everton | ✅ 匹配 |
| **客队** | Fulham | fulham | ✅ 匹配 |
| **URL** | - | everton-fulham-ID0062ESJB | ✅ 有效 |
| **匹配分数** | - | - | **1.0 (完美)** |

---

## 📸 实弹提取证据

### 页面加载成功

```
✅ 代理连接: http://172.25.16.1:7890
✅ Ghost Protocol: applied (playwright-stealth + V144.0 fingerprint + V150.0 TLS)
✅ 页面访问: https://www.oddsportal.com/football/england/premier-league/everton-fulham-ID0062ESJB/
✅ 页面加载: load (4秒)
```

### 导出的 JSON 样本

**文件**: `logs/v150_19/mapping_calibration_list.json`

```json
{
  "timestamp": "2026-01-08T18:11:08.131015+00:00",
  "total_records": 388,
  "aligned_count": 69,
  "misaligned_count": 319,
  "top_10_records": [
    {
      "fotmob_id": "4193454",
      "match_date": "2023-08-12 00:00:00",
      "home_team_db": "Everton",
      "away_team_db": "Fulham",
      "home_team_url": "everton",
      "away_team_url": "fulham",
      "url": "https://www.oddsportal.com/football/england/premier-league/everton-fulham-ID0062ESJB/",
      "is_aligned": true,
      "alignment_score": 1.0
    }
  ]
}
```

---

## ⚠️ 数据提取问题分析

### 问题：Node_P 数据未找到

**提取器日志**:
```
🎯 提取 Node_P 时序: 4193454 - Everton vs Fulham
✅ 提取完成: 0 个采样点
```

**根因分析**:

1. **选择器问题**: 当前选择器 `"row.textContent.includes('Pinnacle')"` 可能无法匹配页面中的实际元素
2. **页面结构**: OddsPortal 可能使用了不同的 DOM 结构或类名
3. **动态加载**: Pinnacle 数据可能通过 JavaScript 动态加载，需要等待

**建议修复**:
- 需要检查实际页面 DOM 结构
- 更新选择器以匹配实际元素
- 可能需要触发 hover/click 交互来加载数据

---

## 🔄 下一步行动

### 立即行动 (高优先级)

1. **DOM 结构分析**: 使用浏览器开发工具检查 Everton vs Fulham 页面的实际 DOM 结构
2. **选择器优化**: 更新 Pinnacle 数据提取选择器
3. **交互触发**: 实现 hover/click 交互来加载历史数据

### 数据质量修复 (中优先级)

1. **清理脏数据**: 删除所有 v150_13_ 开头的错误映射
2. **重新对齐**: 使用正确的 URL 更新 319 场错误映射
3. **批量验证**: 对所有 380 场执行映射校准

---

## ✅ 准入结论

### 已达成目标

| 目标 | 状态 | 证据 |
|------|------|------|
| **代理连通** | ✅ 通过 | 7890 端口验证成功 |
| **页面渲染** | ✅ 通过 | 页面加载 4 秒，Ghost Protocol 应用成功 |
| **映射校准** | ✅ 通过 | 388 场扫描完成，69 场正确对齐 |
| **URL 提取** | ✅ 通过 | 成功提取 URL 中的队名并标准化 |

### 待优化项

| 目标 | 状态 | 需要修复 |
|------|------|----------|
| **Node_P 时序数据** | ⚠️ 待优化 | 选择器需要匹配实际 DOM 结构 |
| **采样点 >= 3** | ⚠️ 待优化 | 需要实现 hover/click 交互触发 |

### 建议

**部分准入 - 映射校准阶段完成，数据提取阶段需优化后全量收割**

---

**审计执行人**: V150.19 Data Architecture Team
**报告生成时间**: 2026-01-09 02:11:49 UTC
**版本**: V150.19-Mapping-Calibration
