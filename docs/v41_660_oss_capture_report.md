# V41.660 OSS Intelligence Capture - 综合总结报告

**版本**: V41.660 / V41.661 / V41.662
**日期**: 2026-01-22
**任务**: 汲取开源逻辑突破 OddsPortal 哈希封锁
**状态**: 部分完成 - 需要进一步研究

---

## 执行摘要

### 任务目标
参考开源项目（OddsHarvester, Mg30, Stack Overflow 2024/12 方案），重构 OddsPortal 哈希提取方法，目标在英超 100 场缺失记录上达到 90%+ 成功率。

### 核心发现
1. **OddsPortal 使用 Vue.js SPA 架构** - 比赛数据通过 JavaScript 动态加载，不在初始 HTML 中
2. **AJAX API 返回加密数据** - `ajax-all-events` 端点返回 AES 加密的 JSON，但当前密码/盐值无法解密
3. **旧方法数据质量问题** - 1370 条历史记录存在跨赛季哈希重用问题

### 最终方案
**V41.662 Hybrid Capture** - 混合方案：
- 利用历史同日记录（仅限相同日期 ±3 天）
- DOM 深度扫描 + JavaScript 注入（Vue.js SPA 限制）
- 模糊匹配回退（85%+ 相似度阈值）

---

## 技术分析

### 1. OddsPortal 架构发现

#### 1.1 Vue.js Single Page Application
```
初始 HTML:
├── 仅包含导航和应用外壳
├── 比赛数据通过 JavaScript 动态注入
└── 114 个链接（仅导航，无比赛数据）

动态加载:
├── ajax-user-data/t/premier-league-2025-2026/ - 用户配置
├── ajax-all-events/topEvents - 加密比赛数据
└── Vue.js 组件延迟渲染比赛链接
```

#### 1.2 加密数据格式（从 OSS 研究）
```
响应格式: Base64(加密数据:IV)
加密算法: AES-256-CBC 或 AES-128-CBC
密钥派生: PBKDF2 (SHA256, 1000 迭代)

Stack Overflow 2024/12 密码:
  Password: %RtR8AB&\nWsh=AQC+v!=pgAe@dSQG3kQ
  Salt: orieC_jQQWRmhkPvR6u2kzXeTube6aYupiOddsPortal

实际测试结果:
  ✗ 解密失败 - UTF-8 decode error
  → 密码/盐值可能已更新
```

### 2. 实现方案

#### V41.660 - URL Hash Extraction
**文件**: `scripts/ops/v41_660_url_hash_extraction.py`

**策略**: 直接从比赛页面 URL 提取 8 位哈希
```
URL 格式: /football/england/premier-league/team1-team2-HASH/
正则模式: r'/football/[^/]+/[^/]+/.+-([a-zA-Z0-9]{8}|ID[a-zA-Z0-9]{8})/'
```

**测试结果**:
- 找到 114 个链接
- 0 个匹配哈希模式
- **结论**: Vue.js SPA 不在初始 DOM 中渲染比赛链接

#### V41.661 - Ultimate Capture
**文件**: `scripts/ops/v41_661_ultimate_capture.py`

**策略**:
1. 网络请求拦截（捕获 XHR/fetch）
2. JavaScript 注入触发 Vue.js 数据加载
3. 深度等待和滚动（10 次 × 300px）
4. DOM 扫描 + Feed URL 解析

**测试结果**:
- 捕获到 6 个 API 请求（ajax-user-data, ajax-all-events 等）
- 0 个 feed URLs
- **结论**: Feed URL 未通过标准 XHR 加载

#### V41.662 - Hybrid Capture ⭐
**文件**: `scripts/ops/v41_662_hybrid_capture.py`

**策略优先级**:
1. **历史缓存匹配** - 仅限相同日期 ±3 天的记录
2. **DOM 深度扫描** - 扩展等待（90 秒）+ JavaScript 注入
3. **模糊匹配回退** - 85%+ 相似度阈值

**关键创新**:
```python
def _fuzzy_search_cache(record):
    for (home_team, away_team, match_date), cached in self.v650_results.items():
        # 只考虑相同日期的记录（允许 ±3 天误差）
        date_diff = abs((target_date - match_date).days)
        if date_diff > 3:
            continue
        # ... 模糊匹配逻辑
```

### 3. 数据质量问题发现

#### 3.1 跨赛季哈希重用问题
```
旧方法（hybrid_v40, collision_v40）错误:
  同一球队组合 → 相同哈希（忽略日期/赛季）

示例:
  2025-08-22: West Ham vs Chelsea → hash: W4Wumejr
  2023-08-20: West Ham vs Chelsea → hash: W4Wumejr ❌ (错误!)

影响:
  - 1370 条记录中有 691 条使用 hybrid_v40_3_10 方法
  - 342 条使用 collision_v40_10 方法
  - 无法简单复用这些哈希
```

#### 3.2 数据库约束
```sql
-- 哈希唯一性约束
CREATE FUNCTION check_unique_hash_before_insert()
  → RAISE EXCEPTION if hash already exists

结果:
  - 防止了错误哈希的传播 ✅
  - 但需要为每场比赛找到正确哈希 ⚠️
```

