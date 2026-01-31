# Football Prediction System - 开发者上手手册

**版本**: V77.000
**目标读者**: 新加入团队的开发者、运维工程师
**预计阅读时间**: 30 分钟

---

## 1. 环境对齐

### 1.1 一键环境配置

```bash
# 克隆项目后，在项目根目录执行

# 1. 启动核心�心服务 (PostgreSQL + Redis)
make up

# 2. 验证环境
python -m pytest tests/processors/test_ultimate_extractor.py -v

# 3. 运行 72 个自动化测试
python -m pytest tests/processors/test_ultimate_extractor.py \
                 tests/core/test_ghost_protocol.py \
                 tests/unit/test_unified_collector_processor.py -v
```

### 1.2 环境要求

| 组件 | 版本要求 | 验证命令 |
|------|----------|----------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| PostgreSQL | 15+ | `docker exec football_db psql --version` |
| Docker | 24+ | `docker --version` |
| Make | 任意 | `make --version` |

### 1.3 推荐开发工具

```bash
# 代码格式化 + Lint
make format
make lint

# 类型检查
mypy src/

# 安全扫描
bandit -r src/
```

---

## 2. 核心概念速览

### 2.1 "唯一动力源" (SOE) 架构

所有操作必须通过统一入口：

```
数据采集 → FotMobCoreCollector
特征提取 → UltimateFeatureExtractor
反爬防护 → GhostBrowser
```

### 2.2 关键文件位置

| 功能 | 文件路径 | 说明 |
|------|----------|------|
| **特征提取** | `src/processors/ultimate_extractor.py` | 唯一特征提取入口 ⭐ |
| **反爬防护** | `src/core/ghost_protocol.py` | Ghost Protocol 实现 ⭐ |
| **熔断器** | `src/core/circuit_breaker.py` | 故障隔离 |
| **队名映射** | `src/core/team_name_normalizer.py` | 哈希对齐引擎 |
| **控制中心** | `scripts/ops/control.sh` | 一键运维脚本 |

---

## 3. 扩展协议：新增联赛

### 3.1 步骤一：更新联赛配置

编辑 `config/global_harvest_list.yaml`:

```yaml
leagues:
  - name: "Chinese Super League"
    fotmob_id: "77"
    oddsportal_name: "china/chinese-super-league"
    season: "2024"
    country: "China"
    tier: 3  # 1=五大联赛, 2=二级, 3=三级
```

### 3.2 步骤二：添加队名映射

编辑 `src/core/team_name_normalizer.py`:

```python
# 在 TEAM_NAME_MAPPINGS 中添加
TEAM_NAME_MAPPINGS = {
    # ... 现有映射 ...
    "北京国安": ["Beijing Guoan", "Beijing CS"],
    "上海海港": ["Shanghai Port", "Shanghai SIPG"],
    "山东泰山": ["Shandong Taishan", "Shandong Luneng"],
    # ... 更多映射 ...
}
```

### 3.3 步骤三：运行测试验证

```bash
# 验证队名映射
pytest tests/unit/test_team_name_normalizer.py -v

# 试采集 1 场比赛
python -m src.harvesters.oddsportal_archive \
    --league "Chinese Super League" \
    --season "2024" \
    --limit 1
```

### 3.4 步骤四：全量采集

```bash
./scripts/ops/control.sh start
```

---

## 4. 扩展协议：新增特征

### 4.1 步骤一：定义特征函数

在 `src/processors/` 中创建或修改文件：

```python
# 示例: src/processors/my_custom_feature.py

def calculate_custom_feature(match_data: dict) -> float:
    """计算自定义特征"""
    home_team = match_data.get("home_team")
    away_team = match_data.get("away_team")

    # 实现特征计算逻辑
    # ...

    return feature_value
```

### 4.2 步骤二：注册到工厂

编辑 `src/processors/ultimate_extractor.py`:

```python
class UltimateFeatureExtractor:
    def extract_ultimate_features(self, match_data, verbose=False):
        # ... 现有代码 ...

        # 6. 添加自定义特征
        custom_value = calculate_custom_feature(match_data)
        validated_features["my_custom_feature"] = custom_value

        return validated_features
```

### 4.3 步骤三：更新白名单

```python
# 在 ultimate_extractor.py 中
PRE_MATCH_FEATURE_WHITELIST = {
    # ... 现有特征 ...
    "my_custom_feature",  # 新增特征
}
```

### 4.4 步骤四：编写测试

在 `tests/processors/` 中创建测试文件：

```python
# tests/processors/test_my_custom_feature.py

import pytest
from src.processors.my_custom_feature import calculate_custom_feature

def test_calculate_custom_feature():
    match_data = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
    }
    result = calculate_custom_feature(match_data)
    assert isinstance(result, float)
```

---

## 5. 测试防线

### 5.1 运行全部 72 个测试

```bash
# 完整测试套件
python -m pytest tests/processors/test_ultimate_extractor.py \
                 tests/core/test_ghost_protocol.py \
                 tests/unit/test_unified_collector_processor.py -v
```

