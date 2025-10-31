# 🔗 集成外部足球数据API (Football-Data.org或API-Football)

## 问题描述
当前系统使用模拟数据，需要集成真实的足球数据API以获取实时比赛信息、球队统计、球员数据等。

## 当前状态
- ✅ 本地Docker试运营环境已成功部署
- ✅ PostgreSQL数据库集成完成 (端口5433)
- ✅ Redis缓存系统运行正常 (端口6380)
- ✅ 基础的预测CRUD功能已实现
- ❌ 缺少真实足球数据源

## 验收标准
- [ ] 成功集成至少一个外部足球数据API
- [ ] 实现数据自动同步机制 (每日更新)
- [ ] 添加API错误处理和重试机制
- [ ] 实现数据缓存策略减少API调用
- [ ] 通过集成测试验证数据获取功能

## 技术要求
- **API选择**: Football-Data.org 或 API-Football
- **数据类型**: 比赛信息、球队统计、球员数据、联赛积分榜
- **更新频率**: 每日自动同步，支持手动触发
- **错误处理**: 网络超时、API限流、数据格式异常
- **缓存策略**: Redis缓存，24小时过期，支持强制刷新

## 实现步骤

### 第一阶段：API研究和选择 (1-2天)
1. 研究Football-Data.org和API-Football的API文档
2. 比较API覆盖范围、限制、价格
3. 申请API密钥并进行测试
4. 选择最适合的API提供商

### 第二阶段：数据采集器实现 (3-4天)
1. 在`src/collectors/`目录下创建足球数据采集器
2. 实现以下模块：
   - `match_collector.py`: 比赛数据采集
   - `team_collector.py`: 球队数据采集
   - `player_collector.py`: 球员数据采集
   - `league_collector.py`: 联赛数据采集
3. 实现API限流和重试机制
4. 添加数据验证和清洗逻辑

### 第三阶段：数据存储和缓存 (2-3天)
1. 设计数据库表结构存储外部数据
2. 实现Redis缓存策略
3. 创建数据同步任务
4. 添加数据更新日志

### 第四阶段：集成测试 (1-2天)
1. 编写集成测试用例
2. 验证数据同步功能
3. 测试错误处理和恢复机制
4. 性能测试和优化

## 文件结构计划
```
src/
├── collectors/
│   ├── __init__.py
│   ├── base_collector.py          # 基础采集器类
│   ├── football_data_collector.py # Football-Data.org采集器
│   ├── api_football_collector.py  # API-Football采集器
│   └── match_collector.py         # 比赛数据采集
├── models/
│   ├── external/
│   │   ├── __init__.py
│   │   ├── match.py              # 外部比赛数据模型
│   │   ├── team.py               # 外部球队数据模型
│   │   └── player.py             # 外部球员数据模型
├── services/
│   ├── data_sync_service.py      # 数据同步服务
│   └── cache_service.py          # 缓存服务
└── tasks/
    ├── __init__.py
    └── data_sync_tasks.py        # 定时同步任务
```

## API密钥管理
1. 创建环境变量配置：
   ```bash
   FOOTBALL_DATA_API_KEY=your_api_key_here
   API_FOOTBALL_API_KEY=your_api_key_here
   ```
2. 实现API密钥轮换机制
3. 添加API使用量监控

## 数据库设计
```sql
-- 外部比赛数据表
CREATE TABLE external_matches (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE NOT NULL,
    home_team_id INTEGER,
    away_team_id INTEGER,
    league_id INTEGER,
    match_date TIMESTAMP,
    status VARCHAR(20),
    home_score INTEGER,
    away_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 外部球队数据表
CREATE TABLE external_teams (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    country VARCHAR(50),
    founded INTEGER,
    logo_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 缓存策略
```python
# Redis缓存键设计
CACHE_KEYS = {
    'match_list': 'matches:list:{league_id}:{season}',
    'team_info': 'team:info:{team_id}',
    'player_stats': 'player:stats:{player_id}',
    'league_table': 'league:table:{league_id}'
}

# 缓存过期时间
CACHE_TTL = {
    'match_list': 3600,      # 1小时
    'team_info': 86400,      # 24小时
    'player_stats': 21600,   # 6小时
    'league_table': 1800     # 30分钟
}
```

## 测试计划
1. **单元测试**: 测试数据采集器和模型
2. **集成测试**: 测试API集成和数据同步
3. **性能测试**: 测试API响应时间和缓存效果
4. **错误测试**: 测试网络异常和API限流处理

## 风险和缓解措施
1. **API限流**: 实现智能重试和备用API
2. **数据质量**: 添加数据验证和清洗逻辑
3. **服务依赖**: 实现降级和缓存机制
4. **成本控制**: 监控API调用量和费用

## 完成时间预估
- **总时间**: 7-11天
- **关键路径**: API选择 → 数据采集器实现 → 数据库集成

## 后续集成
完成后可以接入：
- Issue #2: 机器学习预测模型
- Issue #13: API文档完善
- Issue #8: 系统监控和告警

---

**优先级**: High
**标签**: feature, api-integration, data-source, high-priority
**负责人**: 待分配
**创建时间**: 2025-10-31
**预计完成**: 2025-11-11