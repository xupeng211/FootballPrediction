# 故障排除指南 (Troubleshooting)

本文档提供 FootballPrediction 项目常见问题的诊断和解决方案。

---

## 📋 目录

- [数据库问题](#数据库问题)
- [网络与代理问题](#网络与代理问题)
- [数据采集问题](#数据采集问题)
- [ML 模型问题](#ml-模型问题)
- [Docker 问题](#docker-问题)
- [性能问题](#性能问题)

---

## 数据库问题

### `psycopg2.OperationalError: FATAL: database "football_db" does not exist`

**原因**: 数据库未初始化

**解决方案**:
```bash
# 方案 1: 使用 Docker
make up
docker-compose exec db psql -U football_user -c "CREATE DATABASE football_db"

# 方案 2: 本地 PostgreSQL
psql -U postgres -c "CREATE DATABASE football_db"
```

---

### `ConnectionRefusedError: [Errno 61] Connect call failed ('127.0.0.1', 5432)`

**原因**: 数据库未启动或端口配置错误

**诊断步骤**:
```bash
# 1. 检查数据库状态
docker-compose ps db
docker-compose exec db pg_isready -U football_user -d football_db

# 2. 检查配置
python -c "from src.config_unified import get_settings; print(get_settings().database)"

# 3. 测试连接
nc -zv localhost 5432  # 或 172.25.16.1 5432 (WSL2)
```

**解决方案**:
```bash
# 重启数据库
docker-compose restart db
```

---

### WSL2 环境数据库连接问题

**症状**: 本地 Python 无法连接 Docker 容器内的数据库

**原因**: WSL2 网络配置，需要使用 Docker 桥接网关 IP

**解决方案**:
```bash
# 检查 WSL2 网络配置
cat /etc/resolv.conf | grep nameserver

# 获取 Docker 桥接网关 IP (通常是 172.25.16.1)
docker network inspect footballprediction_default

# 设置环境变量
export DB_HOST=172.25.16.1
```

---

## 网络与代理问题

### `HTTP 429 Too Many Requests` 或 `HTTP 403 Forbidden`

**原因**: IP 被 API 网站封禁

**诊断步骤**:
```bash
# 1. 检查当前出口 IP
python main.py --test-proxy

# 2. 查看采集器日志
tail -f logs/v142_0_main.log | grep -E "403|429|被封"
```

**恢复策略**:
1. 等待冷却期 (6-24 小时)
2. 降低采集频率 (延迟到 2-5 秒)
3. 使用代理轮换
4. 启用 Ghost Protocol

**代理配置**:
```bash
# 环境变量方式
export HTTPS_PROXY=http://172.25.16.1:7890

# WSL2 自动探测 (推荐)
# BaseExtractor 会自动发现宿主机代理

# 代理文件方式
python main.py --proxy-file proxies.txt
```

---

### `playwright._impl._api_types.TimeoutError: Timeout 30000ms exceeded`

**原因**: 网络慢或页面加载超时

**解决方案**:
```bash
# 1. 检查代理配置
python main.py --test-proxy

# 2. 增加超时时间
# 在 BaseExtractor 中设置:
# timeout=60000  # 60 秒

# 3. 检查网络连接
ping -c 4 www.google.com
```

---

## 数据采集问题

### `KeyError: 'rolling_xg_home'`

**原因**: 特征提取失败，数据库中缺少历史数据

**诊断步骤**:
```bash
# 检查数据库中的历史数据
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT COUNT(*) FROM matches WHERE l2_raw_json IS NOT NULL;
"
```

**解决方案**:
```bash
# 1. 运行历史数据回填
python scripts/maintenance/fotmob_historical_backfill.py --years 3

# 2. 检查特征提取
python scripts/ops/check_db_consistency.py
```

---

### `ValueError: cannot reindex on an axis with duplicate labels`

**原因**: 数据重复

**解决方案**:
```bash
# 1. 检查重复数据
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT match_id, COUNT(*) FROM matches GROUP BY match_id HAVING COUNT(*) > 1;
"

# 2. 运行数据质量检查
python main.py --mode check

# 3. 清理重复数据
# 使用 ON CONFLICT DO UPDATE 或删除重复记录
```

---

### 采集器卡住不响应

**原因**: 页面加载慢或被 Cloudflare 拦截

**诊断步骤**:
```bash
# 1. 检查采集器日志
tail -f logs/v142_0_main.log

# 2. 查看错误截图
ls -lh logs/error_screens/

# 3. 检查 Ghost Protocol 状态
# 查看日志中的 "Ghost Protocol" 相关信息
```

**解决方案**:
```bash
# 1. 重启采集器
pkill -f harvester

# 2. 启用 Ghost Protocol
python main.py --mode single --no-ghost  # 先测试不用 Ghost
python main.py --mode single             # 再启用 Ghost

# 3. 更换代理
export HTTPS_PROXY=http://new_proxy:port
```

---

## ML 模型问题

### `AssertionError: Model file not found`

**原因**: 模型文件缺失或路径错误

**解决方案**:
```bash
# 1. 检查模型文件
ls -lh model_zoo/

# 2. 重新训练模型
python scripts/ml/train_model.py

# 3. 从备份恢复
cp backups/model_zoo_backup/* model_zoo/
```

---

### `AttributeError: 'NoneType' object has no attribute 'predict'`

**原因**: 模型加载失败

**诊断步骤**:
```bash
# 1. 检查模型文件完整性
python -c "
import pickle
with open('model_zoo/v26.8_epl_production.pkl', 'rb') as f:
    model = pickle.load(f)
    print(type(model))
"

# 2. 检查 ModelDispatcher 配置
python -c "from src.ml.engine import ModelDispatcher; print(ModelDispatcher().league_model_mapping)"
```

**解决方案**:
```bash
# 1. 验证模型文件格式
python scripts/ml/validate_model.py

# 2. 重新训练模型
python scripts/ml/train_model.py --league "Premier League"
```

---

### 预测结果异常 (概率过低或过高)

**原因**: 特征维度不一致或数据质量问题

**诊断步骤**:
```bash
# 1. 检查特征维度
python scripts/ops/check_db_consistency.py

# 2. 检查特征清单
python -c "
from src.processors.feature_manifest import FeatureManifest
manifest = FeatureManifest.from_file('config/v26_feature_manifest.json')
print(f'特征维度: {len(manifest.get_required_features())}')
"
```

**解决方案**:
```bash
# 1. 重新提取特征
python scripts/maintenance/reprocess_from_local.py

# 2. 验证特征清单
python scripts/ops/lock_feature_manifest.py --validate
```

---

## Docker 问题

### 容器无法启动

**诊断步骤**:
```bash
# 1. 查看容器状态
docker-compose ps

# 2. 查看容器日志
docker-compose logs --tail=100

# 3. 检查 Docker 资源
docker system df
```

**解决方案**:
```bash
# 1. 清理 Docker 资源
make clean-docker

# 2. 重建容器
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

### 容器内无法访问宿主机服务

**原因**: Docker 网络配置问题

**解决方案**:
```bash
# Docker Desktop (Mac/Windows)
# 使用 host.docker.internal
export DB_HOST=host.docker.internal

# Linux Docker
# 使用宿主机 IP (需要获取)
export DB_HOST=$(ip route | awk '/docker0/ {print $NF}')
```

---

## 性能问题

### 数据库查询慢

**诊断步骤**:
```bash
# 1. 检查慢查询日志
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT query, mean_exec_time, calls
    FROM pg_stat_statements
    ORDER BY mean_exec_time DESC
    LIMIT 10;
"

# 2. 检查索引
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'matches';
"
```

**解决方案**:
```bash
# 1. 创建缺失的索引
docker-compose exec db psql -U football_user -d football_db -c "
    CREATE INDEX IF NOT EXISTS idx_match_league_season
    ON matches(league_name, season);
"

# 2. 更新表统计信息
docker-compose exec db psql -U football_user -d football_db -c "
    VACUUM ANALYZE matches;
    VACUUM ANALYZE metrics_multi_source_data;
"
```

---

### 采集速度慢

**诊断步骤**:
```bash
# 1. 检查采集器配置
# 查看 logs/v142_0_main.log 中的时间戳

# 2. 测试网络速度
curl -o /dev/null -s -w "%{time_total}\n" https://api.ipify.org
```

**解决方案**:
```bash
# 1. 调整采集延迟
# 编辑 src/api/services/harvester_service.py
# 减小 delay_between_requests

# 2. 增加并发数
python scripts/ops/harvest_pinnacle_concurrent.py --workers 5

# 3. 使用代理轮换
# 配置多个代理，提高并发采集能力
```

---

## 完整诊断流程

当遇到未分类的问题时，按以下步骤诊断：

```bash
# 1. 检查服务状态
make ps

# 2. 查看所有日志
make logs-all

# 3. 运行健康检查
python scripts/health_check.py

# 4. 检查网络连接
python main.py --test-proxy

# 5. 检查数据库连接
docker-compose exec db pg_isready -U football_user -d football_db

# 6. 运行数据质量检查
python main.py --mode check

# 7. 运行测试套件
make verify
```

---

## 获取帮助

如果以上解决方案无法解决问题：

1. **查看日志**: `logs/` 目录下的相关日志文件
2. **运行诊断**: `python scripts/health_check.py --verbose`
3. **查看 GitHub Issues**: https://github.com/xupeng211/FootballPrediction/issues
4. **提交 Issue**: 包含完整的错误信息和复现步骤

---

**最后更新**: 2026-01-11