### 5.2 按类别运行测试

```bash
# 仅特征提取测试
pytest tests/processors/test_ultimate_extractor.py -v

# 仅 Ghost Protocol 测试
pytest tests/core/test_ghost_protocol.py -v

# 仅集成测试
pytest tests/unit/test_unified_collector_processor.py -v
```

### 5.3 解读测试结果

```
========================== test session starts ==========================
tests/processors/test_ultimate_extractor.py::TestUltimateExtractorConfig::test_default_config_exists PASSED [  3%]
tests/core/test_ghost_protocol.py::TestRetryPolicy::test_calculate_delay_exponential_backoff PASSED [ 45%]
tests/unit/test_unified_collector_processor.py::TestFullPipelineIntegration::test_end_to_end_feature_extraction PASSED [ 95%]

============================== 72 passed in 2.35s ==============================
```

**状态码说明**:
- `PASSED` ✅ - 测试通过
- `FAILED` ❌ - 测试失败，需要修复
- `SKIPPED` ⏭️ - 测试被跳过（条件不满足）
- `XFAILED` ⚠️ - 预期失败（已知问题）

### 5.4 覆盖率报告

```bash
# 生成 HTML 覆盖率报告
pytest tests/ --cov=src --cov-report=html

# 查看报告
open htmlcov/index.html
```

---

## 6. 常用开发命令

### 6.1 代码质量

```bash
# 格式化代码
ruff format src/ tests/

# Lint 检查
ruff check src/ tests/

# 自动修复
ruff check src/ tests/ --fix

# 完整质量门禁
./scripts/run_checks.sh
```

### 6.2 数据库操作

```bash
# 进入数据库 Shell
make db-shell

# 查看表结构
\d matches
\d matches_mapping

# 查看数据分布
SELECT status, COUNT(*) FROM match_pipeline_state GROUP BY status;
```

### 6.3 日志查看

```bash
# 查看实时日志
tail -f logs/orchestrator.log

# 查看最近 100 行
./scripts/ops/control.sh logs 100

# 查看错误日志
grep ERROR logs/orchestrator.log | tail -20
```

---

## 7. 调试技巧

### 7.1 启用详细日志

```bash
# 设置环境变量
export LOG_LEVEL=DEBUG

# 运行程序
python -m src.harvesters.oddsportal_archive --limit 1
```

### 7.2 使用 Python 调试器

```python
# 在代码中插入断点
import pdb; pdb.set_trace()

# 或使用 ipdb (增强版)
import ipdb; ipdb.set_trace()
```

### 7.3 检查数据完整性

```sql
-- 检查 L2 数据完整性
SELECT
    COUNT(*) as total,
    COUNT(l2_raw_json) as with_l2,
    100.0 * COUNT(l2_raw_json) / COUNT(*) as completeness_percent
FROM matches;
```

---

## 8. Git 工作流

### 8.1 标准提交流程

```bash
# 1. 确认当前分支
git status

# 2. 创建功能分支
git checkout -b feature/your-feature-name

# 3. 进行代码修改
# ... 编辑文件 ...

# 4. 提交前质量检查
make verify

# 5. 添加变更文件
git add src/path/to/your_file.py
git add tests/path/to/test_file.py

# 6. 提交变更
git commit -m "feat: 添加 XXX 功能

- 实现了 XXX 特性
- 添加了对应的单元测试
- 通过了 72/72 测试验证"

# 7. 推送到远程
git push origin feature/your-feature-name
```

### 8.2 提交消息规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

---

## 9. 故障排除

### 9.1 常见错误

#### 错误 1: 数据库连接失败

```bash
# 症状: psycopg2.OperationalError: FATAL: database "football_db" does not exist

# 解决方案:
make up
docker-compose exec db psql -U football_user -c "CREATE DATABASE football_db;"
```

#### 错误 2: 测试失败

```bash
# 症状: ImportError: cannot import name 'XXX'

# 解决方案:
pip install -e .
```

#### 错误 3: 权限问题

```bash
# 症状: Permission denied

# 解决方案:
sudo chown -R $USER:$USER .
```

### 9.2 获取帮助

```bash
# 查看帮助文档
./scripts/ops/control.sh help

# 查看架构文档
cat docs/ARCHITECTURE.md

# 查看运维手册
cat docs/OPERATIONS_SOP.md
```

---

## 10. 快速参考卡

### 10.1 核心文件

| 文件 | 用途 |
|------|------|
| `src/processors/ultimate_extractor.py` | 特征提取入口 |
| `src/core/ghost_protocol.py` | Ghost Protocol |
| `scripts/ops/control.sh` | 控制中心 |
| `tests/unit/test_unified_collector_processor.py` | 集成测试 |

### 10.2 核心命令

```bash
# 启动系统
./scripts/ops/control.sh start

# 停止系统
./scripts/ops/control.sh stop

# 查看状态
./scripts/ops/control.sh status

# 修复失败记录
./scripts/ops/control.sh repair

# 运行测试
python -m pytest tests/ -v
```

---

**最后更新**: 2026-01-25
