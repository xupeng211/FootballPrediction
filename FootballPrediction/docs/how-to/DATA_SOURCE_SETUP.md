# 数据源配置指南

> 📅 **更新时间**: 2025-10-29
> 🎯 **目标**: 配置Football-Data.org API实现真实数据接入

---

## 📋 概述

本指南将帮助您配置足球预测系统的数据源，特别是Football-Data.org API的集成配置。

## 🚀 快速开始

### 1. 获取API密钥

1. 访问 [Football-Data.org](https://www.football-data.org/)
2. 注册账户并登录
3. 在API密钥页面获取您的API令牌
4. 复制API密钥（格式类似：`b1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`）

### 2. 配置环境变量

```bash
# 在项目根目录创建或编辑 .env 文件
echo "FOOTBALL_DATA_API_KEY=your_actual_api_key_here" >> .env

# 或者导出环境变量
export FOOTBALL_DATA_API_KEY=your_actual_api_key_here
```

### 3. 测试连接

```bash
# 运行数据源测试脚本
python3 scripts/test_data_sources.py
```

## 🔧 详细配置

### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# Football Data API
FOOTBALL_DATA_API_KEY=your_actual_api_key_here

# 可选：其他API配置
RAPIDAPI_KEY=your_rapidapi_key_here
WEATHER_API_KEY=your_weather_api_key_here
```

### 支持的联赛

系统目前支持以下主要联赛：

| 联赛ID | 英文名称 | 中文名称 | 支持状态 |
|--------|-----------|----------|----------|
| 39 | Premier League | 英超 | ✅ |
| 140 | La Liga | 西甲 | ✅ |
| 78 | Bundesliga | 德甲 | ✅ |
| 135 | Serie A | 意甲 | ✅ |
| 61 | Ligue 1 | 法甲 | ✅ |
| 2 | Champions League | 欧冠 | ✅ |
| 3 | Europa League | 欧联 | ✅ |
| 418 | FA Cup | 足总杯 | ✅ |
| 541 | DFB-Pokal | 德国杯 | ✅ |
| 525 | Copa del Rey | 国王杯 | ✅ |
| 588 | Coppa Italia | 意大利杯 | ✅ |
| 603 | Coupe de France | 法国杯 | ✅ |

## 📊 API功能

### 获取比赛数据

```python
from src.collectors.data_sources import EnhancedFootballDataOrgAdapter

adapter = EnhancedFootballDataOrgAdapter(api_key="your_api_key")

# 获取未来7天的比赛
matches = await adapter.get_upcoming_matches(days=7)

# 获取特定联赛的比赛
premier_league_matches = await adapter.get_matches(league_id=39)

# 获取特定日期的比赛
today_matches = await adapter.get_matches_by_date(datetime.now())
```

### 获取球队数据

```python
# 获取英超球队
teams = await adapter.get_teams(league_id=39)

# 获取联赛积分榜
standings = await adapter.get_standings(league_id=39)
```

### 获取联赛信息

```python
# 获取所有支持的联赛
competitions = await adapter.get_competitions()
```

## 🛡️ 安全配置

### API密钥安全

1. **不要在代码中硬编码API密钥**
2. **使用环境变量存储密钥**
3. **定期轮换API密钥**
4. **限制API密钥权限**

### 速率限制

Football-Data.org API的速率限制：
- **免费计划**: 10 requests/minute
- **付费计划**: 更多请求/分钟

系统已内置速率限制保护，自动处理429错误。

### 错误处理

系统包含完整的错误处理机制：
- 自动重试机制（指数退避）
- 优雅降级（切换到模拟数据）
- 详细的错误日志记录

## 🧪 测试和验证

### 运行完整测试

```bash
# 运行数据源测试脚本
python3 scripts/test_data_sources.py
```

测试脚本会验证：
- ✅ API密钥配置
- ✅ API连接状态
- ✅ 联赛列表获取
- ✅ 比赛数据获取
- ✅ 特定联赛数据
- ✅ 速率限制处理
- ✅ 数据质量检查
- ✅ 数据源管理器

### 验证配置

```python
from src.collectors.data_sources import DataSourceManager

# 创建数据源管理器
manager = DataSourceManager()

# 验证所有适配器
results = await manager.validate_adapters()
print(results)

# 获取主要适配器
adapter = manager.get_primary_adapter()
print(f"主要适配器: {type(adapter).__name__}")
```

## 🔄 数据收集流程

### 自动数据收集

```python
from src.collectors.data_sources import data_source_manager

# 收集未来30天的所有比赛
matches = await data_source_manager.collect_all_matches(days_ahead=30)
print(f"收集到 {len(matches)} 场比赛")
```

### 定时任务配置

建议配置定时任务定期收集数据：

```bash
# 每小时收集一次比赛数据
0 * * * * python3 scripts/collect_data.py

# 每天凌晨2点更新球队数据
0 2 * * * python3 scripts/update_teams.py
```

## 📈 监控和日志

### 日志查看

```bash
# 查看数据源相关日志
grep "data_source" logs/app.log

# 查看API请求日志
grep "API Request" logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log | grep "data_source"
```

### 性能监控

系统会记录以下指标：
- API请求响应时间
- 数据收集成功率
- 数据质量评分
- 速率限制触发次数

## 🚨 故障排除

### 常见问题

#### 1. API密钥无效

**症状**: `API错误 401: Unauthorized`

**解决方案**:
- 检查API密钥是否正确
- 确认API密钥是否激活
- 验证API密钥是否有足够权限

#### 2. 速率限制

**症状**: `触发API速率限制，等待 X 秒`

**解决方案**:
- 减少请求频率
- 考虑升级API计划
- 使用缓存减少重复请求

#### 3. 网络连接问题

**症状**: `请求失败，X秒后重试`

**解决方案**:
- 检查网络连接
- 验证防火墙设置
- 考虑使用代理

#### 4. 数据解析错误

**症状**: `解析比赛数据失败`

**解决方案**:
- 检查API返回数据格式
- 验证数据结构是否匹配
- 查看详细错误日志

### 调试模式

启用详细日志记录：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 高级配置

### 自定义适配器

```python
from src.collectors.data_sources import DataSourceAdapter, MatchData

class CustomAdapter(DataSourceAdapter):
    async def get_matches(self, **kwargs):
        # 自定义数据获取逻辑
        pass
```

### 数据转换

```python
# 自定义数据转换逻辑
def transform_match_data(raw_data):
    # 数据转换逻辑
    return transformed_data
```

### 缓存配置

```python
from src.cache.redis_manager import get_redis_manager

# 使用缓存减少API调用
cache = get_redis_manager()
cached_data = await cache.get("matches_data")
```

## 🔗 相关文档

- [API使用说明](../reference/API_REFERENCE.md)
- [系统架构](../architecture/architecture.md)
- [测试指南](../testing/TEST_IMPROVEMENT_GUIDE.md)

## 📞 获取帮助

如果遇到配置问题：

1. 查看详细错误日志
2. 运行测试脚本诊断
3. 检查API密钥状态
4. 参考[故障排除指南](../project/ISSUES.md)

---

**文档维护**: 随项目进展实时更新
**版本**: v1.0
**状态**: ✅ 已完成
