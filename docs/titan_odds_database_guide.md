# Titan007 赔率数据库集成指南

## 概述

本文档介绍如何使用 Titan007 赔率数据采集和存储系统，包括：

1. **欧赔数据** (1X2 odds) - 主胜、平局、客胜赔率
2. **亚盘数据** (Asian Handicap) - 让球盘赔率
3. **大小球数据** (Over/Under) - 进球数盘口赔率

## 核心组件

### 1. 数据模型 (`src/database/models/titan.py`)

- **TitanBookmaker**: 博彩公司信息
- **TitanEuroOdds**: 欧赔数据模型
- **TitanAsianOdds**: 亚盘数据模型
- **TitanOverUnderOdds**: 大小球数据模型

### 2. 数据仓库 (`src/database/repositories/`)

- **TitanOddsRepository**: 核心数据操作类，提供 upsert 功能
- **RealTitanOddsRepository**: 简化的调用接口，替换 MockRepository

### 3. 数据采集器 (`src/collectors/titan/`)

- **TitanEuroCollector**: 欧赔数据采集器
- **TitanAsianCollector**: 亚盘数据采集器
- **TitanOverUnderCollector**: 大小球数据采集器

## 使用方法

### 1. 开发环境 (Mock 模式)

```bash
# 使用 Mock 数据库进行开发和测试
python scripts/run_titan_pipeline.py
```

输出示例：
```
🎭 使用模拟数据库 (Mock)
💾 [MockDB] 欧赔数据已入库: 公司=William Hill, 主胜=1.80
💾 [MockDB] 亚盘数据已入库: 公司=Bet365, 盘口=-0.5
💾 [MockDB] 大小球数据已入库: 公司=Pinnacle, 盘口=2.5
```

### 2. 生产环境 (真实数据库)

```bash
# 使用真实 PostgreSQL 数据库
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/football_prediction"

python scripts/run_titan_pipeline.py --use-real-db
```

### 3. 自定义数据库连接

```bash
python scripts/run_titan_pipeline.py --use-real-db --db-url "postgresql+asyncpg://localhost:5432/titan_odds"
```

## 数据库功能验证

运行完整性测试：

```bash
# Mock 模式测试
python test_titan_odds_db.py

# 真实数据库测试
python test_titan_odds_db.py --use-real-db
```

## 核心特性

### 1. Upsert 逻辑

系统实现了智能的更新或插入逻辑：

- **存在记录**: 更新现有赔率数据
- **不存在记录**: 创建新的赔率记录
- **唯一约束**: 基于 `match_id` + `bookmaker_id` 组合

### 2. 博彩公司管理

自动管理博彩公司信息：

```python
# 自动创建或更新博彩公司
bookmaker = await repository.upsert_bookmaker(
    company_id=3,
    company_name="William Hill",
    display_name="William Hill",
    country="UK"
)
```

### 3. 批量操作

支持批量数据操作以提高性能：

```python
# 批量存储欧赔数据
euro_dtos = [dto1, dto2, dto3, ...]
results = await repository.batch_upsert_euro_odds(euro_dtos)
```

## 数据库 Schema

### 欧赔表 (titan_euro_odds)

```sql
CREATE TABLE titan_euro_odds (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL,
    bookmaker_id INTEGER NOT NULL REFERENCES titan_bookmakers(id),
    home_odds NUMERIC(10,4),
    draw_odds NUMERIC(10,4),
    away_odds NUMERIC(10,4),
    home_open NUMERIC(10,4),
    draw_open NUMERIC(10,4),
    away_open NUMERIC(10,4),
    update_time TIMESTAMP NOT NULL,
    is_live BOOLEAN DEFAULT FALSE,
    confidence_score NUMERIC(5,3),
    raw_data TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(match_id, bookmaker_id)
);
```

### 亚盘表 (titan_asian_odds)

