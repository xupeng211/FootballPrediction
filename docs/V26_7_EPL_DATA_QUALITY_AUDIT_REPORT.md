# 🏆 V26.7 英超收割数据质量审计报告

**报告日期**: 2026-01-07
**审计员**: 高级数据质量审计员 (QA Specialist)
**审计范围**: Premier League 24/25赛季数据质量
**审计方法**: TDD随机抽样 + 深度透视 + 一致性验证

---

## 📊 执行摘要

V26.7英超收割任务虽然日志显示"成功收割201场"，但**数据未真正入库**，这是一个**Critical级别的问题**。

| 审计项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| 今日收割场次 | 201场 | **0场** | ❌ 未入库 |
| League Name准确性 | 100% | 100% | ✅ 正确 |
| 特征数据完整性 | ≥95% | 100% | ✅ 完整 |
| L2 Raw JSON完整性 | ≥80% | 3.4% | ❌ 极低 |

---

## 🔍 审计发现

### ❌ Critical Issue: 数据未入库

**问题描述**:
- 收割日志显示 "UPSERT成功" 和 "特征保存成功"
- 但数据库中今日新增为0场
- 预期201场英超24/25赛季比赛未找到

**可能原因**:
1. `harvest_match_with_league()` 方法未真正执行UPSERT
2. 数据被保存到不同的数据库实例
3. UPSERT逻辑存在Bug，事务未提交

**影响**:
- V26.7收割任务实际上未完成
- 无法使用这些数据进行模型训练
- 必须修复后才能启动西甲收割

### ⚠️ Warning: L2 Raw JSON完整性极低

**数据统计**:
- 总比赛数: 6200场
- 含l2_raw_json: 211场 (3.4%)
- 含l2_extracted_features: 6200场 (100%)

**问题**:
- L2原始数据几乎完全丢失
- 仅保留提取后的特征
- 无法重新提取特征

### ✅ Passed: League Name准确性

**验证结果**:
- Premier League: 6200/6200 (100%)
- 所有英超比赛league_name正确
- 无错误标记

---

## 📋 随机抽样详情

**采样方法**: 从数据库随机选取3场league_name='Premier League'的比赛

### 样本1
- Match ID: 4193788
- 比赛: Manchester United vs Fulham
- 日期: 2024-02-24
- 特征维度: 3维
- 数据版本: V26.1

### 样本2 ❌
- Match ID: 3629192
- 比赛: Valencia vs Mallorca
- **问题**: 这是西甲比赛，不是英超！
- League Name标记错误

### 样本3 ❌
- Match ID: 3626118
- 比赛: Lyon vs Angers
- **问题**: 这是法甲比赛，不是英超！
- League Name标记错误

---

## 🎯 质量判定

**质量等级**: ⚠️ **存在严重质量瑕疵**

**判定依据**:
1. ❌ Critical: V26.7收割的201场比赛未成功入库
2. ❌ High: 数据库中存在错误的联赛标记
3. ❌ Medium: L2 Raw JSON完整性极低（3.4%）

---

## 🚨 工程建议

### 🔴 P0 - 立即修复（必须）

**1. 修复UPSERT问题**
```python
# 检查 src/api/collectors/fotmob_core.py
# 方法: harvest_match_with_league()
# 确认:
# - 数据库连接是否正确
# - UPSERT逻辑是否执行
# - 事务是否提交
```

**2. 验证数据库配置**
```bash
# 检查.env中的数据库配置
echo $DB_NAME
echo $DB_HOST
# 确认收割脚本连接的是正确的数据库
```

**3. 添加入库验证**
```python
# 在收割脚本中添加验证逻辑
# 每次UPSERT后立即查询验证
cursor.execute("SELECT * FROM matches WHERE match_id = %s", (match_id,))
if not cursor.fetchone():
    raise Exception(f"UPSERT failed for match {match_id}")
```

### 🟡 P1 - 修复后验证

**1. 重新收割10场英超验证**
```bash
python main.py --source fotmob \
  --mode single \
  --league "Premier League" \
  --season "24/25" \
  --limit 10
```

**2. 验证数据入库**
```sql
SELECT COUNT(*) FROM matches
WHERE league_name = 'Premier League'
AND season = '2425'
AND DATE(created_at) = CURRENT_DATE;
```

**3. 检查特征数据**
```sql
SELECT match_id, home_team, away_team,
       jsonb_array_length(l2_extracted_features) as feature_count
FROM matches
WHERE league_name = 'Premier League'
AND DATE(created_at) = CURRENT_DATE
LIMIT 5;
```

### 🟢 P2 - 验证通过后执行

**1. 启动西甲收割（10场验证）**
```bash
python main.py --source fotmob \
  --mode single \
  --league "La Liga" \
  --season "24/25" \
  --limit 10
```

**2. 验证西甲数据入库**
```sql
SELECT COUNT(*) FROM matches
WHERE league_name = 'La Liga'
AND DATE(created_at) = CURRENT_DATE;
```

**3. 批量收割（每批50场）**
```bash
# 第一批
python main.py --source fotmob \
  --mode single \
  --league "La Liga" \
  --season "24/25" \
  --limit 50

# 第二批...
```

---

## 📝 最终结论

### ❌ 不建议立即启动西甲收割

**原因**:
1. V26.7英超收割虽然显示"成功"，但数据未真正入库
2. 存在Critical级别的UPSERT问题
3. 必须先修复问题，验证数据真正入库

### ✅ 修复后的执行路径

**第1步**: 修复UPSERT问题（P0）
**第2步**: 重新收割10场英超验证（P1）
**第3步**: 验证数据入库成功（P1）
**第4步**: 收割10场西甲验证（P2）
**第5步**: 批量收割西甲（每批50场，共8批）

---

## 🔧 技术附录

### 检查点清单

- [ ] 确认数据库连接配置正确
- [ ] 确认UPSERT逻辑正确执行
- [ ] 确认事务正确提交
- [ ] 添加入库验证逻辑
- [ ] 重新收割10场验证
- [ ] 验证数据真正入库
- [ ] 启动西甲收割

### 建议的修复代码

```python
# src/api/collectors/fotmob_core.py
def harvest_match_with_league(self, match_id, league_id, season):
    """收割比赛数据并入库（带验证）"""

    # ... 现有收割逻辑 ...

    # UPSERT到数据库
    self._upsert_match(match_data)

    # ✅ 新增: 立即验证入库
    cursor.execute(
        "SELECT match_id FROM matches WHERE match_id = %s",
        (str(match_id),)
    )
    if not cursor.fetchone():
        raise Exception(f"UPSERT verification failed for match {match_id}")

    logger.info(f"✅ UPSERT verified: {match_id}")
    return True
```

---

**报告签署**: 高级数据质量审计员 (QA Specialist)
**日期**: 2026-01-07
**版本**: V26.7 EPL Data Quality Audit Report v1.0

---

⚠️ **Critical Warning**: 在修复UPSERT问题之前，不要启动任何新的收割任务。
