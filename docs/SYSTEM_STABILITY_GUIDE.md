# 系统稳定性指南 (System Stability Guide)

**版本**: V41.79
**日期**: 2026-01-15
**状态**: Production Ready

---

## 📋 概述

本文档提供 FootballPrediction 系统的稳定性保障指南，涵盖新联赛接入、队名冲突解决、代理配置等核心操作。

---

## 🌍 新增联赛支持

### 1. 联赛配置

在 `src/config_unified.py` 中添加联赛配置：

```python
# 示例：添加葡超（Liga Portugal）
LEAGUES = {
    "Liga Portugal": {
        "country": "Portugal",
        "season_format": "2023/2024",
        "fotmob_league_id": 62,  # FotMob League ID
    },
}
```

### 2. OddsPortal URL 映射

```python
# OddsPortal URL 格式
base_url = "https://www.oddsportal.com/football/portugal/liga-portugal-2023-2024/results/"
```

### 3. 数据库验证

```sql
-- 验证联赛数据已入库
SELECT COUNT(*), season
FROM matches
WHERE league_name = 'Liga Portugal'
GROUP BY season;
```

---

## 🔍 SemanticRefiner 使用指南

### 队名冲突解决

`SemanticRefiner` 使用智能语义匹配解决队名冲突：

#### 1. 添加队名缩写

编辑 `src/utils/team_alias.py`：

```python
TEAM_ABBREVIATIONS: Dict[str, str] = {
    # 葡超球队缩写
    'slb': 'benfica',           # SL Benfica
    'fcp': 'porto',             # FC Porto
    'scp': 'sporting cp',        # Sporting CP
}
```

#### 2. 添加通用术语

防止误匹配：

```python
generic_terms = {
    'city', 'united', 'fc', 'athletic',
    'club', 'ac', 'inter', 'real',
    'benfica', 'porto', 'sporting'
}
```

#### 3. 配置置信度阈值

```python
# 在 CrawlerService 中调整
refiner = SemanticRefiner(
    db_conn=conn,
    confidence_threshold=85.0,  # 85% 置信度阈值
)
```

### 对齐失败日志

自动记录到 `logs/alignment_failures_YYYYMMDD.csv`：

```csv
timestamp,url,slug,raw_home,raw_away,hash_value,failure_reason,suggested_matches
2026-01-15T12:00:00,/football/xyz/unknown-vs-team-AbCd1234/,unknown-vs-team,Unknown,Team,AbCd1234,No database match above threshold (85.0%),match1|match2
```

---

## 🔌 19 端口代理配置

### 端口范围

```python
# CrawlerService 默认配置
PROXY_PORTS: list[int] = list(range(7891, 7910))  # 7891-7909 (19 个端口)
```

### 代理主机配置

```python
# WSL2 环境
WSL2_PROXY_HOST: str = "172.25.16.1"

# 本地环境
LOCAL_PROXY_HOST: str = "127.0.0.1"
```

### ProxyHealthChecker 配置

```python
proxy_health_checker = ProxyHealthChecker(
    proxy_host="172.25.16.1",
    check_interval=60,              # 60 秒检查间隔
    max_consecutive_failures=3,     # 3 次失败后移除端口
)
```

### 端口健康检查

```bash
# 检查单个端口
timeout 3 bash -c "</dev/tcp/172.25.16.1/7891" && echo "✅ 7891 可用"

# 检查多个端口
for port in 7891 7892 7893 7894 7895; do
    timeout 3 bash -c "</dev/tcp/172.25.16.1/$port" && echo "✅ $port 可用" || echo "❌ $port 不可用"
done
```

---

## 🛡️ 数据库隔离保护

### 环境检测

系统启动时自动检测本地 PostgreSQL 冲突：

```python
# config_unified.py
_validate_database_environment(_settings_instance)
```

### 错误示例

```
🚨 V41.77: 数据库环境验证失败
   错误: 检测到本地 PostgreSQL 服务占用 5432 端口
   请确保数据库环境正确配置
```

### 解决方案

