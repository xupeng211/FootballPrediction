# TITAN 联赛扩张 SOP (Standard Operating Procedure)

> **版本**: V4.46.6 | **最后更新**: 2026-03-09
>
> 本文档指导如何将一个新联赛（如英超、法甲）接入 TITAN 收割系统。

---

## 📋 快速检查清单

```
□ 1. 确认联赛 ID 和配置
□ 2. 修改 leagues.json
□ 3. 运行 L1 扫描 (seed)
□ 4. 测试 L2 收割 (harvest)
□ 5. 执行 L3 熔炼 (smelt)
□ 6. 验证数据完整性
```

---

## 1️⃣ 确认联赛信息

### 1.1 获取 FotMob League ID

访问 FotMob 网站，找到目标联赛的 URL：

```
https://www.fotmob.com/leagues/47/overview/premier-league
                              ↑
                          League ID
```

### 1.2 常用联赛 ID 对照表

| 联赛 | FotMob ID | OddsPortal 名称 |
|------|-----------|-----------------|
| Premier League | 47 | england/premier-league |
| La Liga | 87 | spain/laliga |
| Bundesliga | 54 | germany/bundesliga |
| Serie A | 55 | italy/serie-a |
| Ligue 1 | 53 | france/ligue-1 |
| Champions League | 42 | europe/champions-league |

---

## 2️⃣ 修改配置文件

### 2.1 编辑 `config/leagues.json`

```json
{
  "version": "V4.46.6",
  "active_leagues": [
    {
      "id": 47,                    // ← FotMob League ID
      "name": "Premier League",    // ← 显示名称
      "country": "England",        // ← 国家
      "enabled": true              // ← 设为 true 启用
    }
  ],
  "inactive_leagues": [
    // 其他联赛设为 enabled: false
  ],
  "active_seasons": ["2025/2026"]
}
```

### 2.2 验证配置

```bash
# 进入开发容器
docker-compose -f docker-compose.dev.yml exec dev bash

# 检查配置语法
node -e "console.log(JSON.parse(require('fs').readFileSync('config/leagues.json')))"
```

---

## 3️⃣ 执行 L1 扫描 (赛程发现)

### 3.1 扫描新联赛赛程

```bash
# 方式 A: 使用 npm script (推荐)
npm run seed

# 方式 B: 直接调用脚本
node scripts/ops/seed_fixtures.js --league-id 47

# 方式 C: 扫描所有启用联赛
npm run seed:all
```

### 3.2 验证扫描结果

```bash
# 检查数据库中的新联赛记录
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
SELECT COUNT(*) as discovered 
FROM matches 
WHERE league_name = 'Premier League';
"
```

---

## 4️⃣ 测试 L2 收割

### 4.1 小规模测试 (推荐先执行)

```bash
# 测试收割 5 场比赛
node scripts/ops/run_production.js --limit 5

# 检查成功率
npm run status
```

### 4.2 全量收割

```bash
# 方式 A: 超频蜂群收割 (推荐，15 并发)
npm run harvest

# 方式 B: 生产收割器 (稳定，单 Worker)
npm run harvest:production

# 方式 C: 自定义并发
node scripts/ops/hyper_swarm.js
```

### 4.3 监控收割进度

```bash
# 启动监控栈
npm run monitor:up

# 访问 Grafana
# http://localhost:3001
# 用户名: admin
# 密码: titan2024
```

---

## 5️⃣ 执行 L3 熔炼

### 5.1 生成特征向量

```bash
# 熔炼所有 L2 数据
npm run smelt

# 或指定联赛
python scripts/ops/smelt_l3.py --league-id 47
```

### 5.2 验证特征生成

```bash
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
SELECT 
    'L1' as layer, COUNT(*) as count FROM matches WHERE league_name = 'Premier League'
UNION ALL
SELECT 
    'L2', COUNT(*) FROM raw_match_data r
    JOIN matches m ON r.match_id = m.match_id
    WHERE m.league_name = 'Premier League'
UNION ALL
SELECT 
    'L3', COUNT(*) FROM l3_features l
    JOIN matches m ON l.match_id = m.match_id
    WHERE m.league_name = 'Premier League';
"
```

---

## 6️⃣ 验证数据完整性

### 6.1 运行完整性检查

```bash
# 运行完整性守护脚本
npm run status

# 或直接调用
python scripts/maintenance/integrity_guard.py
```

### 6.2 预期输出

```
╔═══════════════════════════════════════════════════════════════╗
║  🛡️ TITAN 数据完整性守护报告                                  ║
╚═══════════════════════════════════════════════════════════════╝

  L1 (matches):        XXXX 场
  L2 (raw_match_data): XXXX 场
  L3 (l3_features):    XXXX 场

  ✅ 数据完全对齐: L1 = L2 = L3
```

---

## 🔧 故障排查

### 问题 1: L1 扫描返回 0 场比赛

**可能原因**:
- 联赛 ID 错误
- 赛季配置不正确
- 网络连接问题

**解决方案**:
```bash
# 手动测试 API 连接
curl "https://www.fotmob.com/api/leagues?id=47&season=2025/2026"
```

### 问题 2: L2 收割成功率低

**可能原因**:
- 代理池问题
- Turnstile 拦截
- 队名匹配失败

**解决方案**:
```bash
# 检查代理健康
curl -x http://172.25.16.1:7890 https://httpbin.org/ip

# 检查队名匹配
python -c "
from src.utils.cpp_bridge_radar import BridgeRadarEngine
bridge = BridgeRadarEngine()
print(bridge.dynamic_bridge('Arsenal', 'Chelsea', 'Premier League'))
"
```

### 问题 3: L3 熔炼失败

**可能原因**:
- L2 数据格式异常
- 特征计算依赖缺失

**解决方案**:
```bash
# 检查 L2 数据格式
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
SELECT match_id, jsonb_pretty(raw_data) 
FROM raw_match_data 
WHERE match_id LIKE '47_%' 
LIMIT 1;
"
```

---

## 📚 字段映射参考

当新联赛的数据字段与现有 Strategy 不一致时，需要调整映射：

### 文件位置

```
src/parsers/
├── FotMobParser.js        # FotMob 数据解析
├── NextDataParser.js      # __NEXT_DATA__ 解析
└── OddsPortalParser.js    # OddsPortal 赔率解析
```

### 添加新字段映射

```javascript
// src/parsers/FotMobParser.js

// 1. 在 FIELD_MAPPING 对象中添加新映射
const FIELD_MAPPING = {
    'homeTeam.name': 'home_team',
    'awayTeam.name': 'away_team',
    // 添加新字段
    'newField.path': 'normalized_field_name'
};

// 2. 在 extractMatchData 方法中处理
extractMatchData(rawData) {
    return {
        ...existingFields,
        normalized_field_name: this._safeGet(rawData, 'newField.path')
    };
}
```

---

## ✅ 完成确认

当所有步骤完成后，确认以下指标：

| 指标 | 预期值 | 状态 |
|------|--------|------|
| L1 记录数 | > 0 | □ |
| L2 收割率 | > 95% | □ |
| L3 熔炼率 | 100% | □ |
| 数据对齐 | L1=L2=L3 | □ |

---

**文档维护者**: TITAN Engineering Team
**反馈渠道**: GitHub Issues
