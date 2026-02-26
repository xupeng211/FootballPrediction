# V79.0 Constructor Engine 失败诊断报告

**执行时间**: 2026-01-02 18:51 - 18:53
**目标**: 基于球队名称直接构造 URL（不含哈希 ID），验证可访问性
**执行状态**: ❌ **FAILURE - 方案不可行**

---

## 📊 执行摘要

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| PoC 样本 | 5 | 5 | ✅ 完成 |
| 可访问性 | 200/301/302 | **404** | ❌ 全部失败 |
| 成功率 | > 50% | **0%** | 🚨 方案不可行 |

---

## 🔬 PoC 测试结果

### 测试样本

| # | 比赛 | 构造 URL | 状态码 | 结果 |
|---|------|---------|--------|------|
| 1 | Liverpool vs West Bromwich | `/liverpool-west-bromwich/` | 404 | ❌ |
| 2 | Mainz 05 vs Union Berlin | `/mainz-05-union-berlin/` | 404 | ❌ |
| 3 | Bournemouth vs Wolves | `/afc-bournemouth-wolves/` | 404 | ❌ |
| 4 | Man City vs Liverpool | `/man-city-liverpool/` | 404 | ❌ |
| 5 | Leverkusen vs Hoffenheim | `/bayer-leverkusen-hoffenheim/` | 404 | ❌ |

**成功率**: 0/5 (0%)

---

## 🔍 深度诊断

### Playwright 诊断结果

使用 Playwright 访问构造的 URL：

```
GET /football/england/premier-league-2020-2021/liverpool-west-bromwich/
→ 404 Not Found
→ Error: ERR_HTTP_RESPONSE_CODE_FAILURE
```

### 根本原因

**OddsPortal 的 URL 必须包含哈希 ID**

对比分析：

| 不含哈希 (构造) | 含哈希 (真实) |
|----------------|--------------|
| `/liverpool-west-bromwich/` | `/liverpool-crystal-palace-lh1OJUtR/` |
| `/man-city-liverpool/` | `/southampton-manchester-city-6yO4xthU/` |
| `/bayer-leverkusen-hoffenheim/` | `/werder-bremen-rb-leipzig-CbGZMKne/` |

**哈希 ID 格式**: 7-8 位大小写字母数字 (如 `lh1OJUtR`, `CbGZMKne`, `p44guBED`)

---

## 💡 核心结论

### 方案 A 不可行

**直接构造 URL（不含哈希 ID）无法访问 OddsPortal**

原因：
1. OddsPortal 服务器要求 URL 必须包含哈希 ID
2. 返回 404 而非重定向
3. 哈希 ID 无法预测或构造

### 哈希 ID 特征分析

从 57 条有效 URL 中提取的哈希 ID 样本：

```
lh1OJUtR  (7 位)
CbGZMKne  (7 位)
p44guBED  (7 位)
OlGpsXq1  (7 位)
2TI0VAEN  (7 位)
b7USgAT6  (7 位)
jVjHFI03  (7 位)
hnqjYTeK  (7 位)
rR8t8HcK  (7 位)
QJFTcmK7  (7 位)
```

**特征**:
- 长度：7-8 位
- 字符集：大小写字母 + 数字
- 分布：完全随机
- **无法通过球队名称推导**

---

## 📋 历史方案总结

| 方案 | 版本 | 思路 | 结果 | 准确率 |
|------|------|------|------|--------|
| HTML 提取 (单页) | V75.0 | 24/25 赛季结果页 | ❌ 数据污染 | 20% |
| HTML 提取 (精准) | V76.0 | 1-on-1 匹配 | ❌ 数据污染 | 20% |
| HTML 提取 (25页) | V78.0 | 5 赛季全扫描 | ❌ 数据污染 | 0% |
| 直接构造 (无哈希) | V79.0 | 省略哈希 ID | ❌ 404 错误 | N/A |

**共同失败原因**: OddsPortal 的 URL 架构设计要求完整的哈希 ID

---

## 🚀 最终结论与建议

### 不可行的方案

1. ❌ **HTML 提取**：Results 页面不包含完整历史数据
2. ❌ **直接构造**：无哈希 ID 的 URL 返回 404
3. ❌ **模糊匹配**：产生数据交叉污染

### 可行的方向

#### 方案 A：API 反向工程

**目标**: 找到 OddsPortal 的 API 接口

**可能路径**:
1. 使用浏览器 DevTools 监控网络请求
2. 查找 JSON API 端点
3. 分析请求参数和响应格式

**优势**:
- ✅ 可能返回完整的比赛列表
- ✅ 可能包含哈希 ID

**风险**:
- ⚠️ API 可能有加密/签名
- ⚠️ 可能有频率限制

#### 方案 B：分页深入研究

**目标**: 研究 OddsPortal Results 页面的分页机制

**可能路径**:
1. 检查 URL 参数 (`?page=2`)
2. 检查"加载更多"按钮
3. 检查滚动加载机制

**优势**:
- ✅ 可能获取完整历史数据

**风险**:
- ⚠️ V78.0 已扫描 25 页面，未发现分页

#### 方案 C：接受现状

**思路**: 使用现有的 57 条有效 URL

**执行**:
1. 保留 57 条验证过的 URL
2. 对于缺失 URL 的比赛，使用替代数据源
3. 或者手动补充关键比赛的 URL

---

## 📁 相关文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `scripts/v79_constructor_poc.py` | ❌ 失败 | 直接 URL 构造引擎 |
| `scripts/v79_deep_diagnosis.py` | ⚠️ 诊断 | Playwright 深度诊断 |

---

## 📊 V79.0 最终结论

### 失败总结

1. **PoC 测试 100% 失败** (5/5 返回 404)
2. **OddsPortal 要求哈希 ID**，无法省略
3. **哈希 ID 无法预测或构造**

### 技术结论

**OddsPortal URL 架构**:
```
/football/{country}/{league}-{season}/{home}-{away}-{hash}/
                                                        ^^^^
                                                必须包含 (7-8位随机字符)
```

### 下一步建议

**推荐方向**:

1. **API 反向工程** (高优先级)
   - 使用浏览器 DevTools 监控网络请求
   - 查找可能的 API 端点
   - 分析请求/响应格式

2. **分页深入研究** (中优先级)
   - 仔细检查 Results 页面的加载机制
   - 尝试不同的 URL 参数
   - 检查是否有 AJAX 请求

3. **接受现状** (低优先级)
   - 保留 57 条有效 URL
   - 使用替代数据源

---

**V79.0 Constructor Engine 失败。OddsPortal 的哈希 ID 架构使得直接构造 URL 不可行。**

---

**报告生成时间**: 2026-01-02 18:53
**PoC 成功率**: 0%
**建议**: 切换到 API 反向工程或分页研究
