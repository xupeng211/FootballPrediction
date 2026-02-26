# GEMINI.md

This file provides context and guidance for Gemini when working on the **FootballPrediction V57.0** project.

## 🚨 核心指令 (Critical Instructions)

### 1. 语言要求 (Language Requirement)
**请务必使用中文回复用户！**
This is the highest priority non-functional requirement. All conversational output must be in Chinese.

### 2. 核心原则 (Core Principles)
*   **生产级标准**: 代码必须符合 V57.0 的生产级质量要求（类型安全、测试覆盖、文档完整）。
*   **最小修改**: 遵守 "Minimal Change" 原则，优先修改现有文件，严禁创建 `_v2`, `_new` 等版本后缀文件。
*   **架构边界**: 严格遵守 L1/L2/L3 采集架构和 Service/Adapter/Domain 分层，禁止跨层违规调用。
*   **测试保护**: 修改代码后必须运行 `make verify`，禁止为了通过测试而弱化断言。

---

## 📋 项目概览 (Project Overview)

**FootballPrediction** 是一个基于 **XGBoost 3.0+** 的专业足球比赛预测系统，旨在实现 **年化 25% 真实收益率**。

*   **当前版本**: V57.0 (Production Ready)
*   **核心状态**: 版本大一统完成 | 智能自愈引擎 | 毫秒级感应 | 100% 测试覆盖
*   **关键指标**: 基线准确率 56% (真赛前) | 推理延迟 <100ms

### 技术栈 (Tech Stack)
*   **Language**: Python 3.11+
*   **ML**: XGBoost 3.0+, Scikit-learn, Pandas, Playwright (自动采集)
*   **Web**: FastAPI
*   **Database**: PostgreSQL 15 (业务数据), Redis 7 (缓存/队列)
*   **Infrastructure**: Docker, Docker Compose
*   **Quality**: Ruff, Black, Mypy, Pytest, Bandit

---

## 🛠️ 常用命令 (Common Commands)

所有操作优先使用 `Makefile`：

### 启动与运行
*   **启动核心服务 (DB + Redis)**:
    ```bash
    make up
    ```
*   **启动所有服务**:
    ```bash
    make up-all
    ```
*   **运行生产收割引擎**:
    ```bash
    python scripts/production_harvester.py
    ```

### 质量与测试
*   **完整验证 (提交前必跑)**:
    ```bash
    make verify
    ```
    *(包含 lint, format, unit tests, security checks)*
*   **运行全量测试**:
    ```bash
    make test
    ```
*   **代码格式化**:
    ```bash
    make format
    ```

### 数据库操作
*   **进入 DB Shell**:
    ```bash
    make db-shell
    ```
*   **重置数据库 (慎用)**:
    ```bash
    make db-reset
    ```

---

## 🏗️ 核心架构与文件 (Architecture & Files)

### 1. 数据采集 (Data Harvest - V83.0)
采用 L1/L2/L3 三层架构：
*   **L1 (基础)**: `src/api/collectors/fotmob_core.py` - 赛程、基础统计。
*   **L2 (开盘)**: `src/api/collectors/odds_production_extractor.py` - Pinnacle 开盘赔率 (悬停提取)。
*   **L3 (终盘)**: `src/api/collectors/odds_production_extractor.py` - OddsPortal 终盘赔率。
*   **调度入口**: `scripts/production_harvester.py` - 智能轮询、IP 监控、自愈机制。

### 2. 机器学习 (Machine Learning)
*   **引擎入口**: `src/ml/engine.py` - 包含 `ModelDispatcher` (联赛专项模型分发)。
*   **特征工程**: `src/ml/features/` - V25.1 自适应特征提取。
*   **推理服务**: `src/ml/inference/` - 生产级预测服务。

### 3. 配置与基础设施
*   **统一配置**: `src/config_unified.py` - 使用 `get_settings()` 获取配置，严禁硬编码。
*   **数据库连接**: 必须使用 `psycopg2.extras.RealDictCursor`。
*   **Docker**: `docker-compose.yml` 定义了 db, redis, pipeline_worker 等服务。

---

## 🛡️ 开发规范 (Development Guidelines)

1.  **类型注解**: 所有函数必须包含完整的 Type Hints (e.g., `def func(a: int) -> str:`).
2.  **错误处理**: 使用 `src/core/exceptions.py` 中的标准异常。
3.  **日志记录**: 使用统一的 logger，禁止使用 `print`。
4.  **环境隔离**:
    *   Docker 环境 DB host: `db`
    *   本地开发 DB host: `localhost`
    *   使用 `src.config_unified` 自动处理。

## 🔍 故障排查 (Troubleshooting)

*   **HTTP 429/403**: 采集被封禁。系统会自动冷却，或需人工更换 IP。
*   **DB 连接失败**: 检查 `docker-compose ps` 确保 db 服务健康。
*   **测试失败**: 优先修复代码逻辑，禁止修改测试断言来掩盖问题。

---
**Gemini Context Updated**: 2026-01-03