---

## 测试结果

### V41.662 混合方案测试

```
测试配置:
  联赛: Premier League
  限制: 10 条记录
  训练数据: 1370 条历史记录

结果:
  总处理数: 10
  成功匹配: 0
  匹配失败: 10
  成功率: 0.00%

失败原因:
  - 历史缓存中无相同日期记录（2025-12-xx vs 2023-20xx）
  - DOM 扫描找到 114 个链接但 0 个比赛链接
  - Vue.js SPA 限制
```

### 方法分布统计

```
现有数据库方法:
  hybrid_v40_3_10:    691 条 (50.4%)
  collision_v40_10:   342 条 (25.0%)
  season_sweep_v4:     92 条 (6.7%)
  collision_v40_7:     84 条 (6.1%)
  hybrid_v40_3_6:      58 条 (4.2%)
  collision_v40_11:    52 条 (3.8%)
  collision_v40_9:     36 条 (2.6%)
  其他方法:           15 条 (1.1%)

英超缺失记录: 1383 条
```

---

## 核心挑战

### 1. Vue.js SPA 动态内容加载
**问题**: 比赛数据不在初始 HTML 中
**尝试方案**:
  ✓ networkidle 等待
  ✓ 滚动触发懒加载
  ✓ JavaScript 注入触发 Vue 更新
  ✓ 网络请求拦截

**结果**: 仍无法捕获动态插入的比赛链接

### 2. 加密 API 端点
**问题**: ajax-all-events 返回加密数据，当前密码无法解密
**尝试方案**:
  ✓ AES-256-CBC 解密（Stack Overflow 密码）
  ✓ AES-128-CBC 解密（16 字节密钥）

**结果**: UTF-8 decode error - 密码/盐值可能已更新

### 3. 哈希唯一性约束
**问题**: 旧方法跨赛季重用哈希，导致冲突
**解决方案**:
  ✓ V41.662 只复用相同日期的哈希
  ⚠️ 需要为新日期的比赛找到新哈希

---

## 建议后续方案

### 短期方案（1-2 周）
1. **更新 OSS 解密密码**
   - 反编译最新的 app.js
   - 查找当前密码和盐值
   - 测试 ajax-all-events 解密

2. **优化 DOM 等待策略**
   - 增加等待时间到 120 秒
   - 尝试更多 Vue.js 触发方法
   - 使用 Playwright 的 `wait_for_selector` 等待特定元素

3. **URL 构造尝试**
   - 基于球队名构造可能的 URL
   - 测试不同 URL 格式
   - 使用 HEAD 请求验证 URL 有效性

### 中期方案（1-2 月）
1. **实现浏览器自动化回填**
   - 使用完整浏览器（非 headless）
   - 手动导航到联赛页面
   - 等待完整加载后提取数据

2. **逆向工程 Vue.js API**
   - 分析 Vue.js 应用代码
   - 找到数据加载端点
   - 模拟 API 请求

3. **多源数据融合**
   - 结合其他赔率源数据
   - 使用球队名 + 日期交叉验证
   - 降低对单一哈希的依赖

### 长期方案（3-6 月）
1. **训练机器学习模型**
   - 基于 1370 条正确哈希训练
   - 预测新比赛的哈希格式
   - 持续学习和优化

2. **建立哈希数据库**
   - 收集更多历史哈希数据
   - 建立哈希到比赛的正向映射
   - 支持模糊搜索和推荐

---

## 文件清单

### 核心实现
- `src/core/oddsportal_decryptor.py` - AES 解密模块（基于 Stack Overflow）
- `tests/core/test_oddsportal_decryptor.py` - TDD 测试（12/12 通过）
- `scripts/ops/v41_660_url_hash_extraction.py` - URL 哈希提取
- `scripts/ops/v41_661_ultimate_capture.py` - 终极捕获（网络拦截）
- `scripts/ops/v41_662_hybrid_capture.py` - 混合方案 ⭐

### 调试输出
- `logs/debug_pages/v41_660_page_20260122_154510.html` - 页面快照

---

## 总结

### 成就 ✅
1. 完成 OSS 情报收集 - 研究 Stack Overflow、GitHub 项目
2. 实现 TDD 测试框架 - 12/12 测试通过
3. 发现 Vue.js SPA 架构限制 - 解释了为什么传统方法失败
4. 创建混合方案 V41.662 - 最大化利用现有数据
5. 识别数据质量问题 - 跨赛季哈希重用

### 挑战 ⚠️
1. Vue.js SPA 动态内容难以捕获
2. 加密 API 密码可能已更新
3. 需要为每场具体比赛找到正确哈希
4. 90%+ 成功率目标尚未达成

### 下一步 🎯
1. **优先**: 更新 OSS 解密密码（反编译 app.js）
2. **备选**: 完整浏览器自动化回填
3. **长期**: ML 模型预测哈希

---

**报告生成时间**: 2026-01-22
**生成者**: V41.660 OSS Intelligence Capture Team
