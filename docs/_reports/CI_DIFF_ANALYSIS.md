# CI 差异分析

## GitHub Actions 基线
- `ci.yml`：Ubuntu-latest、Python 3.11；安装 `pip install -r requirements.txt -r requirements-dev.txt && pip install -e . && make check-deps`。
- Fast suite：`pytest tests/unit --maxfail=1 --disable-warnings --cov=src --cov-report=term --cov-report=xml --cov-fail-under=80`。
- Slow suite：在 Postgres/Redis/Kafka 服务下运行，同样要求 80% 覆盖率。
- 其他工作流：`coverage-gate.yml`、`test-guard.yml` 等继续执行 `make coverage`、`make lint`、`make test` 等严格门禁。

## 本地执行发现的差异
- 默认 `pytest.ini` 强制 `-q --maxfail=1 --cov=src` 且禁用 `xdist`；导致任何脚本使用 `-n` 参数（如 `scripts/run_tests_with_report.py`、CI 中的并行计划）都会立即失败。
- 本地 `pytest` 在收集阶段因语法错误终止，实际覆盖率远低于 CI 要求（参考旧 `coverage.xml` 仅 17%）。
- `make prepush` 会直接运行 `black`/`isort`，当前仓库存在 100+ 自动生成的语法错误文件，导致格式化中断并改写大量文件；CI 端依赖该命令前提是代码无语法错误。
- 依赖集合通过 `requirements.lock` 安装成功，但 CI 还执行 `pip install -e .` 与 `make check-deps`，本地未验证。

## 容器/服务差异
- `docker build -t suite_check:local .` 需 9 分钟以上，命令在 120 秒超时前未完成；需要更长超时或分阶段构建。
- `docker compose config`/`up` 显示大量未设置的变量：`POSTGRES_PASSWORD`、`MINIO_ROOT_USER/PASSWORD`、`MLFLOW_DB_*`、`AWS_*` 等，默认回退为空字符串。
- `docker compose up -d` 过程中 BuildKit 多次输出错误栈信息；应检查自定义 Buildx 设置或拆分大规模服务。
- `curl http://localhost:8000/health` / `/metrics` → Connection refused（服务未启动）。CI 针对 FastAPI 端点的健康检查需要补齐启动脚本与配置。

## 建议的对齐动作
1. 将 `pytest.ini` 中的 `-p no:xdist` 与 `addopts` 与 CI 所需参数对齐；或更新脚本避免为禁用插件传递 `-n`。
2. 在 `Makefile` 中为 `prepush` 增加语法预检（`python scripts/fix_test_syntax.py`）以防批量写坏文件。
3. 提供 `.env.ci` 样例并在 `docker-compose` 里引用，确保敏感变量使用占位符而非空字符串。
4. 复刻 CI 环境的命令组合：`python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt && pip install -e . && make check-deps && pytest tests/unit --maxfail=1 --disable-warnings --cov=src --cov-fail-under=80`。
