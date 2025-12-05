# Football Prediction System - Core Architecture

## 📖 概述

本文档是 **Football Prediction System** 的核心架构文档，作为技术传承和AI辅助开发的标准参考。记录系统设计原则、关键决策和技术实现细节。

## 🏗️ 系统架构

### 核心原则
- **单一数据源**: FotMob 作为主要数据源
- **分层采集**: L1 (赛程) → L2 (详情) → L3 (特征) 的数据流水线
- **HTTP优先**: 禁止使用 Playwright，必须使用 HTTP API
- **外键安全**: 通过 `ensure_team_exists` 解决球队外键约束
- **异步架构**: 全链路异步，支持高并发

### 技术栈
- **后端**: FastAPI + PostgreSQL 15 + Redis 7.0+
- **ORM**: SQLAlchemy 2.0+ (async)
- **HTTP客户端**: aiohttp + asyncio
- **机器学习**: XGBoost + TensorFlow + MLflow
- **容器化**: Docker + Docker Compose

## 🌐 数据源架构

### FotMob API 规范

#### 端点定义
```python
# L1 - 赛程采集
L1_ENDPOINT = "https://www.fotmob.com/api/matches?date={YYYYMMDD}&timezone=Asia/Shanghai&ccode3=CHN"

# L2 - 详情采集
L2_ENDPOINT = "https://www.fotmob.com/api/matchDetails?matchId={match_id}"
```

#### API 鉴权 (关键)
所有 FotMob API 请求必须包含以下 Header：

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.fotmob.com/",
    "Origin": "https://www.fotmob.com",
    # 🎯 关键鉴权头
    "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0=",
    "x-foo": "production:208a8f87c2cc13343f1dd8671471cf5a039dced3",
}
```

**⚠️ 严格禁止**: 任何形式的 Playwright 或浏览器自动化
**✅ 必须使用**: `src/collectors/enhanced_fotmob_collector.py`

## 🔄 数据流水线

### L1 - 赛程采集 (`src/jobs/run_l1_fixtures.py`)

**职责**: 创建基础数据记录
- 创建 `teams` 表记录 (通过 `_get_or_create_team`)
- 创建 `matches` 表基础记录
- 设置 `data_completeness = 'partial'`

**关键方法**:
```python
async def ensure_team_exists(self, session, team_name: str) -> int:
    """
    解决外键约束的核心方法
    1. 检查球队是否存在
    2. 不存在则创建新记录
    3. 返回球队ID
    """
```

### L2 - 详情采集 (`src/jobs/run_l2_details.py`)

**职责**: 更新深度详情数据
- 更新 `matches` 表的详情字段
- 采集 xG、赔率、射门数据
- 设置 `data_completeness = 'complete'`

**数据字段**:
```sql
-- L2 更新的字段
UPDATE matches SET
    home_xg = :home_xg,           -- 主队期望进球数
    away_xg = :away_xg,           -- 客队期望进球数
    referee = :referee,           -- 裁判
    weather_data = :weather_data, -- 天气信息 (JSON)
    shotmap_data = :shotmap_data, -- 射门数据 (JSON)
    odds_data = :odds_data,       -- 赔率数据 (JSON)
    data_completeness = 'complete'
WHERE fotmob_id = :fotmob_id;
```

## 🗄️ 数据库设计

### 核心表结构

#### teams 表
```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### matches 表
```sql
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER REFERENCES teams(id),  -- 外键约束
    away_team_id INTEGER REFERENCES teams(id),  -- 外键约束
    home_score INTEGER,
    away_score INTEGER,
    status VARCHAR(20),
    match_date TIMESTAMP,
    venue VARCHAR(255),
    league_id INTEGER,
    season VARCHAR(20),
    fotmob_id VARCHAR(50),           -- FotMob比赛ID
    data_source VARCHAR(50),         -- 数据源标识
    data_completeness VARCHAR(20),  -- 数据完整性
    home_xg FLOAT,                  -- 主队xG (L2)
    away_xg FLOAT,                  -- 客队xG (L2)
    referee VARCHAR(255),           -- 裁判 (L2)
    weather_data JSONB,             -- 天气数据 (L2)
    shotmap_data JSONB,             -- 射门数据 (L2)
    odds_data JSONB,                -- 赔率数据 (L2)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 🚀 生产运行

### 启动命令

#### 开发环境
```bash
# 启动开发环境
make dev