```sql
CREATE TABLE titan_asian_odds (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL,
    bookmaker_id INTEGER NOT NULL REFERENCES titan_bookmakers(id),
    upper_odds NUMERIC(10,4),
    lower_odds NUMERIC(10,4),
    handicap VARCHAR(20),
    upper_open NUMERIC(10,4),
    lower_open NUMERIC(10,4),
    handicap_open VARCHAR(20),
    update_time TIMESTAMP NOT NULL,
    is_live BOOLEAN DEFAULT FALSE,
    confidence_score NUMERIC(5,3),
    raw_data TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(match_id, bookmaker_id)
);
```

### 大小球表 (titan_overunder_odds)

```sql
CREATE TABLE titan_overunder_odds (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL,
    bookmaker_id INTEGER NOT NULL REFERENCES titan_bookmakers(id),
    over_odds NUMERIC(10,4),
    under_odds NUMERIC(10,4),
    overunder VARCHAR(20),
    over_open NUMERIC(10,4),
    under_open NUMERIC(10,4),
    overunder_open VARCHAR(20),
    update_time TIMESTAMP NOT NULL,
    is_live BOOLEAN DEFAULT FALSE,
    confidence_score NUMERIC(5,3),
    raw_data TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(match_id, bookmaker_id)
);
```

## API 使用示例

### 1. 存储单条赔率数据

```python
from src.database.repositories.titan_odds_factory import RealTitanOddsRepository
from src.schemas.titan import EuroOddsRecord

# 创建仓库
repo = RealTitanOddsRepository()

# 创建 DTO
dto = EuroOddsRecord.model_validate({
    "matchid": "2971465",
    "companyid": 3,
    "companyname": "William Hill",
    "homeodds": 1.85,
    "drawodds": 3.60,
    "awayodds": 4.20,
    "utime": "2024-01-01T16:00:00Z"
})

# 存储
success = await repo.save_euro_odds(dto)
```

### 2. 查询赔率数据

```python
from src.database.repositories.odds_repository import TitanOddsRepository

repo = TitanOddsRepository()

# 获取欧赔数据
euro_odds = await repo.get_euro_odds("2971465", 3)  # match_id, company_id

# 获取亚盘数据
asian_odds = await repo.get_asian_odds("2971465", 8)

# 获取大小球数据
overunder_odds = await repo.get_overunder_odds("2971465", 17)
```

### 3. 统计和监控

```python
# 统计比赛赔率数量
stats = await repo.count_odds_by_match("2971465")
print(f"欧赔: {stats['euro']}, 亚盘: {stats['asian']}, 大小球: {stats['overunder']}")

# 获取最近的赔率更新
recent_odds = await repo.get_recent_odds(hours=24)
```

## 错误处理

系统包含完善的错误处理机制：

1. **网络错误**: 自动重试机制
2. **数据验证**: Pydantic 模型验证
3. **数据库错误**: 事务回滚
4. **字段缺失**: 安全的解析方法

## 性能优化

1. **连接池**: 使用 SQLAlchemy 连接池
2. **批量操作**: 支持批量插入和更新
3. **索引优化**: 在关键字段上建立索引
4. **异步操作**: 全链路异步处理

## 部署注意事项

1. **环境变量**: 设置 `DATABASE_URL`
2. **数据库权限**: 确保用户有 CREATE、INSERT、UPDATE 权限
3. **连接池配置**: 根据并发需求调整连接池大小
4. **监控**: 设置数据库连接监控

## 故障排除

### 常见问题

1. **连接失败**: 检查数据库 URL 和网络连接
2. **权限错误**: 确保数据库用户有足够权限
3. **表不存在**: 运行数据库迁移脚本
4. **内存不足**: 调整连接池配置

### 日志调试

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 更新日志

- **v1.0.0**: 初始版本，支持基础赔率存储
- **v1.1.0**: 添加 upsert 逻辑和批量操作
- **v1.2.0**: 集成 Titan007 采集器
- **v1.3.0**: 添加数据验证和错误处理