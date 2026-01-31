# V78.0 Great Mapping 失败诊断报告

**执行时间**: 2026-01-02 18:16 - 18:21
**目标**: 通过遍历 25 个历史汇总页，补齐 8,930 个 URL 缺口
**执行状态**: ❌ **FAILURE - 已回滚**

---

## 📊 执行摘要

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 填充率 | 80%+ | 5.04% | ❌ 未达标 |
| 新增 URL | ~8,930 | 396 | ❌ 部分完成 |
| 数据准确率 | 100% | **0%** | 🚨 严重失败 |

---

## 🔬 根本原因分析

### 问题发现

随机抽样验证 5 条新增 URL，**0 条正确**：

```
数据库记录              → URL 路径                      匹配？
Real Sociedad vs Valencia → sevilla-barcelona           ❌
Rayo Vallecano vs Betis   → mallorca-getafe             ❌
Elche vs Athletic Club    → elche-alaves               ❌
Frosinone vs Udinese      → fiorentina-monza           ❌
Torino vs Roma            → torino-napoli              ❌
```

### 根本原因

**OddsPortal Results 页面只显示部分比赛，不是完整历史记录**

| 联赛 x 赛季 | 数据库记录 | HTML 提取 | 缺口比例 |
|-------------|-----------|----------|---------|
| Premier League 20/21 | 380 | 9 | **97.6%** 缺失 |
| Premier League 21/22 | 380 | 18 | **95.3%** 缺失 |
| Bundesliga 20/21 | 306 | 3 | **99.0%** 缺失 |
| Serie A 20/21 | 380 | 24 | **93.7%** 缺失 |
| Ligue 1 20/21 | 380 | 27 | **92.9%** 缺失 |

**平均值**: 每个赛季页面只显示 **6.7%** 的比赛（~20-25 场 / 300-380 场）

### 算法缺陷

即使使用 **0.95 相似度阈值**，仍然产生错误匹配：

```python
# 问题逻辑
for db_match in db_matches:  # 380 条
    for html_match in html_matches:  # 仅 9 条
        home_score = matcher.calculate_similarity(db_home, html_match['home'])
        away_score = matcher.calculate_similarity(db_away, html_match['away'])

        if home_score > 0.95 and away_score > 0.95:  # 仍然错误！
            # 分配 URL
```

**原因**:
- 380 个数据库记录竞争 9 个 HTML 提取的 URL
- 即使 0.95 阈值，仍有足够多的"接近"球队名称产生错误匹配
- 例如：Real Sociedad (皇家社会) 与 Sevilla (塞维利亚) 在模糊匹配下可能达到 0.95+

---

## 📋 执行结果详情

### HTML 提取统计

| 联赛 | 20/21 | 21/22 | 22/23 | 23/24 | 24/25 | 合计 |
|------|-------|-------|-------|-------|-------|------|
| Premier League | 9 | 18 | 11 | 11 | 14 | 63 |
| Bundesliga | 3 | 2 | 6 | 11 | 6 | 28 |
| La Liga | 15 | 11 | 15 | 11 | 12 | 64 |
| Serie A | 24 | 24 | 24 | 24 | 25 | 121 |
| Ligue 1 | 27 | 24 | 27 | 23 | 24 | 125 |
| **合计** | **78** | **79** | **83** | **80** | **81** | **401** |

**总计提取**: 401 个 URL

### 数据库更新统计

| 联赛 | 20/21 | 21/22 | 22/23 | 23/24 | 24/25 | 合计 |
|------|-------|-------|-------|-------|-------|------|
| Premier League | 9 | 18 | 11 | 10 | 13 | 61 |
| Bundesliga | 2 | 2 | 6 | 11 | 6 | 27 |
| La Liga | 15 | 11 | 15 | 11 | 12 | 64 |
| Serie A | 24 | 24 | 24 | 24 | 24 | 120 |
| Ligue 1 | 26 | 24 | 27 | 23 | 24 | 124 |
| **合计** | **76** | **79** | **83** | **79** | **79** | **396** |

**总计更新**: 396 条（其中 5 条 URL 验证失败）

---

## 🔄 回滚操作

```sql
-- 回滚 V78.0 所有更新
UPDATE matches
SET oddsportal_url = NULL
WHERE updated_at > '2026-01-02 10:16:00'  -- UTC 时间
  AND oddsportal_url IS NOT NULL;

-- 结果：UPDATE 396
```

