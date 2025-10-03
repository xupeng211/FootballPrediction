# 深度体检报告（FootballPrediction）

## 执行摘要
整体健康度偏低：测试体系在收集阶段即失败，核心业务代码仍停留在 TODO 占位层面，安全基线存在多项未修复漏洞。上线前需优先补齐测试语法、实现缺失逻辑，并完成依赖与配置加固。

## 🔴 红色 Blockers
1. **测试套件无法导入**
   - 根因：大量自动生成的测试文件缩进/语法错误（如 `tests/unit/api/test_api_models.py:140`、`tests/integration/models/test_model_integration.py:361`）。
   - 复现：`pytest -q -ra --maxfail=1`。
   - 修复方案：逐一修复 try/except 缩进、`await` 调用位置，可先运行 `ruff check tests/unit/api` 指导改动，再执行格式化工具。
   - 预计影响：未修复前 CI 直接失败，无法验证任何功能或生成覆盖率。

2. **核心业务逻辑仍为占位实现**
   - 根因：`src/scheduler/tasks.py`、`src/data/collectors/*.py`、`src/services/content_analysis.py` 等关键任务保留 `TODO`，实际返回伪数据或空结果。
   - 复现：`rg "# TODO" src/scheduler src/data src/services`。
   - 修复方案：按照数据管道设计补齐预测生成、数据采集、清洗与告警逻辑，并新增集成测试验证。
   - 预计影响：即使部署成功，仍无法提供真实预测结果，业务不可用。

3. **生产基线依赖与配置缺失**
   - 根因：`docker compose config` 显示大量必填变量（`POSTGRES_PASSWORD`、`MINIO_ROOT_USER`、`AWS_*` 等）默认空值；`curl http://localhost:8000/health` 拒绝连接。
   - 复现：`docker compose config` / `docker compose up -d` / `curl -sS http://localhost:8000/health`。
   - 修复方案：整理 `.env.production` 模板，为数据库、对象存储、MLflow 等生成独立凭据；在 compose 文件中引用并提供最小启动脚本。
   - 预计影响：现状下无法安全启动容器栈，上线部署会立刻失败。

## 🟡 黄色 Major
- **覆盖率与质量门槛全线告警**：最新 `coverage.xml` 行覆盖率 17.25%，远低于 CI 80% 要求；Top 20 未覆盖模块集中在 `src/services`、`src/api`、`src/monitoring`。
- **依赖漏洞未修复**：`safety check` 报告 16 个漏洞，包含 `knack<=0.12.0` ReDoS、`feast 0.47.0` XSS 等；需评估升级与替代方案。
- **静态检查噪声巨大**：`ruff` 输出 4286 条告警（含语法错误），`mypy` 在 `docs/legacy/*.py` 直接报语法错误；建议先隔离遗留脚本或加入排除目录。
- **Bandit 中等级风险**：`src/database/sql_compatibility.py` 等处使用字符串拼接 SQL，存在注入风险。

## 🟢 Quick Wins
- 在 `pytest.ini` 中恢复 `-vv`/`-ra` 可读性，移除或条件化 `-p no:xdist`，配合脚本默认参数。
- 运行 `python scripts/fix_test_syntax.py`（若可用）或编写一次性脚本批量修复常见缩进模式。
- 立即生成 `.env.ci`，在 compose/Makefile 中引用，避免空密码默认值。

## 测试套件体检
- 失败点：详见 `docs/_reports/TEST_SUMMARY.md`，核心是 5 个语法错误文件。
- Flaky：未进入执行阶段，暂无数据。
- Skip/xfail：无新记录。
- 覆盖率：参考旧报告 17.25%。Top 20 未覆盖模块与缺失行数列于 `TEST_SUMMARY.md`。
- 阈值对齐建议：恢复基础单元测试后执行 `pytest tests/unit --cov=src --cov-fail-under=80` 与 `make coverage`。

## 依赖与安全
- `pip check`：通过。
- `safety`：16 个漏洞（knack, feast, azure 系列），详情见 `docs/_reports/DEPENDENCY_ISSUES.md`。
- `bandit`：43 条告警，其中 12 条 MEDIUM 级别 SQL 注入风险（`src/database/sql_compatibility.py:222-290` 等）。
- `ruff`：4286 条告警（语法、未使用变量、未定义名称等）。
- `mypy`：阻塞于 `docs/legacy/async_database_test_template.py` 语法错误。

## CI/容器一致性
- GitHub Actions 要求 Python 3.11、`pip install -e .`、`make check-deps`、单测覆盖率≥80%。
- 本地默认禁用 xdist，脚本参数未与 CI 对齐，导致 `scripts/run_tests_with_report.py` 自动失败。
- Docker build 需>9分钟且在默认超时内失败；docker-compose 依赖多项密钥，未配置时服务无法启动。
- 详见 `docs/_reports/CI_DIFF_ANALYSIS.md`。

## 外部依赖与可替代策略
- 数据库：Postgres（主库/MLflow/Marquez），可提供 `docker-compose.test.yml` 供本地模拟。
- 缓存与队列：Redis、Celery、Kafka；建议在测试中 mock 或使用 `pytest` fixture 启动轻量容器。
- 对象存储：MinIO + AWS 兼容接口；本地测试可使用 `minio` 容器或 `moto`。
- MLflow/监控：Grafana、Prometheus、Alertmanager；建议提供干净的 docker profile 与 fake client。

## 落地修复计划
- **D1（今日完成）**
  1. 修复五个语法错误测试文件 → `pytest -q -ra --maxfail=1` 全量通过收集阶段。
  2. 恢复 `pytest.ini`/脚本参数一致性 → `python scripts/run_tests_with_report.py` 无报错。
- **D3（本周完成）**
  1. 实现 `src/scheduler/tasks.py` 预测与数据管道 TODO → 新增集成测试 `pytest tests/integration -k prediction` 通过。
  2. 将 SQL 拼接改为参数化查询 → `bandit -r src -q` 无 MEDIUM 级别。
  3. 修复安全漏洞依赖（knack、feast 等）→ `safety scan` 零高危。
- **D7（下周后）**
  1. 补齐 Top 20 未覆盖模块的单测/集成测试 → `pytest tests/unit --cov=src --cov-fail-under=80` 通过。
  2. 梳理 docker-compose 环境变量并提供本地最小 profile → `docker compose up -d` 成功拉起核心 API，`curl http://localhost:8000/health` 返回 200。

## 附录
- 测试输出：`docs/_reports/TEST_SUMMARY.md`
- 安全与依赖：`docs/_reports/DEPENDENCY_ISSUES.md`、`docs/_reports/BANDIT_REPORT.json`
- CI 差异：`docs/_reports/CI_DIFF_ANALYSIS.md`
- 环境快照：`docs/_reports/ENV_SNAPSHOT.md`
- TODO 看板：`docs/_reports/BUGFIX_TODO.md`
