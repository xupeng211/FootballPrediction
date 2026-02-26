# V76.0 数据完整性危机报告

**执行时间**: 2026-01-02 17:46 - 17:52
**状态**: 🚨 CRITICAL FAILURE - 需立即回滚
**数据准确率**: **20%** (2/10 随机抽样正确)

---

## 📊 执行摘要

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| URL 填充率 | 80%+ | 100% (24/25赛季) | ⚠️ 数值达标但数据错误 |
| 队名匹配准确率 | 100% | **20%** | 🚨 严重失败 |
| 更新记录数 | ~1,700 | 1,688 | ⚠️ 需全部回滚 |

---

## 🔬 根本原因分析

### 算法缺陷

V76.0 的"精准对齐"逻辑存在致命缺陷：

```python
# v76_precision_aligner.py:234-258
for db_match_id, db_home, db_away, db_date in db_matches:  # 371 条
    for html_match in html_matches:  # 仅 14 条
        home_score = matcher.calculate_similarity(db_home, html_match['home'])
        away_score = matcher.calculate_similarity(db_away, html_match['away'])

        if home_score >= 0.90 and away_score >= 0.90:  # 90% 阈值仍然太宽松
            avg_score = (home_score + away_score) / 2
            if avg_score > best_score:
                best_match = {...}
```

**问题**:
1. **数量不对等**: HTML 仅提取 14-25 场比赛，数据库有 300-371 场
2. **重复分配**: 同一个 URL 被分配给多个数据库记录
3. **阈值过宽**: 90% 相似度导致错误匹配（如 "Liverpool" 匹配 "Everton"）

### 数据验证

| 联赛 | 数据库记录 | HTML 提取 | V76.0 匹配 | 数学可能性 |
|------|-----------|----------|-----------|-----------|
| Premier League | 371 | 14 | 371 | ❌ 不可能 |
| Bundesliga | 300 | 6 | 293 | ❌ 不可能 |
| La Liga | 372 | 12 | 372 | ❌ 不可能 |
| Serie A | 362 | 25 | 362 | ❌ 不可能 |
| Ligue 1 | 290 | 24 | 290 | ❌ 不可能 |

**结论**: 14 个 HTML 提取结果不可能 1-on-1 匹配 371 个数据库记录。

---

## 🚨 数据污染样本

### 随机抽样验证 (10 条)

| match_id | 数据库记录 | URL 路径 | 状态 |
|----------|-----------|---------|------|
| 4535574 | Fiorentina vs Napoli | fiorentina-bologna | ❌ 错误 |
| 4514028 | PSG vs Marseille | brest-lille | ❌ 错误 |
| 4507114 | Sevilla vs Las Palmas | villarreal-leganes | ❌ 错误 |
| 4506571 | West Ham vs Spurs | brentford-fulham | ❌ 错误 |
| 4534763 | Gladbach vs Mainz | bochum-mainz | ❌ 错误 |
| 4514117 | PSG vs Saint-Etienne | marseille-rennes | ❌ 错误 |
| 4535624 | Empoli vs Parma | empoli-parma | ✅ 正确 |
| 4506447 | Liverpool vs Fulham | everton-southampton | ❌ 错误 |
| 4514152 | Toulouse vs Lens | toulouse-lens | ✅ 正确 |
| 4534830 | Bayern vs Gladbach | heidenheim-bochum | ❌ 错误 |

**准确率**: 20% (2/10)

---

## 📋 当前数据库状态

### 按赛季统计 (24/25)

| 联赛 | 总比赛 | 有 URL | 填充率 |
|------|--------|--------|--------|
| Premier League | 380 | 380 | 100% |
| Bundesliga | 306 | 299 | 97.71% |
| La Liga | 380 | 380 | 100% |
| Serie A | - | - | - |
| Ligue 1 | 306 | 306 | 100% |

**总计**: 1,752 条记录被污染

---

## 💡 紧急修复方案

### 方案 A：立即回滚 (推荐)

```sql
-- 清空 V76.0 所有更新
UPDATE matches
SET oddsportal_url = NULL
WHERE updated_at > '2026-01-02 17:40:00';

-- 恢复到 V75.0 之前的状态（57 条有效 URL）
-- 这 57 条是手动验证过的正确数据
```

**优势**:
- ✅ 立即停止数据污染
- ✅ 恢复到干净状态
- ✅ 保留 57 条验证过的正确 URL

### 方案 B：放弃 HTML 提取，直接构造 URL

**核心思路**: 不依赖 HTML 中的哈希 ID，直接基于球队名称构造 URL

```python
def construct_url_directly(country: str, league_slug: str, season: str,
                           home_team: str, away_team: str) -> str:
    # 标准化球队名称
    home_norm = normalize_team_name(home_team)  # Liverpool → liverpool
    away_norm = normalize_team_name(away_team)  # Everton → everton

    # 构造 URL（不含哈希 ID）
    url = f"https://www.oddsportal.com/football/{country}/{league_slug}-{season}/{home_norm}-{away_norm}/"

    return url
```

**优势**:
- ✅ 100% 名称匹配
- ✅ 不依赖 HTML 提取
- ✅ 可批量处理所有 8,940 条记录

**风险**:
- ⚠️ 不含哈希 ID 的 URL 可能无法访问（需验证）

---

## 🎯 下一步行动

| 优先级 | 任务 | 预计时间 |
|--------|------|----------|
| **P0** | 立即回滚 V76.0 所有更新 | 2 分钟 |
| **P0** | 验证回滚后数据库状态 | 5 分钟 |
| **P1** | 测试方案 B（直接 URL 构造） | 30 分钟 |
| **P1** | 验证 10 条直接构造的 URL | 10 分钟 |
| **P2** | 批量填充剩余记录 | 1 小时 |

---

## 📊 V76.0 失败总结

### 失败原因

1. **架构误解**: 假设 HTML 包含所有比赛，但实际只显示部分（14-25 场）
2. **算法缺陷**: 允许 90% 模糊匹配导致错误关联
3. **数学不可能**: 14 个源 → 371 个目标，违反 1-on-1 原则

### 吸取的教训

1. **数量预检**: 在匹配前必须检查源数据数量是否足够
2. **严格验证**: 必须要求 100% 名称匹配，不允许模糊匹配
3. **抽样验收**: 任何批量更新后必须随机抽样验证

---

## 📁 相关文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `scripts/v76_precision_aligner.py` | ❌ 失败 | 逻辑错误 |
| `logs/v76_precision_aligner.log` | ⚠️ 记录错误 | 包含错误的匹配结果 |
| `audit_temp/v76_aligned_records.json` | ❌ 污染数据 | 需删除 |

---

**V76.0 已完全失败。建议立即执行回滚并切换到方案 B（直接 URL 构造）。**

---

**报告生成时间**: 2026-01-02 17:53
**数据准确率**: 20%
**建议**: 立即回滚
