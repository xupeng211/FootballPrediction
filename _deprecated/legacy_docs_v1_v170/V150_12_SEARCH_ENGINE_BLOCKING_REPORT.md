# V150.12 搜索引擎封锁报告

**日期**: 2026-01-08
**任务**: V150.12 定点打捞战役 - 搜索引擎 URL 发现
**状态**: ❌ 搜索引擎全面封锁自动化搜索

---

## 🔍 尝试的方法

### 方法 1: HTTP 请求到 DuckDuckGo
- **实现**: `requests.get('https://html.duckduckgo.com/html/?q=...')`
- **结果**: ❌ 封锁 - 只返回 1 个链接（DuckDuckGo 自己的链接）
- **响应**: 202 Accepted，但内容被反机器人保护替换

### 方法 2: 直接 URL 构造
- **实现**: 基于 team1-team2 格式构造 URL
- **结果**: ❌ 全部 404 - URL 不存在
- **原因**: OddsPortal 使用 8 位哈希 ID，无法直接预测

### 方法 3: Playwright + Google 搜索
- **实现**: 使用 Chromium 无头浏览器访问 Google 搜索
- **结果**: ❌ 封锁 - 页面标题显示 URL 本身（异常），只返回 3 个链接
- **检测**: Google 检测到无头浏览器并返回受限页面

### 方法 4: Playwright + Bing 搜索
- **实现**: 使用 Chromium 无头浏览器访问 Bing 搜索
- **结果**: ❌ 受限 - 找到链接但都是 Bing 自己的搜索链接
- **检测**: Bing 过滤了所有实际的搜索结果

---

## 🛡️ 搜索引擎反机器人措施

### Google
```
页面标题: https://www.google.com/search?q=... (异常)
链接数量: 3 个（正常应该是 10+ 个搜索结果）
OddsPortal 链接: 0 个
```

### Bing
```
页面标题: 正常（"oddsportal.com ... - Sök"）
链接数量: 8-11 个（但都是 Bing 自己的链接）
OddsPortal 链接: 0 个（所有链接都是 /search?q=...）
```

### DuckDuckGo
```
响应状态: 202 Accepted
实际内容: 反机器人保护页面
真实搜索结果: 0 个
```

---

## 💡 替代方案

