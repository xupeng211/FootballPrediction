# MCP 工具链配置指南

## 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Claude Code (MCP Client)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ stdio / JSON-RPC
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MCP Configuration                                   │
│                     .claude/mcp-config.json                                  │
└─────────────────────────────────────────────────────────────────────────────┘
         │              │              │              │              │
         ▼              ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ filesystem  │ │   postgres  │ │   pytest    │ │   docker    │ │  playwright │
│     MCP     │ │     MCP     │ │     MCP     │ │     MCP     │ │     MCP     │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
       │              │              │              │              │
       ▼              ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   项目文件   │ │ PostgreSQL  │ │   pytest    │ │   Docker    │ │  Chromium   │
│   读写访问   │ │  只读查询   │ │   测试执行  │ │   容器管理  │ │   浏览器    │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
       │              │              │              │
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FootballPrediction Project                               │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐                 │
│  │    src/   │  │  tests/   │  │  scripts/ │  │   data/   │                 │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘                 │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Docker Compose Services                             │  │
│  │  ┌─────┐ ┌───────┐ ┌────────┐ ┌────────────┐ ┌──────────────────┐     │  │
│  │  │ db  │ │ redis │ │  api   │ │  pipeline  │ │   production     │     │  │
│  │  └─────┘ └───────┘ └────────┘ └────────────┘ └──────────────────┘     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
/home/xupeng/projects/FootballPrediction/
├── .claude/
│   ├── mcp-config.json          # MCP 配置文件 (主配置)
│   ├── settings.json            # Claude Code 设置
│   └── settings.local.json      # 本地设置
│
├── mcp_servers/                  # MCP 服务器脚本
│   ├── pytest_server.py         # pytest MCP 服务器
│   └── docker_server.py         # Docker MCP 服务器
│
├── deploy/docker/
│   └── init_claude_reader.sql   # PostgreSQL 只读用户创建脚本
│
├── scripts/ops/
│   ├── setup_mcp.sh             # MCP 安装脚本
│   └── verify_mcp.sh            # MCP 验证脚本
│
└── docker-compose.mcp.yml       # MCP Docker Compose 扩展
```

## 执行顺序

### Step 1: 安装依赖
```bash
cd /home/xupeng/projects/FootballPrediction
bash scripts/ops/setup_mcp.sh
```

### Step 2: 创建 PostgreSQL 只读用户
```bash
# 启动数据库 (如果未运行)
docker-compose up -d db

# 执行 SQL 脚本
docker-compose exec -T db psql -U football_user -d football_db < deploy/docker/init_claude_reader.sql

# 验证用户创建
docker-compose exec db psql -U claude_reader -d football_db -c "SELECT current_user"
```

### Step 3: 重启 Claude Code
```bash
# 退出当前 Claude Code 会话，重新启动
# MCP 配置会自动加载
```

### Step 4: 验证配置
```bash
bash scripts/ops/verify_mcp.sh
```

## 验证 Checklist

| 检查项 | 命令 | 预期结果 |
|--------|------|----------|
| MCP 配置文件存在 | `cat .claude/mcp-config.json` | JSON 格式配置 |
| Filesystem MCP 可用 | `npx -y @modelcontextprotocol/server-filesystem --help` | 帮助信息 |
| PostgreSQL MCP 可用 | `npx -y @modelcontextprotocol/server-postgres --help` | 帮助信息 |
| Python MCP SDK 安装 | `python -c "import mcp"` | 无错误 |
| PostgreSQL 只读用户 | `docker-compose exec db psql -U claude_reader -d football_db -c "SELECT 1"` | 返回 1 |
| Docker 可用 | `docker ps` | 容器列表 |
| Docker Compose 可用 | `docker-compose ps` | 服务列表 |

## MCP 工具功能

### 1. Filesystem MCP
- **功能**: 读写项目文件
- **范围**: 仅限 `/home/xupeng/projects/FootballPrediction`
- **命令**: 自动通过 Claude Code 调用

### 2. PostgreSQL MCP
- **功能**: 执行只读 SQL 查询
- **用户**: `claude_reader`
- **权限**: SELECT only
- **示例查询**:
```sql
-- 查看最近预测
SELECT * FROM predictions ORDER BY created_at DESC LIMIT 10;

-- 统计比赛数据
SELECT COUNT(*) FROM matches WHERE match_time > NOW();
```

### 3. pytest MCP
- **工具**:
  - `run_tests`: 运行测试
  - `get_test_failures`: 获取失败日志
  - `get_coverage_report`: 获取覆盖率报告
  - `run_continuous_bugfix`: 运行持续修复

### 4. Docker MCP
- **工具**:
  - `docker_ps`: 列出容器
  - `docker_logs`: 查看日志
  - `docker_exec`: 执行命令
  - `compose_up`: 启动服务
  - `compose_down`: 停止服务
  - `compose_restart`: 重启服务
  - `get_service_health`: 健康检查
- **安全限制**:
  - 仅允许访问项目 docker-compose.yml 定义的服务
  - 禁止执行危险命令 (rm -rf, dd, 等)

## 潜在风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| PostgreSQL 只读用户权限过大 | 数据泄露 | 定期审计权限，仅授予 SELECT |
| Docker 命令注入 | 容器被破坏 | 黑名单过滤危险命令 |
| Filesystem 访问越界 | 敏感文件泄露 | 限制项目目录范围 |
| MCP 服务资源占用 | 系统性能下降 | 设置资源限制 |

## 故障排查

### MCP 服务未加载
```bash
# 检查配置文件
cat .claude/mcp-config.json

# 检查路径是否正确
ls -la mcp_servers/

# 重启 Claude Code
```

### PostgreSQL 连接失败
```bash
# 检查数据库是否运行
docker-compose ps db

# 检查用户是否存在
docker-compose exec db psql -U football_user -d football_db -c "\du"

# 重新创建用户
docker-compose exec -T db psql -U football_user -d football_db < deploy/docker/init_claude_reader.sql
```

### pytest MCP 报错
```bash
# 检查 MCP SDK
pip show mcp

# 重新安装
pip install --upgrade mcp
```

### Docker MCP 报错
```bash
# 检查 Docker 权限
docker ps

# 检查 docker-compose 文件
docker-compose config
```