```bash
# 停止本地 PostgreSQL 服务
sudo service postgresql stop

# 或者跳过验证（仅开发环境）
export SKIP_ENV_VALIDATION=1
```

---

## 🧪 TDD 测试规范

### 测试组织

```
tests/
├── unit/                    # 单元测试
│   ├── test_v41_77_team_alias_tdd.py           # 65 个测试
│   ├── test_v41_77_match_repository_tdd.py     # 19 个测试
│   └── test_v41_77_semantic_refiner_tdd.py     # 28 个测试
└── integration/             # 集成测试
    └── test_v41_78_pipeline.py                 # 21 个测试
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行特定测试文件
pytest tests/unit/test_v41_77_semantic_refiner_tdd.py -v
```

### 代码质量检查

```bash
# Lint 检查
ruff check src/ tests/

# 类型检查
mypy src/

# 安全扫描
bandit -r src/

# 完整验证
make verify
```

---

## 🚀 生产部署检查清单

### 部署前检查

- [ ] 所有测试通过 (pytest tests/)
- [ ] 代码质量检查通过 (ruff check)
- [ ] 类型检查通过 (mypy src/)
- [ ] 无残留 print() 语句
- [ ] 所有方法都有 Docstring
- [ ] 所有方法都有类型提示
- [ ] 无临时调试脚本
- [ ] 数据库隔离验证已启用
- [ ] 代理健康检查已启用

### 环境变量检查

```bash
# .env 文件配置
DB_NAME=football_db
DB_HOST=db                    # Docker 环境使用 "db"
DB_PORT=5432
DB_USER=football_user
DB_PASSWORD=football_pass
```

### Docker 服务检查

```bash
# 检查服务状态
docker ps

# 检查数据库容器
docker logs football_prediction_db

# 重启服务
make restart
```

---

## 📊 监控指标

### 对齐成功率

```sql
-- 计算对齐成功率
SELECT
    league_name,
    season,
    COUNT(*) as total_matches,
    COUNT(mm.oddsportal_hash) as aligned_matches,
    ROUND(100.0 * COUNT(mm.oddsportal_hash) / COUNT(*), 2) as alignment_rate
FROM matches m
LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
GROUP BY league_name, season
ORDER BY alignment_rate DESC;
```

### 代理端口状态

```python
# 实时查看可用端口
crawler = CrawlerService(db_conn=conn, enable_proxy_health_check=True)
print(f"可用端口: {len(crawler.available_ports)}/{len(crawler.proxy_ports)}")
```

### 对齐失败日志

```bash
# 查看今日失败记录
cat logs/alignment_failures_$(date +%Y%m%d).csv | wc -l

# 分析失败原因
cut -d',' -f7 logs/alignment_failures_$(date +%Y%m%d).csv | sort | uniq -c
```

---

## 🆘 故障排除

### 问题 1: 对齐成功率低

**症状**: 对齐成功率 < 85%

**解决方案**:

1. 检查队名缩写配置 (`TEAM_ABBREVIATIONS`)
2. 检查通用术语配置 (`generic_terms`)
3. 降低置信度阈值 (谨慎使用)

### 问题 2: 代理端口不可用

**症状**: 可用端口数量 < 10

**解决方案**:

1. 检查代理服务状态
2. 重启代理服务
3. 检查防火墙配置

### 问题 3: 数据库连接失败

**症状**: `database does not exist` 或 `connection refused`

**解决方案**:

1. 检查 Docker 服务状态 (`make ps`)
2. 检查数据库容器日志
3. 验证环境变量配置

---

## 📚 相关文档

- [CLAUDE.md](../CLAUDE.md) - 核心开发指南
- [onboarding.md](onboarding.md) - 新开发者快速上手
- [troubleshooting.md](troubleshooting.md) - 故障排除指南
- [V41.78_COMPLETION_REPORT.md](V41.78_COMPLETION_REPORT.md) - V41.78 完成报告

---

**文档维护者**: 首席系统架构师
**最后更新**: 2026-01-15
**版本**: V41.79 Final