**回滚后状态**:
- 总比赛: 8,997
- 有 URL: 57
- 填充率: 0.63%

---

## 💡 核心结论

### OddsPortal 页面限制

**Results 页面不是完整历史记录，只显示最近 ~20-25 场比赛**

可能原因：
1. **分页机制**: 需要翻页才能查看完整历史
2. **懒加载**: 滚动加载更多比赛
3. **API 驱动**: 数据通过 API 动态加载，不在初始 HTML 中

### 依赖 HTML 提取的方案不可行

| 方案 | V75.0 | V76.0 | V78.0 |
|------|-------|-------|-------|
| 提取方法 | 单页面 24/25 | 单页面 24/25 | 25 页面全赛季 |
| HTML 提取数 | 67 | 81 | 401 |
| 数据准确率 | 20% | 20% | **0%** |
| 结论 | ❌ 失败 | ❌ 失败 | ❌ 失败 |

**共同问题**: HTML 源码不包含完整历史数据

---

## 🚀 下一步建议

### 方案 A：放弃 HTML 提取，直接构造 URL（推荐）

**核心思路**: 不依赖哈希 ID，直接基于球队名称构造 URL

```python
def construct_url_directly(league: str, season: str,
                           home_team: str, away_team: str) -> str:
    from scripts.v75_url_builder import normalize_team_name

    # 联赛映射
    league_config = {
        "Premier League": ("england", "premier-league"),
        "Bundesliga": ("germany", "bundesliga"),
        "La Liga": ("spain", "laliga"),
        "Serie A": ("italy", "serie-a"),
        "Ligue 1": ("france", "ligue-1"),
    }

    country, slug = league_config[league]
    season_url = season.replace("/", "-")  # 20/21 → 20-21

    home_norm = normalize_team_name(home_team)
    away_norm = normalize_team_name(away_team)

    # 不含哈希 ID 的 URL
    url = f"https://www.oddsportal.com/football/{country}/{slug}-{season_url}/{home_norm}-{away_norm}/"

    return url
```

**优势**:
- ✅ 可批量处理 8,940 条缺失 URL
- ✅ 100% 名称匹配
- ✅ 不依赖 HTML 抓取

**风险**:
- ⚠️ 不含哈希 ID 的 URL 可能重定向或 404（需验证）

**执行步骤**:
1. 随机构造 10 个 URL 并验证可访问性
2. 如果可行，批量构造并更新所有 8,940 条记录
3. 如果失败，执行方案 B

### 方案 B：研究 OddsPortal 分页/翻页机制

**目标**: 找到加载完整历史记录的方法

**可能方向**:
1. 检查 Results 页面是否有"下一页"按钮
2. 检查是否有 AJAX 请求加载更多数据
3. 检查 URL 参数（如 `?page=2`）

**风险**:
- ⚠️ 需要额外研发时间
- ⚠️ 可能触发反爬机制

### 方案 C：接受低填充率，聚焦 57 条有效 URL

**思路**:
- 保留 57 条验证过的正确 URL
- 其他比赛使用替代数据源或手动收集

---

## 📁 相关文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `scripts/v78_great_mapping.py` | ❌ 失败 | 25 页面抓取逻辑 |
| `logs/v78_great_mapping.log` | ⚠️ 记录错误 | 包含错误的匹配结果 |
| `audit_temp/v78_mapping_results.json` | ❌ 污染数据 | 需删除 |

---

## 📊 V78.0 最终结论

### 失败总结

1. **HTML 提取方案三次失败** (V75.0, V76.0, V78.0)
2. **数据准确率 0%** (5/5 随机抽样错误)
3. **OddsPortal Results 页面不包含完整历史数据**

### 吸取的教训

1. **样本验证必须先行**: 在批量更新前必须验证数据质量
2. **数量不对等 = 必然失败**: 401 个源 → 8,940 个目标，不可能 1-on-1 匹配
3. **0.95 阈值仍然不够**: Real Sociedad vs Sevilla 仍可达到 0.95+

### 推荐行动

**立即执行方案 A 测试**:
1. 随机构造 10 个 URL（不含哈希 ID）
2. 验证是否可访问（200 状态码）
3. 如果成功，批量构造并更新 8,940 条记录

---

**V78.0 五年大巡航失败。建议放弃 HTML 提取方案，切换到直接 URL 构造。**

---

**报告生成时间**: 2026-01-02 18:21
**数据准确率**: 0%
**建议**: 立即测试方案 A（直接 URL 构造）
