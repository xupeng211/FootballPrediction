# 故障排除手册

## 🔍 快速诊断

### 环境状态检查

```bash
# 一键环境检查
make env-check

# 完整状态报告
make doctor

# 智能诊断
python3 scripts/smart_quality_fixer.py
```

### 核心问题识别

```bash
# 语法错误检查
python3 -m py_compile src/main.py

# 导入错误检查
python3 -c "import src.main"

# 测试环境检查
pytest --collect-only -q | head -20
```

## 🚨 常见问题及解决方案

### 1. 环境配置问题

#### 问题: Python环境不正确
**症状**: `command not found: python3` 或版本错误

**解决方案**:
```bash
# 检查Python版本
python3 --version  # 应该是3.11+

# 激活虚拟环境
source .venv/bin/activate

# 重新创建环境
make clean
make install
make env-check
```

#### 问题: 依赖缺失
**症状**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
```bash
# 自动修复
make fix-deps

# 手动安装
pip install -r requirements.txt

# 更新依赖
make update-deps

# 检查依赖冲突
pip check
```

### 2. 测试问题

#### 问题: 测试大量失败
**症状**: 100+测试失败

**解决方案**:
```bash
# 一键测试危机修复
make solve-test-crisis

# 智能修复
python3 scripts/smart_quality_fixer.py

# 逐步修复
make test-phase1          # 核心测试
make fix-test-errors       # 错误修复
make improve-test-quality  # 质量提升
```

#### 问题: 数据库测试失败
**症状**: `DatabaseManager is not initialized`

**解决方案**:
```bash
# 检查数据库配置
cat .env | grep DATABASE

# 使用测试数据库
export DATABASE_URL="sqlite:///:memory:"

# 修复导入路径
# 确保使用正确的导入路径:
# from src.database.connection import DatabaseManager  # ✅
# 而不是:
# from database.base import DatabaseManager  # ❌
```

#### 问题: 异步测试失败
**症状**: `RuntimeWarning: coroutine was never awaited`

**解决方案**:
```python
# 添加pytest-asyncio标记
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None

# 确保conftest.py配置正确
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### 3. 代码质量问题

#### 问题: Ruff错误过多
**症状**: 200+ Ruff错误

**解决方案**:
```bash
# 智能修复
python3 scripts/smart_quality_fixer.py

# 自动修复
ruff check src/ tests/ --fix --unsafe-fixes

# 分类修复
make syntax-fix          # 语法错误
make security-fix        # 安全问题
make style-fix          # 代码风格

# 渐进式修复
ruff check src/ --select=A,B,E,N,F | head -20  # 只看严重错误
```

#### 问题: 类型检查失败
**症状**: MyPy类型错误

**解决方案**:
```bash
# 类型检查
mypy src/ --ignore-missing-imports

# 添加类型注解
def process_data(data: dict[str, Any]) -> dict[str, Any]:
    return {"processed": True}

# 使用typing.Any作为临时解决方案
from typing import Any
```

### 4. API问题

#### 问题: FastAPI服务器启动失败
**症状**: `Address already in use` 或导入错误

**解决方案**:
```bash
# 检查端口占用
lsof -i :8000
kill -9 <PID>

# 检查导入问题
python3 -c "from src.main import app"

# 使用不同端口
uvicorn src.main:app --port 8001

# 检查环境变量
print $DATABASE_URL
print $REDIS_URL
```

#### 问题: 认证失败
**症状**: `401 Unauthorized` 或token错误

**解决方案**:
```python
# 检查SECRET_KEY配置
import os
assert os.getenv("SECRET_KEY") is not None

# 生成新token
python3 -c "
from src.security.jwt_auth import JWTAuthManager
manager = JWTAuthManager()
token = manager.create_access_token({'user_id': 1})
print(token)
"

# 验证token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/users/me
```

### 5. 数据库问题

#### 问题: 数据库连接失败
**症状**: `Connection refused` 或认证失败

**解决方案**:
```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 测试连接
psql -h localhost -U username -d database_name

# 检查连接字符串
echo $DATABASE_URL

# 使用SQLite作为后备
export DATABASE_URL="sqlite:///./test.db"
```

#### 问题: 数据库迁移失败
**症状**: `alembic upgrade head` 失败

**解决方案**:
```bash
# 检查迁移状态
alembic current
alembic history

# 强制迁移
alembic upgrade head --sql

# 回滚并重新迁移
alembic downgrade base
alembic upgrade head

# 生成新迁移
alembic revision --autogenerate -m "description"
```

### 6. 缓存问题

#### 问题: Redis连接失败
**症状**: `Redis connection failed`

**解决方案**:
```bash
# 检查Redis状态
redis-cli ping

# 启动Redis
redis-server

# 使用本地Redis替代
export REDIS_URL="redis://localhost:6379/0"

# 测试连接
python3 -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()
"
```

### 7. 性能问题

#### 问题: API响应慢
**症状**: 请求耗时>2秒

**解决方案**:
```python
# 添加性能监控
from src.monitoring.metrics import track_performance

@track_performance
async def slow_function():
    # 函数实现
    pass

# 使用缓存
from src.cache.decorators import cache_result

@cache_result(ttl=300)
async def expensive_operation():
    # 耗时操作
    pass

