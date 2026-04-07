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

说明:

- 上图以 Claude Code 为例展示仓库内 MCP 配置流
- Codex CLI 使用本机 `~/.codex/config.toml`，不读取仓库内 `.claude/mcp-config.json`
- 仓库内脚本只能验证仓库配置和依赖，不能代替 Codex CLI 对本机配置的实际加载结果

## 目录结构

```
/home/xupeng/projects/FootballPrediction/
├── .claude/
│   ├── mcp-config.json          # Claude Code MCP 配置
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
│   └── verify_mcp.sh            # MCP 验证与重载提示脚本
│
└── docker-compose.mcp.yml       # MCP Docker Compose 扩展
```

## 执行顺序

### Step 1: 启动开发容器

```bash
cd /home/xupeng/projects/FootballPrediction
docker-compose -f docker-compose.dev.yml up -d
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

### Step 3: 重载 MCP

```bash
# 如果修改了 .claude/mcp-config.json、~/.codex/config.toml
# 或 mcp_servers/*.py，需要退出当前 Claude / Codex 会话并重新启动客户端
```

补充说明:

- Claude Code 读取仓库内 `.claude/mcp-config.json`
- Codex CLI 读取本机 `~/.codex/config.toml`
- 如果 `filesystem`、`postgres`、`playwright` 通过 `npx` 启动，且当前机器网络或代理较慢，建议在 `~/.codex/config.toml` 中显式设置更长的 `startup_timeout_sec`
- `bash scripts/ops/verify_mcp.sh` 只验证仓库内配置与依赖，不检查 `~/.codex/config.toml` 是否已被 Codex CLI 实际加载

示例:

```toml
[mcp_servers.filesystem]
startup_timeout_sec = 180

[mcp_servers.postgres]
startup_timeout_sec = 180

[mcp_servers.playwright]
startup_timeout_sec = 180
```

### Step 4: 验证配置

```bash
# 说明: 该脚本只验证仓库内配置与依赖，不验证 Codex CLI 本机配置是否已生效
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
- **命令**: 自动通过当前 MCP 客户端调用

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

- **实际执行方式**:
  `docker-compose -f docker-compose.dev.yml exec -T dev python -m pytest ...`
- **说明**:
  统一走 `dev` 容器，避免宿主机缺失 `pandas`、`pytest` 等项目依赖。

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
# 检查 Claude Code 配置文件
cat .claude/mcp-config.json

# 如果使用 Codex CLI，手动检查本机配置
sed -n '1,160p' ~/.codex/config.toml

# 检查路径是否正确
ls -la mcp_servers/

# 修改 .claude/mcp-config.json、~/.codex/config.toml
# 或 mcp_servers/*.py 后，重启对应客户端
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
# 先跑仓库内验证脚本
bash scripts/ops/verify_mcp.sh

# 再重启客户端，重新加载 MCP 配置
# 如果是 Codex CLI 启动超时，手动检查 ~/.codex/config.toml 中对应 MCP 的 startup_timeout_sec
```

### Docker MCP 报错

```bash
# 检查 Docker 权限
docker ps

# 检查 docker-compose 文件
docker-compose config
```
