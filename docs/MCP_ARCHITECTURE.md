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
│                    Repository MCP Reference                                  │
│          .claude/mcp-config.json (not runtime loading proof)                 │
└─────────────────────────────────────────────────────────────────────────────┘
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   filesystem    │ │     pytest      │ │     docker      │ │   playwright    │
│       MCP       │ │       MCP       │ │       MCP       │ │       MCP       │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    项目文件      │ │    pytest 测试   │ │   Docker 容器    │ │    Chromium     │
│    读写访问      │ │      执行        │ │      管理         │ │      浏览器      │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │                   │
         └───────────────────┴───────────────────┴───────────────────┘
                                      │
                                      ▼
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

- 上图展示仓库内 MCP reference 的结构，不代表当前宿主已经加载这些 entry
- 当前 tracked `.claude/mcp-config.json` 没有 PostgreSQL MCP entry
- 仓库没有 MCP loader；当前宿主是否读取该环境相关配置必须单独确认
- Codex CLI 使用本机 `~/.codex/config.toml`，不读取仓库内 `.claude/mcp-config.json`
- 仓库内脚本只能验证仓库配置和依赖，不能代替 Codex CLI 对本机配置的实际加载结果

## 目录结构

```
/home/xupeng/projects/FootballPrediction/
├── .claude/
│   ├── mcp-config.json          # 环境相关 MCP reference（不是加载证明）
│   ├── settings.json            # Claude Code 设置
│   └── settings.local.json      # 本地设置
│
├── mcp_servers/                  # MCP 服务器脚本
│   ├── pytest_server.py         # pytest MCP 服务器
│   └── docker_server.py         # Docker MCP 服务器
│
├── deploy/docker/
│   └── init_claude_reader.sql   # PostgreSQL NOLOGIN ACL role 初始化脚本
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

### Step 2: 确认历史 PostgreSQL MCP 登录已退役

`deploy/docker/init_claude_reader.sql` 由 PostgreSQL 官方 initdb 入口在 fresh development
database 初始化时调用。它保留 `claude_reader` 的既有 ACL，但将该 role provision 为
`NOLOGIN`，且不再 provision password。不要以 `claude_reader` 发起认证探测或把它作为
interactive/MCP 登录身份。

如需核对已运行 development database 的状态，应通过受支持的管理员 metadata 路径查询
`pg_roles.rolcanlogin`，预期 `claude_reader` 为 `false`；该检查不需要也不应使用历史
credential。

### Step 3: 宿主配置变更后的重载

```bash
# 仅当已单独证明当前宿主会加载对应配置时，退出并重新启动该客户端
# repository entry 本身不能证明 active loading
```

补充说明:

- `.claude/mcp-config.json` 是环境相关 reference；仓库本身不负责加载
- Codex CLI 读取本机 `~/.codex/config.toml`
- 如果 `filesystem`、`playwright` 通过 `npx` 启动，且当前机器网络或代理较慢，建议在 `~/.codex/config.toml` 中显式设置更长的 `startup_timeout_sec`
- `bash scripts/ops/verify_mcp.sh` 只验证仓库内配置与依赖，不检查 `~/.codex/config.toml` 是否已被 Codex CLI 实际加载
- 当前没有受支持的 PostgreSQL MCP LOGIN identity；不要自行向本机配置添加替代登录 role

示例:

```toml
[mcp_servers.filesystem]
startup_timeout_sec = 180

[mcp_servers.playwright]
startup_timeout_sec = 180
```

### Step 4: 验证配置

```bash
# 说明: 该脚本只验证仓库内配置与依赖，不证明任何宿主已主动加载 MCP entry
bash scripts/ops/verify_mcp.sh
```

## 验证 Checklist

| 检查项 | 命令 | 预期结果 |
|--------|------|----------|
| MCP reference 格式 | `python3 -m json.tool .claude/mcp-config.json >/dev/null` | exit 0 |
| Filesystem MCP 可用 | `npx -y @modelcontextprotocol/server-filesystem --help` | 帮助信息 |
| Python MCP SDK 安装 | `python -c "import mcp"` | 无错误 |
| 历史 PostgreSQL ACL role | 通过管理员 metadata 路径查询 `pg_roles.rolcanlogin` | `claude_reader` 存在且为 `false` |
| PostgreSQL MCP 登录状态 | 检查 tracked `.claude/mcp-config.json` | 无 PostgreSQL entry；无受支持 LOGIN identity |
| Docker 可用 | `docker ps` | 容器列表 |
| Docker Compose 可用 | `docker-compose ps` | 服务列表 |

## MCP 工具功能

### 1. Filesystem MCP

- **功能**: 读写项目文件
- **范围**: 仅限 `/home/xupeng/projects/FootballPrediction`
- **命令**: 自动通过当前 MCP 客户端调用

### 2. PostgreSQL MCP（历史 / 已退役登录）

当前状态：

- `CURRENT_ROLE_TYPE=RETAINED_ACL_ROLE`
- `CURRENT_LOGIN_STATE=NOLOGIN`
- `CURRENT_DIRECT_LOGIN_SUPPORT=NO`
- `CURRENT_POSTGRESQL_MCP_LOGIN_IDENTITY=NOT_ESTABLISHED`
- `CURRENT_TRACKED_POSTGRES_MCP_ENTRY=ABSENT`

`claude_reader` 曾是 development PostgreSQL MCP 的登录身份；该登录工作流现已退役。
role 仍保留既有只读 ACL，供 ownership/ACL 语义延续，但 `NOLOGIN` 明确禁止它建立
direct session。当前 tracked `.claude/mcp-config.json` 也没有 PostgreSQL MCP entry。

PostgreSQL MCP package 或历史实现仍可存在于依赖和历史说明中，这不代表仓库当前已经建立
可用的 PostgreSQL MCP 登录身份。恢复该能力需要未来独立的身份、secret sink 与安全授权，
不得复用 `claude_reader` 或自行指定替代 role。

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
| 保留 ACL role 的权限漂移 | 潜在访问面扩大 | 保持 `NOLOGIN`，并独立审计 ACL 变更 |
| Docker 命令注入 | 容器被破坏 | 黑名单过滤危险命令 |
| Filesystem 访问越界 | 敏感文件泄露 | 限制项目目录范围 |
| MCP 服务资源占用 | 系统性能下降 | 设置资源限制 |

## 故障排查

### MCP 服务未加载

```bash
# 只验证 repository MCP reference 的 JSON 结构，不打印配置值
python3 -m json.tool .claude/mcp-config.json >/dev/null

# Codex CLI 的本机配置可能含环境 secret；不要整文件打印
# 仅通过受支持的宿主工具检查必要的结构 metadata

# 检查路径是否正确
ls -la mcp_servers/

# 修改 .claude/mcp-config.json、~/.codex/config.toml
# 或 mcp_servers/*.py 后，重启对应客户端
```

### 历史 PostgreSQL MCP 配置问题

```bash
# 检查数据库是否运行
docker-compose ps db

```

当前没有受支持的 PostgreSQL MCP LOGIN identity。不要通过重新创建 `claude_reader`、恢复
`LOGIN` 或添加 password 来排查连接问题。若只需确认 retirement 状态，通过 development
管理员 metadata 路径检查该 role 存在且 `rolcanlogin=false`；需要恢复 PostgreSQL MCP
能力时，应启动独立的安全设计与授权流程。

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
