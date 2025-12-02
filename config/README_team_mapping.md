# 队名映射使用指南

## 📋 概述

本目录包含FBref与FotMob队名映射文件，用于解决两个数据源的实体对齐问题。

## 📁 文件说明

### 1. `team_mapping.json` (主文件)
完整映射文件，包含：
- `high_confidence`: 高可信度映射 (相似度 ≥ 85%)
- `low_confidence`: 低可信度映射 (相似度 70-85%)
- `unmatched`: 未匹配队名
- `metadata`: 统计信息

### 2. `team_mapping_low_confidence.json`
低可信度映射，需要人工审核。

### 3. `team_mapping_unmatched.json`
未匹配队名列表，包括：
- FBref独有的队名
- FotMob独有的队名 (标记为 `__FOTMOB_ONLY__`)

### 4. `team_mapping_updates.sql`
SQL更新语句，用于统一数据库中的team_id。

## 🔧 使用方法

### 在Python代码中使用映射

```python
import json

# 加载映射文件
with open('config/team_mapping.json', 'r', encoding='utf-8') as f:
    mapping_data = json.load(f)

# 获取高可信度映射
high_conf = mapping_data['high_confidence']
low_conf = mapping_data['low_confidence']

# 映射FBref队名到FotMob
def get_fotmob_name(fbref_name):
    if fbref_name in high_conf:
        return high_conf[fbref_name]
    elif fbref_name in low_conf:
        print(f"⚠️  低可信度映射: {fbref_name} → {low_conf[fbref_name]}")
        return low_conf[fbref_name]
    else:
        print(f"❌ 未找到映射: {fbref_name}")
        return None

# 示例
fbref_team = "Manchester City"
fotmob_team = get_fotmob_name(fbref_team)
print(f"{fbref_team} → {fotmob_team}")
```

### 在SQL中使用映射

```sql
-- 示例：JOIN两个数据源
SELECT
    fbref_matches.*,
    fotmob_matches.*
FROM fbref_matches
JOIN fotmob_matches ON (
    fotmob_matches.home_team_name = (
        SELECT team_mapping.fotmob_name
        FROM team_mapping
        WHERE team_mapping.fbref_name = fbref_matches.home_team_name
    )
    OR fotmob_matches.home_team_name = fbref_matches.home_team_name
);
```

### 应用SQL更新

```bash
# ⚠️  执行前请备份数据库！
psql -d football_prediction -f config/team_mapping_updates.sql
```

## 📊 映射统计

- **FBref队名总数**: 96
- **FotMob队名总数**: 1318
- **高可信度映射**: 56个 (58.3%)
- **低可信度映射**: 17个 (17.7%)
- **未匹配**: 23个FBref + 1245个FotMob (24.0%)

## ⚠️ 注意事项

### 1. 低可信度映射需人工审核
以下映射需要人工确认：
- `Atalanta` → `Atalanta U23` (青年队)
- `Bayern Munich` → `Bayern München` (同队，不同表示)
- `Manchester Utd` → `Manchester United U18` (成人队 vs 青年队)
- `Real Madrid` → `Real Madrid Castilla` (一队 vs 二队)

### 2. 未匹配队名原因
- **FBref独有**: FBref数据集中可能没有FotMob的比赛
- **FotMob独有**: 包含全球低级别联赛、小联赛、女子联赛
- **命名差异**: 部分队名差异较大，需要手动映射

### 3. 建议工作流
1. 使用高可信度映射（自动应用）
2. 审核低可信度映射（手动确认）
3. 补充常见队名的手动映射
4. 定期更新映射（随着新数据源的增加）

## 🔄 更新映射

当有新数据时，重新运行生成器：

```bash
python scripts/generate_team_mapping.py
```

## 📞 支持

如有问题，请联系数据清洗团队。

---

**生成时间**: 2025-12-02 01:42
**生成工具**: scripts/generate_team_mapping.py
