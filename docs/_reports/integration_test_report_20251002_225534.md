# 集成测试报告

## 执行结果
- **状态**: ⚠️ 失败
- **时间**: Thu Oct  2 22:55:34 CST 2025
- **执行时长**: 30秒
- **退出码**: 1

## 服务状态
```
NAME             IMAGE              COMMAND                  SERVICE   CREATED          STATUS          PORTS
docker-api-1     python:3.11-slim   "bash -c 'pip instal…"   api       29 seconds ago   Up 28 seconds   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
docker-db-1      postgres:15        "docker-entrypoint.s…"   db        29 seconds ago   Up 28 seconds   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
docker-redis-1   redis:7-alpine     "docker-entrypoint.s…"   redis     29 seconds ago   Up 28 seconds   0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp
```

## 测试统计
tests/integration/test_api_integration.py: 4
tests/integration/test_api_to_database_integration.py: 15
tests/integration/test_database_integration.py: 3
tests/integration/test_memory_database.py: 6
tests/integration/test_simple_api.py: 8
tests/integration/test_simple_db.py: 5
tests/integration/test_sqlite_integration.py: 5
tests/integration/test_standalone_api.py: 8

=============================== warnings summary ===============================
.venv/lib/python3.11/site-packages/pydantic/_internal/_config.py:291
  /home/user/projects/FootballPrediction/.venv/lib/python3.11/site-packages/pydantic/_internal/_config.py:291: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.9/migration/
    warnings.warn(DEPRECATION_MESSAGE, DeprecationWarning)

.venv/lib/python3.11/site-packages/great_expectations/data_context/types/base.py:1098
  /home/user/projects/FootballPrediction/.venv/lib/python3.11/site-packages/great_expectations/data_context/types/base.py:1098: ChangedInMarshmallow4Warning: `Number` field should not be instantiated. Use `Integer`, `Float`, or `Decimal` instead.
    config_version: fields.Number = fields.Number(

src/api/predictions.py:102
  /home/user/projects/FootballPrediction/src/api/predictions.py:102: DeprecationWarning: `example` has been deprecated, please use `examples` instead
    match_id: int = Path(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
SKIPPED [1] tests/integration/test_cache_integration.py:21: Cache modules not available

## 日志信息
### Docker服务日志
```
redis-1  | 1:C 02 Oct 2025 14:55:05.719 * oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
redis-1  | 1:C 02 Oct 2025 14:55:05.719 * Redis version=7.4.5, bits=64, commit=00000000, modified=0, pid=1, just started
redis-1  | 1:C 02 Oct 2025 14:55:05.719 # Warning: no config file specified, using the default config. In order to specify a config file use redis-server /path/to/redis.conf
redis-1  | 1:M 02 Oct 2025 14:55:05.719 * monotonic clock: POSIX clock_gettime
redis-1  | 1:M 02 Oct 2025 14:55:05.720 * Running mode=standalone, port=6379.
redis-1  | 1:M 02 Oct 2025 14:55:05.720 * Server initialized
redis-1  | 1:M 02 Oct 2025 14:55:05.720 * Ready to accept connections tcp
db-1     | 
db-1     | PostgreSQL Database directory appears to contain a database; Skipping initialization
db-1     | 
db-1     | 2025-10-02 14:55:05.768 UTC [1] LOG:  starting PostgreSQL 15.14 (Debian 15.14-1.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
db-1     | 2025-10-02 14:55:05.769 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
db-1     | 2025-10-02 14:55:05.769 UTC [1] LOG:  listening on IPv6 address "::", port 5432
db-1     | 2025-10-02 14:55:05.785 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
db-1     | 2025-10-02 14:55:05.802 UTC [29] LOG:  database system was shut down at 2025-10-02 14:54:55 UTC
db-1     | 2025-10-02 14:55:05.808 UTC [1] LOG:  database system is ready to accept connections
api-1    | [notice] A new release of pip is available: 24.0 -> 25.2
api-1    | [notice] To update, run: pip install --upgrade pip
api-1    | 2025-10-02 14:55:25,900 - src.main - INFO - MINIMAL_API_MODE 启用：跳过安全与性能中间件
api-1    | 2025-10-02 14:55:25,901 - src.main - INFO - MINIMAL_API_MODE 启用，仅注册健康检查路由
api-1    | INFO:     Started server process [1]
api-1    | INFO:     Waiting for application startup.
api-1    | 2025-10-02 14:55:25,901 - src.main - INFO - 🚀 足球预测API启动中...
api-1    | 2025-10-02 14:55:25,901 - src.main - INFO - ⚙️ MINIMAL_API_MODE 启用：跳过数据库、Redis、监控初始化
api-1    | INFO:     Application startup complete.
api-1    | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
api-1    | 2025-10-02 14:55:26,033 - src.api.health - INFO - 健康检查请求: minimal_mode=True
api-1    | ⚠️  使用通用方式抑制 Marshmallow 警告
api-1    | ⚠️  使用通用方式抑制 Marshmallow 警告
api-1    | ⚠️  使用通用方式抑制 Marshmallow 警告
api-1    | INFO:     172.18.0.1:47202 - "GET /health HTTP/1.1" 200 OK
api-1    | 2025-10-02 14:55:32,254 - src.api.health - INFO - 健康检查请求: minimal_mode=True
api-1    | INFO:     172.18.0.1:39036 - "GET /health HTTP/1.1" 200 OK
api-1    | INFO:     172.18.0.1:39050 - "GET /docs HTTP/1.1" 200 OK
api-1    | INFO:     172.18.0.1:39062 - "GET /metrics HTTP/1.1" 404 Not Found
api-1    | INFO:     172.18.0.1:39072 - "GET /predictions/ HTTP/1.1" 404 Not Found
```

## 建议
- 如果测试失败，请检查服务是否正常运行
- 确认数据库连接配置正确
- 查看具体测试失败原因

---
Generated at Thu Oct  2 22:55:40 CST 2025
