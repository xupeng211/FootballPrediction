# 新开发者入门指南

欢迎加入 FootballPrediction 项目！本指南帮助你在 **30 分钟**内快速上手。

---

## 前置要求

| 软件 | 版本 | 检查命令 |
|------|------|----------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Docker | 24+ | `docker --version` |
| Git | 最新 | `git --version` |

---

## 第一步：环境准备（5 分钟）

### 1.1 克隆项目

```bash
git clone https://github.com/your-org/FootballPrediction.git
cd FootballPrediction
git status  # 确认当前分支
```

### 1.2 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 1.3 配置环境变量

```bash
cp .env.example .env
nano .env  # 编辑 DB_PASSWORD
```

**最小配置**：

```bash
DB_HOST=db                  # Docker: db, WSL2: 172.25.16.1
DB_PASSWORD=your_password
```

---

## 第二步：启动服务（5 分钟）

```bash
make up              # 启动核心服务 (db + redis)
make ps              # 检查容器状态
```

预期输出：

```
NAME                           STATUS
football_prediction_db          Up (healthy)
football_prediction_redis       Up
```

---

## 第三步：验证环境（5 分钟）

```bash
# 测试代理
python main.py --test-proxy

# 运行测试采集
python main.py --source fotmob --mode single --limit 1 --dry-run
```

---

## 第四步：了解项目结构（10 分钟）

### 核心目录

```
FootballPrediction/
├── main.py                    # ⭐ 统一命令入口
├── Makefile                   # ⭐ 命令快捷方式
├── src/                       # 核心代码
│   ├── api/                   # 数据采集层
│   ├── ml/                    # ML 引擎
│   ├── processors/            # 特征提取
│   └── config/                # Python 配置管理
├── scripts/                   # 运维脚本
├── tests/                     # 测试
└── model_zoo/                 # 模型文件
```

### 关键文件

| 文件 | 作用 | 何时修改 |
|------|------|----------|
| `main.py` | 命令入口 | 很少改 |
| `src/config/__init__.py` | 配置入口 | 需要新增或读取统一配置 |
| `src/api/collectors/` | 数据采集 | 添加新数据源 |
| `src/ml/engine.py` | 预测引擎 | 修改模型 |
| `Makefile` | 快捷命令 | 添加新命令 |

---

## 第五步：第一次贡献（5 分钟）

### 5.1 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 5.2 工作流程

```bash
# 1. 修改代码
# 2. 添加测试
# 3. 运行质量检查
make verify

# 4. 提交变更
git add src/path/to/your_file.py
git add tests/path/to/test_file.py
git commit -m "feat: 添加 XXX 功能"

# 5. 推送到远程
git push origin feature/your-feature-name
```

---

## 常用命令

### 环境管理

```bash
make up                  # 启动核心服务
make up-pipeline         # 启动 + 数据流水线
make up-api              # 启动 + API 服务
make up-dev              # 启动 + 开发工具 (pgadmin)
make down                # 停止服务
make ps                  # 查看状态
make logs                # 查看日志
```

### 数据采集

```bash
# FotMob API 数据源
python main.py --source fotmob --mode single --limit 10

# OddsPortal RPA 数据源
python main.py --source oddsportal --mode single --limit 10

# 24h 巡航
python main.py --mode cruise

# 测试代理
python main.py --test-proxy
```

### 代码质量

```bash
make verify              # 快速验证 (lint + test-unit + security)
./scripts/run_checks.sh  # 完整质量门禁 (7 步检查)
ruff format src/ tests/  # 格式化代码
ruff check src/ tests/   # Lint 检查
```

### 测试

```bash
make test-unit           # 快速单元测试
pytest tests/ -v          # 运行所有测试
pytest tests/unit/test_config.py -v  # 运行单个文件
pytest tests/ -k "test_database" -v  # 按关键字运行
```

### 数据库

```bash
make db-shell            # 进入 PostgreSQL Shell
make db-backup           # 备份数据库
make db-reset            # 重置数据库 (危险!)
```

---

## 核心概念

### 数据流

```
数据采集层 (FotMob/OddsPortal)
    ↓
特征工程层 (GoldenExtractor)
    ↓
数据持久层 (PostgreSQL)
    ↓
预测引擎层 (XGBoost)
```

### 版本号体系

| 版本前缀 | 组件范围 |
|----------|----------|
| `V26.x` | ML 引擎和模型 |
| `V41.x` | 数据采集运维 |
| `V144.x` | 命令中心 (main.py) |

**项目版本** (`V26.7.0`) 与组件版本独立。

---

## 获取帮助

### 文档

- **快速参考**: `CLAUDE.md`
- **故障排除**: `docs/troubleshooting.md`
- **JavaScript 工具**: `docs/CLAUDE_JS_TOOLS.md`

### 诊断命令

```bash
python main.py --test-proxy              # 测试代理
python scripts/health_check.py          # 健康检查
make ps                                 # 查看容器状态
```

### 常见问题

**Q: 数据库连接失败？**

```bash
make up  # 启动服务
```

**Q: 测试失败？**

```bash
pytest tests/ -v -s  # 查看详细错误
```

**Q: 代码格式化失败？**

```bash
ruff format src/ tests/
ruff check src/ tests/ --fix
```

---

## 检查清单

开始开发前，确认：

- [ ] Python 3.11+ 已安装
- [ ] Node.js 18+ 已安装（JavaScript 工具需要）
- [ ] Docker 服务正在运行
- [ ] 虚拟环境已激活
- [ ] 依赖已安装
- [ ] 数据库服务已启动
- [ ] 环境变量已配置
- [ ] 测试可以运行

---

**预计完成时间**: 30 分钟

**最后更新**: 2026-01-31
