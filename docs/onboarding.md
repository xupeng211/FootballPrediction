# 新开发者快速上手指南 (Onboarding)

欢迎使用 FootballPrediction 项目！本文档帮助你在 30 分钟内快速上手。

---

## 📋 目录

- [前置要求](#前置要求)
- [5 分钟快速启动](#5-分钟快速启动)
- [15 分钟核心概念](#15-分钟核心概念)
- [30 分钟实战练习](#30-分钟实战练习)
- [下一步学习](#下一步学习)

---

## 前置要求

### 必需软件

| 软件 | 版本要求 | 用途 | 检查命令 |
|------|----------|------|----------|
| Python | 3.11+ | 核心开发语言 | `python --version` |
| Docker | 24+ | 容器化部署 | `docker --version` |
| Docker Compose | 2.0+ | 服务编排 | `docker-compose --version` |
| Git | 2.0+ | 版本控制 | `git --version` |
| PostgreSQL 客户端 | 15+ | 数据库连接 | `psql --version` |

### 可选软件

- **VS Code** 或 **PyCharm**: 推荐的 Python IDE
- **pgAdmin**: PostgreSQL 图形化管理工具
- **Redis Commander**: Redis 图形化管理工具

---

## 5 分钟快速启动

### 步骤 1: 克隆项目 (1 分钟)

```bash
# 克隆仓库
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 检查 Python 版本
python --version  # 应该是 3.11+
```

### 步骤 2: 配置环境 (2 分钟)

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置数据库密码
# 最少需要配置:
# DB_PASSWORD=your_secure_password

# 使用你喜欢的编辑器打开 .env
# nano .env
# vim .env
# code .env  # VS Code
```

### 步骤 3: 启动服务 (1 分钟)

```bash
# 启动核心服务 (db + redis)
make up

# 等待服务启动 (约 10-20 秒)
# 检查服务状态
make ps
```

### 步骤 4: 验证安装 (1 分钟)

```bash
# 运行测试代理
python main.py --test-proxy

# 如果看到出口 IP 信息，说明安装成功！
```

---

## 15 分钟核心概念

### 系统架构 (5 分钟)

FootballPrediction 采用**三层架构**:

```
┌─────────────────────────────────────────────┐
│  main.py - V144.7 命令中心                   │
│  统一入口，支持多数据源                      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  HarvesterService - V142.0 收割服务          │
│  队列驱动，Ghost Protocol 保护               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  PostgreSQL - 数据持久层                     │
│  matches 表 + metrics_multi_source_data 表   │
└─────────────────────────────────────────────┘
```

**关键术语**:

| 术语 | 说明 |
|------|------|
| **Ghost Protocol** | V141.0 反爬检测系统，随机化浏览器指纹 |
| **收割 (Harvest)** | 数据采集过程，从外部 API 获取比赛数据 |
| **FotMob** | L1 数据源，提供比赛基础信息和统计数据 |
| **OddsPortal** | L3 数据源，提供赔率数据 |

### 核心目录结构 (5 分钟)

```
FootballPrediction/
├── src/                          # 生产代码
│   ├── api/collectors/           # 数据采集器
│   │   ├── base_extractor.py     # Ghost Protocol 基类
│   │   └── fotmob_core.py        # FotMob API 采集
│   ├── ml/                       # ML 引擎
│   │   └── engine.py             # XGBoost 模型
│   └── config_unified.py         # 统一配置
├── scripts/                      # 运维脚本
│   ├── ops/                      # 运维脚本
│   └── maintenance/              # 维护脚本
├── tests/                        # 测试套件
├── main.py                       # ⭐ 命令入口
├── Makefile                      # ⭐ 命令快捷方式
└── CLAUDE.md                     # ⭐ 项目文档
```

### 常用命令 (5 分钟)

```bash
# === 服务管理 ===
make up              # 启动核心服务
make down            # 停止服务
make ps              # 查看状态
make logs            # 查看日志

# === 开发命令 ===
make verify          # 代码质量检查 (提交前必须运行!)
make test-unit       # 运行单元测试
make format          # 格式化代码

# === 数据采集 ===
python main.py --source fotmob --mode single --limit 10   # 采集 10 场比赛
python main.py --mode check                              # 数据质量检查

# === 数据库 ===
make db-shell        # 进入 PostgreSQL Shell
make db-backup       # 备份数据库
```

---

## 30 分钟实战练习

### 练习 1: 运行首次数据采集 (10 分钟)

```bash
# 1. 测试模式（不实际采集）
python main.py --source fotmob --mode single --limit 1 --dry-run

# 2. 实际采集 1 场比赛
python main.py --source fotmob --mode single --limit 1

# 3. 查看采集的数据
make db-shell
```

在 PostgreSQL Shell 中运行:
```sql
-- 查看最新采集的比赛
SELECT match_id, league_name, home_team, away_team, match_time
FROM matches
ORDER BY match_time DESC
LIMIT 5;

-- 退出
\q
```

### 练习 2: 理解数据流 (10 分钟)

```bash
# 1. 查看数据库表结构
make db-shell
```

在 PostgreSQL Shell 中运行:
```sql
-- 查看 matches 表结构
\d matches

-- 查看 metrics_multi_source_data 表结构
\d metrics_multi_source_data

-- 退出
\q
```

```bash
# 2. 查看特征清单
cat config/v26_feature_manifest.json | head -50

# 3. 查看模型文件
ls -lh model_zoo/
```

### 练习 3: 运行测试 (10 分钟)

```bash
# 1. 运行单元测试
make test-unit

# 2. 运行完整质量检查
make verify

# 3. 查看测试覆盖率（可选）
pytest tests/ --cov=src --cov-report=html
# 报告生成在 htmlcov/index.html
```

---

## 下一步学习

### 推荐阅读顺序

1. **本文档** (onboarding.md) - 快速上手 ✅ 当前文档
2. **CLAUDE.md** - 完整项目文档
3. **docs/CHANGELOG.md** - 版本历史
4. **docs/troubleshooting.md** - 故障排除

### 深入学习路径

#### 路径 A: 数据采集工程师

```bash
# 学习重点
1. src/api/collectors/          # 数据采集器
2. src/api/services/            # 收割服务
3. scripts/ops/                 # 运维脚本

# 实践任务
- [ ] 理解 Ghost Protocol 工作原理
- [ ] 添加一个新的数据源
- [ ] 优化采集器性能
```

#### 路径 B: 机器学习工程师

```bash
# 学习重点
1. src/ml/                      # ML 引擎
2. src/processors/              # 特征提取
3. scripts/ml/                  # ML 训练脚本

# 实践任务
- [ ] 理解特征工程流程
- [ ] 训练一个新的模型
- [ ] 优化模型性能
```

#### 路径 C: 后端工程师

```bash
# 学习重点
1. src/main.py                  # FastAPI 入口
2. src/api/v1/endpoints/        # API 路由
3. src/database/                # 数据库层

# 实践任务
- [ ] 添加一个新的 API endpoint
- [ ] 优化数据库查询
- [ ] 实现 API 认证
```

### 常见问题

**Q: 如何调试数据采集问题？**

```bash
# 1. 查看日志
tail -f logs/v144_7_main.log

# 2. 运行诊断
python scripts/health_check.py

# 3. 测试代理
python main.py --test-proxy
```

**Q: 如何添加新特征？**

```bash
# 1. 编辑特征提取器
# src/processors/v25_production_extractor.py

# 2. 更新特征清单
# config/v26_feature_manifest.json

# 3. 重新训练模型
# scripts/ml/train_model.py
```

**Q: 如何部署到生产环境？**

```bash
# 1. 检查 docs/troubleshooting.md 中的部署章节

# 2. 运行部署命令
make deploy

# 3. 监控服务状态
make health
```

---

## 获取帮助

- **文档**: 查看项目根目录的 `CLAUDE.md`
- **故障排除**: 查看 `docs/troubleshooting.md`
- **GitHub Issues**: https://github.com/xupeng211/FootballPrediction/issues

---

## 📊 项目版本信息

了解项目的当前状态有助于你更好地理解系统：

| 属性 | 值 |
|------|-----|
| **项目版本** | V26.7.0 (pyproject.toml) |
| **生产版本** | V69.000 (Pipeline Orchestrator) |
| **命令中心** | V144.9 (Multi-Source Command Center) |
| **ML 模型** | V26.8 (联赛专项模型) |
| **状态** | ✅ Production Ready |

**版本号说明**: 本项目采用多版本号体系，不同组件独立演进：
- `V26.x`: ML 特征引擎和模型
- `V36.x`: 数据同步和自动化
- `V41.x`: 数据采集运维工具
- `V69.x`: Pipeline 编排器
- `V144.x`: 多数据源命令中心

> 详细版本历史请查看 `CLAUDE.md` 的版本演进章节。

---

**祝你开发愉快！** 🎉

**最后更新**: 2026-01-25
