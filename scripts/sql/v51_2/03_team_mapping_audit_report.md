# V51.2 球队名称映射审计报告

**生成时间**: 2025-12-31 20:52:30
**总计映射数**: 116

## 1. 映射统计摘要

| 指标 | 数值 |
|------|------|
| FotMob 球队总数 | 133 |
| OddsPortal 球队总数 | 94 |
| 成功映射数 | 99 |
| 低置信度映射数 | 17 |
| 未匹配球队数 | 36 |
| **映射成功率** | **74.4%** |

## 2. 需要人工审核的映射

> 置信度低于 90% 的映射需要人工审核

| FotMob | OddsPortal | 置信度 | 联赛 |
|--------|------------|--------|------|
| Borussia Dortmund | B. Dortmund | 85.5% | Bundesliga |
| Manchester City | Man City | 85.5% | Premier League |
| Manchester United | Man United | 85.5% | Premier League |
| Norwich City | Man City | 85.5% | Premier League |
| Sheffield United | Man United | 85.5% | Premier League |
| West Bromwich Albion | West Ham | 85.5% | Premier League |
| Manchester City | Man City | 85.5% | 英超 |
| Manchester United | Man United | 85.5% | 英超 |
| Wolverhampton Wanderers | Wolves | 81.8% | Premier League |
| Wolverhampton Wanderers | Wolves | 81.8% | 英超 |
| Bayern München | Bayern Munich | 81.5% | Bundesliga |
| Atletico Madrid | Atl. Madrid | 76.9% | La Liga |
| Borussia Mönchengladbach | B. Monchengladbach | 76.2% | Bundesliga |
| Leganes | Lens | 72.7% | La Liga |
| Saint-Etienne | Rennes | 72.0% | Ligue 1 |
| Leeds United | Man United | 71.2% | Premier League |
| Leeds United | Man United | 71.2% | 英超 |

## 3. 未匹配球队

> 以下球队未能找到匹配 (置信度 < 70%)

| 球队名称 | 联赛 |
|----------|------|
| 1. FC Köln | Bundesliga |
| Arminia Bielefeld | Bundesliga |
| Darmstadt | Bundesliga |
| Greuther Fürth | Bundesliga |
| Hertha BSC | Bundesliga |
| Holstein Kiel | Bundesliga |
| Schalke 04 | Bundesliga |
| Almeria | La Liga |
| Athletic Club | La Liga |
| Cadiz | La Liga |
| Eibar | La Liga |
| Elche | La Liga |
| Espanyol | La Liga |
| Granada | La Liga |
| Levante | La Liga |
| SD Huesca | La Liga |
| AC Ajaccio | Ligue 1 |
| Bordeaux | Ligue 1 |
| Clermont Foot | Ligue 1 |
| Dijon | Ligue 1 |
| Nimes | Ligue 1 |
| Paris Saint-Germain | Ligue 1 |
| Troyes | Ligue 1 |
| Burnley | Premier League |
| Luton Town | Premier League |
| Watford | Premier League |
| Benevento | Serie A |
| Cremonese | Serie A |
| Crotone | Serie A |
| Frosinone | Serie A |
| Salernitana | Serie A |
| Sampdoria | Serie A |
| Sassuolo | Serie A |
| Spezia | Serie A |
| Burnley | 英超 |
| Sunderland | 英超 |

## 4. 审核操作指南

### 4.1 批准映射
```sql
-- 批准单个映射
UPDATE team_name_mapping
SET mapping_status = 'approved', needs_review = FALSE, reviewed_by = 'your_name'
WHERE id = <mapping_id>;

-- 批量批准高置信度映射 (>85%)
UPDATE team_name_mapping
SET mapping_status = 'approved', needs_review = FALSE, reviewed_by = 'your_name'
WHERE confidence_score >= 85 AND needs_review = TRUE;
```

### 4.2 修正映射
```sql
-- 修正错误的映射
UPDATE team_name_mapping
SET oddsportal_name = '正确名称',
    confidence_score = 100,
    mapping_status = 'approved',
    needs_review = FALSE,
    reviewed_by = 'your_name',
    notes = '人工修正'
WHERE id = <mapping_id>;
```

### 4.3 拒绝映射
```sql
-- 标记为无效映射
UPDATE team_name_mapping
SET mapping_status = 'rejected', needs_review = FALSE, reviewed_by = 'your_name'
WHERE id = <mapping_id>;
```

## 5. 验证查询

```sql
-- 检查映射完成度
SELECT
    COUNT(DISTINCT fotmob_name) as mapped_teams,
    (SELECT COUNT(DISTINCT home_team) FROM matches WHERE home_team IS NOT NULL
     UNION
     SELECT COUNT(DISTINCT away_team) FROM matches WHERE away_team IS NOT NULL) as total_teams
FROM team_name_mapping
WHERE mapping_status = 'approved';

-- 查找重复映射
SELECT oddsportal_name, COUNT(*) as count
FROM team_name_mapping
WHERE mapping_status = 'approved'
GROUP BY oddsportal_name
HAVING COUNT(*) > 1;
```

---
*报告结束*