# 数据库查询优化
# 使用索引
# 避免N+1查询
# 使用连接池
```

#### 问题: 内存使用过高
**症状**: 内存泄漏或使用过多

**解决方案**:
```bash
# 内存分析
python3 -m memory_profiler src/main.py

# 检查对象引用
import gc
print(len(gc.get_objects()))

# 使用内存分析工具
pip install memory-profiler
python3 -m memory_profiler script.py
```

## 🔧 高级故障排除

### 1. 深度调试

#### 使用Python调试器
```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用ipdb（更友好的界面）
import ipdb; ipdb.set_trace()

# 在pytest中使用
pytest tests/unit/test_file.py::test_function --pdb
```

#### 使用日志调试
```python
from src.core.logger import get_logger

logger = get_logger(__name__)

def debug_function():
    logger.info("函数开始执行")
    try:
        result = some_operation()
        logger.debug(f"操作结果: {result}")
        return result
    except Exception as e:
        logger.error(f"函数执行失败: {e}")
        raise
```

### 2. 性能分析

#### CPU性能分析
```bash
# 使用cProfile
python3 -m cProfile -o profile.stats src/main.py

# 分析结果
python3 -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats(20)
"
```

#### 内存分析
```bash
# 使用memory_profiler
pip install memory-profiler
python3 -m memory_profiler src/main.py

# 使用tracemalloc
python3 -c "
import tracemalloc
tracemalloc.start()
# 运行代码
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"
```

### 3. 网络问题诊断

#### API连接测试
```bash
# 测试API端点
curl -v http://localhost:8000/health

# 测试POST请求
curl -X POST -H "Content-Type: application/json" \
     -d '{"key": "value"}' \
     http://localhost:8000/api/v1/endpoint

# 测试认证
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/protected
```

#### 数据库连接测试
```python
# 测试数据库连接
from src.database.connection import get_async_session
import asyncio

async def test_db_connection():
    try:
        session = await get_async_session()
        print("数据库连接成功")
        return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False

# 运行测试
asyncio.run(test_db_connection())
```

## 📊 监控和预警

### 系统健康检查

```python
from src.monitoring.health import HealthChecker

async def system_health_check():
    checker = HealthChecker()

    # 检查各个组件
    health_status = {
        "database": await checker.check_database(),
        "redis": await checker.check_redis(),
        "api": await checker.check_api(),
        "memory": checker.check_memory(),
        "disk": checker.check_disk()
    }

    return health_status
```

### 日志监控

```bash
# 实时查看日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log

# 查看性能日志
grep PERFORMANCE logs/app.log

# 日志分析
python3 scripts/analyze_logs.py logs/app.log
```

### 性能监控

```python
from src.monitoring.metrics import PerformanceMonitor

monitor = PerformanceMonitor()

# 监控API响应时间
@monitor.track_api_response_time
async def api_endpoint():
    # API逻辑
    pass

# 监控数据库查询性能
@monitor.track_db_query_time
async def db_operation():
    # 数据库操作
    pass
```

## 🚨 紧急恢复程序

### 完全环境重置

```bash
# 1. 备份当前状态
cp -r . backup_$(date +%Y%m%d_%H%M%S)

# 2. 清理环境
make clean
make clean-all

# 3. 重新安装
make install
make env-check

# 4. 恢复数据库
make db-restore

# 5. 验证环境
make test.unit
make coverage
```

### 数据库紧急修复

```bash
# 1. 停止应用
make down

# 2. 备份数据库
pg_dump football_prediction > backup_$(date +%Y%m%d).sql

# 3. 修复数据库
psql -d football_prediction -f fix_script.sql

# 4. 重启应用
make up

# 5. 验证数据
make db-check
```

### 服务紧急重启

```bash
# 快速重启服务
make restart

# 强制重建
make down
make up --force-recreate

# 检查服务状态
docker-compose ps
docker-compose logs app
```

## 📞 获取帮助

### 日志收集

```bash
# 生成诊断报告
make diagnostic-report

# 收集系统信息
make system-info

# 收集日志
make collect-logs
```

### 问题报告模板

创建GitHub Issue时包含：

1. **环境信息**
   ```bash
   python3 --version
   pip list | grep -E "(fastapi|sqlalchemy|pytest)"
   uname -a
   ```

2. **错误信息**
   ```bash
   # 完整的错误堆栈
   python3 -c "import src.main" 2>&1
   ```

3. **复现步骤**
   - 详细的操作步骤
   - 预期结果
   - 实际结果

4. **相关日志**
   ```bash
   # 相关日志片段
   tail -100 logs/app.log | grep -A 10 -B 10 "ERROR"
   ```

### 社区资源

- **文档**: 查看项目文档目录
- **Issues**: 搜索已有问题和解决方案
- **讨论**: GitHub Discussions
- **代码审查**: 请求团队成员协助

---

## 🎯 预防措施

### 定期维护

```bash
# 每周执行
make weekly-maintenance

# 每日检查
make daily-check

# 每月深度清理
make monthly-cleanup
```

### 监控设置

```bash
# 设置监控
make setup-monitoring

# 配置告警
make setup-alerts

# 健康检查
make health-check
```

### 备份策略

```bash
# 代码备份
git push origin main

# 数据备份
make backup-data

# 配置备份
make backup-config
```

---

*文档版本: v1.0 | 最后更新: 2025-11-08 | 维护者: Claude Code*