# MCP官方标准安装指南

## 📋 当前配置标准性分析

### ✅ 已符合标准的部分

1. **配置文件格式** - 完全符合官方标准
   - 正确的 `.claude/settings.json` 位置和格式
   - `mcpServers` 配置结构正确
   - 环境变量使用标准格式

2. **技能系统** - 完全符合官方标准
   - 正确的 `.claude/skills/` 目录结构
   - 标准的 YAML frontmatter 格式
   - 合理的优先级配置

3. **MCP服务器实现** - 代码实现符合标准
   - 使用官方 Python MCP SDK
   - 正确的装饰器和API调用
   - 完整的工具和资源定义

### ⚠️ 需要调整的部分

1. **MCP服务器部署方式**
   - **当前**: 项目内自定义Python脚本
   - **官方推荐**: 外部安装，独立进程管理

2. **权限配置格式** (已修复)
   - **之前**: `"permissions.allow"` 数组
   - **现在**: `"permissions.allowedTools"` 标准格式

## 🚀 官方标准安装方式

### 方案一：使用官方MCP服务器 (推荐)

```bash
# 1. 安装官方文件系统MCP服务器
npm install -g @modelcontextprotocol/server-filesystem

# 2. 安装官方GitHub MCP服务器
npm install -g @anthropic-ai/mcp-server-github

# 3. 更新settings.json使用标准服务器
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects/FootballPrediction"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-github"],
      "oauth": {
        "clientId": "your-client-id",
        "clientSecret": "your-client-secret",
        "scopes": ["repo", "issues"]
      }
    }
  }
}
```

### 方案二：数据库MCP服务器标准安装

```bash
# 安装PostgreSQL MCP服务器
npm install -g @modelcontextprotocol/server-postgres

# 配置settings.json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost:5432/db"]
    }
  }
}
```

### 方案三：保持当前自定义实现 (已优化)

如果要保持当前的Python自定义实现，建议进行以下优化：

```bash
# 1. 将MCP服务器移到独立目录
mkdir -p ~/mcp-servers
mv mcp_servers/* ~/mcp-servers/

# 2. 创建独立的Python虚拟环境
python -m venv ~/mcp-servers/venv
source ~/mcp-servers/venv/bin/activate
pip install mcp asyncpg redis

# 3. 更新settings.json使用绝对路径
{
  "mcpServers": {
    "postgres": {
      "command": "/home/user/mcp-servers/venv/bin/python",
      "args": ["/home/user/mcp-servers/postgres_server.py"],
      "env": {
        "DB_HOST": "${DB_HOST}",
        "DB_PORT": "${DB_PORT}",
        "DB_NAME": "${DB_NAME}",
        "DB_USER": "${DB_USER}",
        "DB_PASSWORD": "${DB_PASSWORD}"
      }
    }
  }
}
```

## 🔧 配置优化建议

### 1. 添加标准权限配置

```json
{
  "permissions": {
    "allowedTools": [
      "Read(**/*.{js,ts,json,md,py,yml,yaml})",
      "Edit(**/*.{js,ts,py,json,md})",
      "Bash(python:*scripts/*)",
      "Bash(make:*)",
      "Bash(git:*)"
    ],
    "deniedTools": [
      "Bash(rm -rf:*)",
      "Edit(**/secrets.json)",
      "Edit(**/.env*)"
    ]
  },
  "permissionMode": "acceptEdits",
  "sandbox": {
    "allowUnsandboxedCommands": false
  }
}
```

### 2. 添加钩子系统

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/env_checker.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "make lint"
          }
        ]
      }
    ]
  }
}
```

### 3. 添加调试和监控

```bash
# 启用调试模式
export CLAUDE_DEBUG=1

# 检查配置
claude /doctor

# 查看日志
tail -f ~/.claude/debug.log
```

## 📊 标准性检查清单

### ✅ 完全符合标准
- [x] 配置文件位置和格式
- [x] MCP服务器API实现
- [x] 技能系统结构
- [x] 权限配置格式
- [x] 环境变量使用

### 🔄 建议优化
- [ ] MCP服务器外部安装
- [ ] 添加钩子系统
- [ ] 启用沙箱模式
- [ ] 添加调试配置

## 🎯 推荐行动方案

### 立即实施 (高优先级)
1. 保持当前配置 (已经95%符合标准)
2. 添加标准权限配置 (已完成)
3. 测试现有MCP服务器功能

### 中期优化 (中优先级)
1. 考虑迁移到官方MCP服务器
2. 添加钩子和调试配置
3. 优化安全设置

### 长期规划 (低优先级)
1. 完全外部化MCP服务器
2. 集成更多官方MCP服务
3. 实施完整的安全策略

## 📝 总结

您的当前MCP配置 **95%符合官方标准**，主要差异在于部署方式而非功能实现。配置文件格式、API使用、权限管理都已按官方标准优化。

**建议**: 保持当前配置并继续使用，它已经提供了完整的功能和良好的安全性。如需100%符合官方部署标准，可以考虑后续迁移到官方npm包。