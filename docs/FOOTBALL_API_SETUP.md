# Football-Data.org API 集成指南

本文档介绍如何配置和使用Football-Data.org API适配器。

## 📋 前提条件

1. **获取API Key**: 访问 [Football-Data.org](https://www.football-data.org/) 注册账户并获取API Key
2. **Python环境**: 确保Python 3.10+和必要的依赖已安装
3. **网络连接**: 确保能够访问https://api.football-data.org

## 🔧 配置步骤

### 1. 设置环境变量

创建 `.env` 文件（如果不存在）：

```bash
# 复制示例文件
cp .env.example .env

# 编辑文件，添加你的API Key
FOOTBALL_DATA_API_KEY=your_actual_api_key_here
```

### 2. 验证连接

运行验证脚本确保API连接正常：

```bash
python scripts/verify_api_connection.py
```

成功输出示例：
```
✅ API Key已配置 (长度: 32)
✅ 适配器初始化成功
✅ 获取到 380 场比赛数据
🎉 API连接验证成功！
```

## 🚀 使用方法

### 基本用法

```python
import asyncio
from src.adapters.football import ApiFootballAdapter

async def main():
    # 初始化适配器
    adapter = ApiFootballAdapter()

    try:
        # 初始化适配器
        await adapter.initialize()

        # 获取英超2024赛季比赛数据
        fixtures = await adapter.get_fixtures(league_code="PL", season=2024)
        print(f"获取到 {len(fixtures)} 场比赛")

        # 获取球队数据
        teams = await adapter.get_teams(league_code="PL")
        print(f"获取到 {len(teams)} 支球队")

        # 获取可用联赛
        competitions = await adapter.get_competitions()
        print(f"获取到 {len(competitions)} 个联赛")

    finally:
        # 清理适配器
        await adapter.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### 错误处理

```python
from src.adapters.football import ApiFootballAdapter, FootballAdapterError, FootballAdapterConnectionError

async def safe_api_call():
    adapter = ApiFootballAdapter()

    try:
        await adapter.initialize()
        fixtures = await adapter.get_fixtures("PL", 2024)
        return fixtures

    except FootballAdapterConnectionError as e:
        print(f"网络连接错误: {e}")
    except FootballAdapterError as e:
        print(f"适配器错误: {e}")
    finally:
        await adapter.cleanup()
```

## 📊 API端点说明

### 支持的联赛代码

- `PL`: 英超 (Premier League)
- `BL1`: 德甲 (Bundesliga)
- `SA`: 意甲 (Serie A)
- `FL1`: 法甲 (Ligue 1)
- `PD`: 西甲 (La Liga)

### 可用方法

1. **get_fixtures(league_code, season)**: 获取比赛赛程
2. **get_teams(league_code)**: 获取球队列表
3. **get_competitions()**: 获取可用联赛

## ⚠️ 注意事项

### API限制

- **免费版**: 每天10次请求限制
- **付费版**: 更高的请求限制和更多数据访问权限

### 错误码说明

- `403`: API Key无效或订阅过期
- `404`: 联赛代码或赛季不存在
- `429`: 请求频率超限
- `500`: 服务器内部错误

### 最佳实践

1. **缓存数据**: 避免重复请求相同数据
2. **错误重试**: 实现指数退避重试机制
3. **请求限制**: 遵守API的请求频率限制
4. **异常处理**: 妥善处理网络和API错误

## 🔍 故障排除

### 常见问题

1. **"FOOTBALL_DATA_API_KEY未配置"**
   - 检查 `.env` 文件是否存在
   - 确认API Key正确设置

2. **"API验证失败"**
   - 验证API Key是否有效
   - 检查网络连接

3. **"获取比赛数据失败: HTTP 404"**
   - 确认联赛代码和赛季参数正确
   - 检查该赛季是否有比赛数据

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查适配器状态
print(f"适配器状态: {adapter.status}")
print(f"错误信息: {adapter.get_error_info()}")
```

## 📚 参考资料

- [Football-Data.org 官方文档](https://www.football-data.org/documentation)
- [API v4 文档](https://www.football-data.org/v4/)
- [项目源码](https://github.com/xupeng211/FootballPrediction)