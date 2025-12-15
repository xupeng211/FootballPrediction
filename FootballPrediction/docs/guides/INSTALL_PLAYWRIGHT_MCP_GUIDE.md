# 🚀 Ubuntu系统安装Playwright MCP详细指南

## ✅ 系统状态检查结果

- **Node.js**: v22.19.0 ✅
- **npm**: v10.9.3 ✅
- **操作系统**: Ubuntu ✅
- **Claude Code配置**: 需要初始化 ⚠️

---

## 📋 安装步骤

### 第一步：安装Claude Code CLI (如果还没有安装)

```bash
# 方法1: 通过npm安装
npm install -g @anthropic-ai/claude-code

# 方法2: 通过下载安装包
wget https://github.com/anthropics/claude-code/releases/latest/download/claude-code-linux-x64
chmod +x claude-code-linux-x64
sudo mv claude-code-linux-x64 /usr/local/bin/claude-code
```

### 第二步：初始化Claude Code配置

```bash
# 创建配置目录
mkdir -p ~/.claude-code

# 创建配置文件
touch ~/.claude-code/claude_desktop_config.json
```

### 第三步：安装Playwright MCP服务器

```bash
# 创建MCP服务器目录
mkdir -p ~/.claude-code/servers

# 安装Playwright MCP服务器
cd ~/.claude-code/servers
npm init -y
npm install @modelcontextprotocol/server-playwright

# 或者全局安装
npm install -g @modelcontextprotocol/server-playwright
```

### 第四步：配置Claude Code

编辑配置文件：
```bash
nano ~/.claude-code/claude_desktop_config.json
```

添加以下内容：
```json
{
  "mcpServers": {
    "playwright": {
      "command": "node",
      "args": ["~/.claude-code/servers/node_modules/@modelcontextprotocol/server-playwright/dist/index.js"]
    }
  }
}
```

### 第五步：安装Playwright浏览器

```bash
# 进入MCP服务器目录
cd ~/.claude-code/servers

# 安装Playwright浏览器
npx playwright install

# 安装系统依赖 (Ubuntu特有)
sudo npx playwright install-deps
```

### 第六步：验证安装

```bash
# 检查Claude Code版本
claude-code --version

# 测试MCP连接
claude-code list-mcps

# 验证Playwright功能
node ~/.claude-code/servers/node_modules/@modelcontextprotocol/server-playwright/dist/index.js --help
```

---

## 🔧 详细操作命令

### 完整安装命令序列

```bash
# 1. 安装Claude Code CLI (如果需要)
npm install -g @anthropic-ai/claude-code

# 2. 创建配置目录
mkdir -p ~/.claude-code
mkdir -p ~/.claude-code/servers

# 3. 初始化npm项目
cd ~/.claude-code/servers
npm init -y

# 4. 安装Playwright MCP
npm install @modelcontextprotocol/server-playwright

# 5. 创建配置文件
cat > ~/.claude-code/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "playwright": {
      "command": "node",
      "args": ["~/.claude-code/servers/node_modules/@modelcontextprotocol/server-playwright/dist/index.js"]
    }
  }
}
EOF

# 6. 安装Playwright浏览器
npx playwright install

# 7. 安装系统依赖 (Ubuntu)
sudo npx playwright install-deps

# 8. 验证安装
claude-code --version
```

---

## 🔍 故障排除

### 常见问题及解决方案

#### 问题1: "claude-code: command not found"
```bash
# 解决方案: 重新安装或检查PATH
which claude-code
echo $PATH | grep -o claude-code
```

#### 问题2: "权限被拒绝"
```bash
# 解决方案: 修复权限
chmod +x ~/.claude-code/servers/node_modules/@modelcontextprotocol/server-playwright/dist/index.js
```

#### 问题3: "Playwright浏览器安装失败"
```bash
# 解决方案: 手动安装
cd ~/.claude-code/servers
PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chrome firefox
```

#### 问题4: "MCP服务器连接失败"
```bash
# 解决方案: 检查配置文件
cat ~/.claude-code/claude_desktop_config.json
claude-code list-mcps
```

---

## 🎯 验证成功标志

安装成功后，您应该看到：

### ✅ 成功指标
- [ ] `claude-code --version` 显示版本信息
- [ ] `claude-code list-mcps` 显示 "playwright" 服务器
- [ ] Playwright浏览器安装完成
- [ ] 系统依赖安装成功

### 🎊 安装完成后测试

```bash
# 重启Claude Code
claude-code restart

# 测试MCP功能
claude-code test mcp playwright
```

---

## 🚀 安装后的第一步

安装成功后，我将能够：

1. **直接创建GitHub Issue #99**
2. **自动更新项目进度**
3. **智能管理项目标签**
4. **生成项目报告**

### 首次操作预览

安装完成后，我就可以执行：
```javascript
// 我将能够直接运行这样的代码
"创建GitHub Issue #99，标题为测试覆盖率提升计划"
// 自动访问GitHub，填写表单，添加标签，提交Issue
```

---

## 📞 获取帮助

如果遇到问题：

1. **查看日志**: `claude-code logs`
2. **重新安装**: 删除 `~/.claude-code` 目录重新开始
3. **检查网络**: 确保能访问npm和GitHub
4. **系统更新**: `sudo apt update && sudo apt upgrade`

---

**准备好开始安装了吗？按照这些步骤操作，我们就能开启全新的自动化协作模式！** 🚀
