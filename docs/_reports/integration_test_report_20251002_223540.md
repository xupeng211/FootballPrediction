# 集成测试报告

## 执行结果
- **状态**: ⚠️ 失败
- **时间**: Thu Oct  2 22:35:40 CST 2025
- **执行时长**: 28秒
- **退出码**: 1

## 服务状态
```
NAME           IMAGE              COMMAND                  SERVICE   CREATED          STATUS                         PORTS
docker-api-1   python:3.11-slim   "bash -c 'pip instal…"   api       28 seconds ago   Restarting (1) 7 seconds ago   
docker-db-1    postgres:15        "docker-entrypoint.s…"   db        28 seconds ago   Up 27 seconds                  5432/tcp
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
db-1  | 
db-1  | PostgreSQL Database directory appears to contain a database; Skipping initialization
db-1  | 
db-1  | 2025-10-02 14:35:12.985 UTC [1] LOG:  starting PostgreSQL 15.14 (Debian 15.14-1.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
db-1  | 2025-10-02 14:35:12.985 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
db-1  | 2025-10-02 14:35:12.985 UTC [1] LOG:  listening on IPv6 address "::", port 5432
db-1  | 2025-10-02 14:35:12.995 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
db-1  | 2025-10-02 14:35:13.007 UTC [30] LOG:  database system was shut down at 2025-10-02 14:34:47 UTC
db-1  | 2025-10-02 14:35:13.015 UTC [1] LOG:  database system is ready to accept connections
api-1  | ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements-minimal.txt'
api-1  | 
api-1  | [notice] A new release of pip is available: 24.0 -> 25.2
api-1  | [notice] To update, run: pip install --upgrade pip
api-1  | ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements-minimal.txt'
api-1  | 
api-1  | [notice] A new release of pip is available: 24.0 -> 25.2
api-1  | [notice] To update, run: pip install --upgrade pip
api-1  | ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements-minimal.txt'
api-1  | 
api-1  | [notice] A new release of pip is available: 24.0 -> 25.2
api-1  | [notice] To update, run: pip install --upgrade pip
api-1  | ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements-minimal.txt'
api-1  | 
api-1  | [notice] A new release of pip is available: 24.0 -> 25.2
api-1  | [notice] To update, run: pip install --upgrade pip
api-1  | ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements-minimal.txt'
api-1  | 
api-1  | [notice] A new release of pip is available: 24.0 -> 25.2
api-1  | [notice] To update, run: pip install --upgrade pip
```

## 建议
- 如果测试失败，请检查服务是否正常运行
- 确认数据库连接配置正确
- 查看具体测试失败原因

---
Generated at Thu Oct  2 22:35:47 CST 2025
