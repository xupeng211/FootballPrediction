# MCP集成指南

## 概述

本项目已成功集成Model Context Protocol (MCP)和Claude Code技能系统，提供强大的AI编程辅助能力。

## 配置总览

### MCP服务器 (3个)
1. **PostgreSQL MCP服务器** (`mcp_servers/postgres_server.py`)
   - 数据库查询和表结构访问
   - 环境变量: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

2. **Redis MCP服务器** (`mcp_servers/redis_server.py`)
   - 缓存管理和键值操作
   - 环境变量: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`

3. **文件系统MCP服务器** (`mcp_servers/filesystem_server.py`)
   - 项目文件访问和Git集成
   - 安全边界限制在项目根目录内

### Claude Code技能 (5个)
1. **football-prediction** - 足球预测核心业务技能
2. **data-collection** - 数据收集技能
3. **report-generation** - 报告生成技能
4. **performance-monitoring** - 性能监控技能
5. **database-operations** - 数据库操作技能

## 管理工具

### MCP管理脚本
```bash
# 查看所有MCP服务器状态
./scripts/mcp_manager.sh status

# 启动所有MCP服务器
./scripts/mcp_manager.sh start

# 启动单个服务器
./scripts/mcp_manager.sh start_single postgres

# 查看日志
./scripts/mcp_manager.sh logs

# 测试连接
./scripts/mcp_manager.sh test
```

### 配置验证脚本
```bash
# 验证MCP配置
python scripts/simple_mcp_test.py
```

## 使用方法

### 1. 启动服务
```bash
# 启动数据库和Redis服务
docker-compose up -d db redis

# 确保服务正常运行
docker-compose ps
```

### 2. 重启Claude Code
重启Claude Code以加载新的MCP配置和技能。

### 3. 开始使用
现在你可以：
- 使用数据库查询工具直接访问PostgreSQL
- 管理Redis缓存和键值存储
- 通过MCP安全地访问项目文件
- 利用专业技能获得针对性的开发建议

## 技能自动加载

当进行特定任务时，Claude会自动加载相关技能：

- **足球预测相关任务**: 自动加载`football-prediction`技能
- **数据收集任务**: 自动加载`data-collection`技能
- **报告生成任务**: 自动加载`report-generation`技能
- **性能监控任务**: 自动加载`performance-monitoring`技能
- **数据库操作任务**: 自动加载`database-operations`技能

## MCP工具示例

### PostgreSQL工具
- `execute_sql` - 执行SQL查询
- `get_table_info` - 获取表结构
- `get_schema_info` - 获取数据库schema
- `check_connection` - 测试数据库连接

### Redis工具
- `redis_get` - 获取键值
- `redis_set` - 设置键值
- `redis_delete` - 删除键
- `redis_search` - 搜索键
- `redis_info` - 获取Redis信息

### 文件系统工具
- `read_file` - 读取文件
- `write_file` - 写入文件
- `list_directory` - 列出目录
- `search_files` - 搜索文件
- `git_status` - Git状态
- `git_diff` - Git差异

## 安全特性

### 文件系统安全
- 所有文件操作限制在项目根目录内
- 路径遍历攻击防护
- Git集成安全访问

### 数据库安全
- 使用环境变量管理敏感配置
- 连接池和超时限制
- 查询执行沙箱

## 故障排除

### 常见问题

1. **MCP服务器无法启动**
   ```bash
   # 检查错误日志
   ./scripts/mcp_manager.sh logs

   # 验证配置
   python scripts/simple_mcp_test.py
   ```

2. **数据库连接失败**
   ```bash
   # 启动数据库服务
   docker-compose up -d db redis

   # 检查连接
   ./scripts/mcp_manager.sh test
   ```

3. **技能未自动加载**
   - 重启Claude Code
   - 检查`.claude/settings.json`配置

### 日志位置
- MCP服务器日志: `logs/{server}_server.log`
- Claude配置: `.claude/settings.json`
- 技能文件: `.claude/skills/{skill}/SKILL.md`

## 更新和维护

### 添加新的MCP服务器
1. 在`mcp_servers/`目录创建新服务器文件
2. 更新`.claude/settings.json`中的`mcpServers`配置
3. 更新`scripts/mcp_manager.sh`中的服务器列表

### 添加新技能
1. 在`.claude/skills/`目录创建技能文件夹
2. 创建`SKILL.md`文件，包含YAML frontmatter
3. 更新`.claude/settings.json`中的技能优先级

## 版本信息

- **MCP版本**: 1.24.0
- **asyncpg**: 0.31.0 (PostgreSQL)
- **redis**: 7.1.0 (Redis)
- **配置日期**: 2024-12-18
- **兼容性**: Claude Code最新版本

---

**重要提醒**: 此配置已通过验证测试，可以安全使用。确保在生产环境中适当配置环境变量和网络安全。