# L1 赛程采集
python src/jobs/run_l1_fixtures.py

# L2 详情采集
python src/jobs/run_l2_details.py
```

#### 生产环境
```bash
# 后台运行 L1
nohup python src/jobs/run_l1_fixtures.py > logs/l1_fixtures.log 2>&1 &

# 后台运行 L2
nohup python src/jobs/run_l2_details.py > logs/l2_details.log 2>&1 &
```

### 监控命令
```bash
# 检查数据状态
SELECT
    COUNT(*) as total_matches,
    COUNT(*) FILTER (WHERE data_source = 'fotmob_v2') as l1_count,
    COUNT(*) FILTER (WHERE data_completeness = 'complete') as l2_count
FROM matches;

# 检查进程状态
ps aux | grep -E "(run_l1|run_l2)" | grep -v grep
```

## 🛡️ 安全与性能

### 反爬策略
- **请求头伪装**: 完整的浏览器请求头
- **智能延迟**: 2-5秒随机延迟
- **认证签名**: x-mas 和 x-foo 头部
- **错误处理**: 完善的异常处理和重试机制

### 性能优化
- **异步数据库**: 使用 asyncpg 连接池
- **批量处理**: 批量插入和更新
- **连接复用**: aiohttp 会话复用
- **缓存机制**: Redis 缓存热点数据

## 🔧 开发规范

### 代码标准
- **异步优先**: 所有 I/O 操作使用 async/await
- **类型注解**: 完整的 Python 类型提示
- **错误处理**: 详细的异常处理和日志记录
- **测试覆盖**: 核心业务逻辑 100% 测试覆盖

### 导入规范
```python
# ✅ 正确的导入路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector
from src.database.async_manager import get_db_session
```

### 日志规范
```python
# ✅ 标准化日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/job_name.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
```

## 📋 关键决策记录

### 为什么禁止 Playwright？
1. **性能问题**: 浏览器启动开销大 (10-100x)
2. **稳定性差**: 页面加载依赖，易受网络影响
3. **维护复杂**: 需要处理页面结构变化
4. **资源消耗**: 内存和 CPU 占用高

### 为什么需要 `ensure_team_exists`？
1. **外键约束**: matches 表依赖 teams 表
2. **数据完整性**: 确保球队记录先于比赛记录存在
3. **避免错误**: 防止外键约束异常
4. **自动创建**: 未知球队自动创建，保证数据采集连续性

### API 鉴权的重要性
1. **访问控制**: 无鉴权返回 401 错误
2. **签名验证**: x-mas 是加密签名
3. **版本控制**: x-foo 标识客户端版本
4. **反爬检测**: 基础请求头不足以绕过检测

## 🔍 故障排查

### 常见问题

#### 401 Unauthorized
```bash
# 检查鉴权头
curl -H "x-mas: <signature>" -H "x-foo: <version>" https://www.fotmob.com/api/matches?date=20241205
```

#### 外键约束错误
```sql
-- 检查缺失的球队
SELECT DISTINCT home_team_id FROM matches
WHERE home_team_id NOT IN (SELECT id FROM teams);
```

#### 数据采集失败
```bash
# 检查日志
tail -f logs/l1_fixtures.log
tail -f logs/l2_details.log

# 检查进程
ps aux | grep python
```

## 📚 参考资源

- **项目配置**: `CLAUDE.md` - 开发指南
- **API文档**: `src/collectors/enhanced_fotmob_collector.py`
- **数据库**: `src/database/async_manager.py`
- **测试**: `tests/unit/collectors/`

---

**维护说明**: 本文档是系统的技术圣经，任何架构变更都必须同步更新本文档。

**版本**: v2.0.0
**最后更新**: 2024-12-05
**负责人**: Tech Lead & Documentation Expert