### 方案 A: 使用付费搜索 API ⭐ 推荐
**服务提供商**:
- SerpAPI (https://serpapi.com/)
- ScrapingBee (https://www.scrapingbee.com/)
- ZenRows (https://www.zenrows.com/)

**优势**:
- 100% 成功率（专业处理反机器人）
- 按次付费（适合一次性任务）
- 无需维护代理池
- 支持 Google、Bing、DuckDuckGo

**成本估算**:
- 380 次搜索 × $0.002/次 = ~$1-2
- 或订阅套餐 $50/月（如需长期使用）

**示例代码**:
```python
import serpapi

# 使用 SerpAPI
search = serpapi.search({
    "engine": "google",
    "q": 'oddsportal.com "Burnley" "Manchester City" 2023-08-11',
    "api_key": "YOUR_API_KEY"
})

for result in search.get("organic_results", []):
    if "oddsportal.com" in result.get("link", ""):
        print(result["link"])
```

### 方案 B: 使用 V150.9 的 Archive API 拦截
**位置**: `scripts/ops/v150_9_hash_scout.py`

**策略**:
- 访问 OddsPortal Archive 页面
- 拦截 AJAX 响应
- 解析 Base64 + Gzip 编码的数据
- 从中提取比赛 URL

**成功率**: 2.05%（需要改进）

**改进方向**:
- 更准确的 API 端点拦截
- 更好的响应解析
- 增加重试机制

### 方案 C: 手动 URL 发现
**流程**:
1. 导出 380 场比赛清单
2. 手动搜索每场比赛的 OddsPortal URL
3. 批量导入数据库
4. 运行赔率提取

**时间估算**: 380 场 × 30 秒/场 = ~3 小时

### 方案 D: 使用现有数据
**发现**:
```sql
SELECT COUNT(*) FROM matches
WHERE league_name = 'Premier League'
  AND season = '2023/2024'
  AND l3_odds_data IS NOT NULL;
-- 结果: 5 条记录
```

**现有数据**:
- 1 条包含真实的 oddsportal_url（哈希: ID0017KBXO）
- 3 条是 TDD 测试数据（模拟数据）
- 1 条状态为 failed

**策略**:
- 从现有的 1 条真实 URL 开始
- 手动扩展到其他比赛
- 或使用现有数据作为种子

### 方案 E: 直接访问 OddsPortal 页面
**策略**:
- 使用已知的 URL 模式
- 从联赛结果页面开始
- 逐级导航到具体比赛

**URL 模式**:
```
https://www.oddsportal.com/football/england/premier-league/results/
→ 选择 2023/2024 赛季
→ 遍历所有比赛
→ 提取每场比赛的 URL 和哈希
```

---

## 📊 推荐方案对比

| 方案 | 成功率 | 成本 | 时间 | 推荐度 |
|------|--------|------|------|--------|
| **A. SerpAPI** | ⭐⭐⭐⭐⭐ 100% | 💰💰 $1-2 | ⚡⚡⚡ <1小时 | ⭐⭐⭐⭐⭐ 强烈推荐 |
| **B. V150.9 改进** | ⭐⭐ 2-10% | 💰 免费 | ⏰⏰⏰⏰ 1-2天 | ⭐⭐ 需要开发 |
| **C. 手动发现** | ⭐⭐⭐⭐ 100% | ⏰⏰⏰ 3小时 | ⏰⏰⏰ 3小时 | ⭐⭐⭐ 可行 |
| **D. 现有数据** | ⭐ <1% | 💰 免费 | ⚡⚡ <10分钟 | ⭐ 不足够 |
| **E. 直接导航** | ⭐⭐⭐ 未知 | 💰 免费 | ⏰⏰ 2-4小时 | ⭐⭐⭐ 值得尝试 |

---

## 🎯 最终建议

### 短期方案（今天完成）
1. **尝试方案 E**（直接导航）
   ```bash
   python scripts/ops/v150_12_direct_navigation.py
   ```
   - 从联赛结果页面开始
   - 遍历所有 2023/24 赛季比赛
   - 提取 URL 和哈希

2. **如果方案 E 失败，使用方案 A**（SerpAPI）
   - 注册 SerpAPI 账户（免费 100 次搜索）
   - 运行 380 场比赛的搜索
   - 提取并验证 URL

### 长期方案（本周完成）
3. **改进 V150.9**（Archive API 拦截）
   - 分析失败的响应格式
   - 改进解析逻辑
   - 增加容错机制

---

## 📋 TDD 准入红线状态

| 阶段 | 目标 | 实际 | 状态 |
|------|------|------|------|
| A1: 读取 380 场比赛 | 380 | 380 | ✅ 完成 |
| A2: 实现哈希侦察器 | 完整实现 | 完整实现 | ✅ 完成 |
| A3: TDD 测试点火 | 3/3 成功 | 0/3 成功 | ❌ 失败 |
| A4: 验证数据入库 | 3/3 入库 | 0/3 入库 | ❌ 失败 |

**结论**: ❌ **搜索引擎全面封锁，TDD 准入红线未通过**

---

## 🔧 下一步行动

### 立即执行（优先级最高）
1. **实现方案 E**: 直接从 OddsPortal 联赛结果页面导航
   ```bash
   # 创建新脚本
   scripts/ops/v150_13_direct_navigation.py
   ```

2. **或使用 SerpAPI**:
   ```bash
   # 安装 SDK
   pip install google-search-results

   # 获取免费 API 密钥
   # https://serpapi.com/users/sign_up
   ```

### 后续工作（低优先级）
3. 改进 V150.9 Archive API 拦截
4. 研究其他数据源
5. 考虑付费数据服务

---

**报告生成时间**: 2026-01-08 17:43
**V150.12 状态**: ❌ 搜索引擎封锁 - 需要替代方案
**推荐方案**: 方案 A (SerpAPI) 或 方案 E (直接导航)
