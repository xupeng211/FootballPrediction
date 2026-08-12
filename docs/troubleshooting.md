# 故障排除指南

本文档提供 FootballPrediction 项目常见问题的诊断和解决方案。

---

## 快速诊断流程

遇到问题时，按以下顺序诊断：

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

## 数据库问题

### `database does not exist`

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
python -c "from src.config import get_settings; print(get_settings().database)"

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

## 网络与代理问题

### `HTTP 429 Too Many Requests` 或 `HTTP 403 Forbidden`

**原因**: IP 被 API 网站封禁

**诊断步骤**:

```bash
# 1. 检查当前出口 IP
python main.py --test-proxy

# 2. 查看采集器日志
tail -f logs/v144_7_main.log | grep -E "403|429|被封"
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

### `prediction model unavailable`

**含义**：canonical `v26_7_aligned` artifact 当前缺失、未激活、校验失败，
或 manifest / feature contract 绑定不可用。git-tracked 当前状态是
`status=pending`、`checksum_sha256=null`，因此 CLI 非零退出、HTTP 返回
503 都是预期的 fail-closed 行为。

**诊断**：

```bash
cat config/model_artifacts.json
cat config/model_feature_contracts.json
docker compose -f docker-compose.dev.yml exec -T dev \
  python -m src.ml.inference.predict_cli --help
```

不要通过直接 pathname 加载、Titan fallback、`v26_mini` 或训练命令绕过
canonical artifact 状态。artifact 恢复、checksum 记录和 activation 属于
单独授权的后续操作。

---

### 预测入口选错模型

默认 `npm run predict` 必须进入
`src.ml.inference.predict_cli`，再通过共享 runtime owner 使用
`v26_7_aligned` 的 verified loader、manifest 和 feature contract。若需要
审计旧 DB/Titan 兼容路径，命令名必须明确写成
`npm run predict:titan-legacy`；该路径不是 canonical，也不能把其旧特征
补齐、重命名或映射成 canonical 20-feature 输入。

---

### 输入契约或特征维度不一致

canonical registry `v26_7_aligned/v1` 固定 20 个有序特征，由
`V26_6_PreMatchAdapter` 形成。CLI 只接收与 HTTP 相同的 JSON payload；不
接受旧 `prediction_repo.extract_features()` 产生的 Titan DB 字典作为隐式
转换输入。缺失或不确定的历史特征来源应让输入失败，不能用零值、默认值
或 H2H 补位伪造 canonical 特征。

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

## JavaScript/Node.js 问题

### `Cannot find module 'playwright'` 或相关错误

**原因**: Node.js 依赖未安装或浏览器未安装

**解决方案**:

```bash
cd scripts/ops

# 1. 安装 Node.js 依赖
npm install

# 2. 安装 Playwright 浏览器
npx playwright install chromium

# 3. 验证安装
node --version  # 应该是 18+
npm --version
```

### Jest 测试失败

**解决方案**:

```bash
cd scripts/ops

# 运行特定测试文件
npx jest tests/interaction_v52.test.js

# 运行特定测试
npx jest -t "test_name"

# 查看覆盖率
npm run test:coverage
```

---

## 性能问题

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

## 完整错误速查表

| 错误 | 原因 | 快速解决方案 |
|------|------|-------------|
| `database does not exist` | 数据库未初始化 | `make up` |
| `ConnectionRefusedError` | 数据库未启动 | `make up` |
| `HTTP 429` | API 限流 | 等待 6-24 小时 |
| `HTTP 403` | IP 被封禁 | 检查代理配置 |
| `TimeoutError` | 网络慢 | 检查代理，增加超时 |
| `KeyError: 'rolling_xg_home'` | 特征提取失败 | 运行历史回填 |
| `cannot reindex` | 数据重复 | 运行 `python main.py --mode check` |
| `Model file not found` | 模型缺失 | 重新训练或从备份恢复 |
| `Cannot find module 'playwright'` | Node.js 依赖缺失 | `cd scripts/ops && npm install` |

---

## 获取帮助

如果以上解决方案无法解决问题：

1. **查看日志**: `logs/` 目录下的相关日志文件
2. **运行诊断**: `python scripts/health_check.py --verbose`
3. **查看 GitHub Issues**: <https://github.com/xupeng211/FootballPrediction/issues>
4. **提交 Issue**: 包含完整的错误信息和复现步骤

---

**最后更新**: 2026-01-31
