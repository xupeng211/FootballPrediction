# MCP和技能使用指南

## 🚀 快速开始

### 1. 启动环境
```bash
# 启动必要的服务
docker-compose up -d db redis

# 验证服务状态
docker-compose ps

# 检查MCP配置
python scripts/simple_mcp_test.py
```

### 2. 重启Claude Code
重启Claude Code以加载新的MCP配置和技能。

## 💡 技能自动加载

当您进行特定任务时，Claude会自动加载相关技能：

- **足球预测任务** → `football-prediction` 技能
- **数据收集任务** → `data-collection` 技能
- **报告生成任务** → `report-generation` 技能
- **性能监控任务** → `performance-monitoring` 技能
- **数据库操作任务** → `database-operations` 技能

## 🛠️ MCP工具使用方法

### PostgreSQL数据库工具

#### 执行SQL查询
```python
# 自然语言请求
"帮我查询最近10场比赛的预测结果"
"查看数据库中有哪些表"
"分析team_stats表的记录数量"
```

#### 获取表结构
```python
# 自然语言请求
"显示matches表的结构"
"查看predictions表的列信息"
"分析数据库schema"
```

#### 测试数据库连接
```python
# 自然语言请求
"检查数据库连接是否正常"
"测试PostgreSQL连接状态"
```

### Redis缓存工具

#### 缓存操作
```python
# 自然语言请求
"查看Redis中所有预测相关的键"
"清除所有缓存数据"
"检查Redis内存使用情况"
```

#### 键值管理
```python
# 自然语言请求
"获取key为prediction:123的值"
"设置缓存键match:456，值为processed"
"搜索所有以feature:开头的键"
```

### 文件系统工具

#### 文件操作
```python
# 自然语言请求
"读取src/config.py文件的内容"
"在tests目录创建新的测试文件"
"搜索所有包含'xgboost'的Python文件"
```

#### Git操作
```python
# 自然语言请求
"查看当前Git状态"
"显示最近的修改内容"
"检查有哪些文件未提交"
```

## 🎯 实际使用场景

### 场景1: 足球预测分析
```python
# 用户输入
"帮我分析一下曼联对阿森纳的比赛预测"

# Claude自动行为：
# 1. 加载football-prediction技能
# 2. 使用PostgreSQL工具查询历史数据
# 3. 使用Redis工具检查缓存
# 4. 返回专业分析结果
```

### 场景2: 数据收集任务
```python
# 用户输入
"收集最近一周的英超比赛数据"

# Claude自动行为：
# 1. 加载data-collection技能
# 2. 使用文件系统工具创建数据收集脚本
# 3. 使用PostgreSQL工具存储数据
# 4. 提供数据质量报告
```

### 场景3: 性能监控
```python
# 用户输入
"检查系统性能，查看预测准确率"

# Claude自动行为：
# 1. 加载performance-monitoring技能
# 2. 使用PostgreSQL工具查询准确率统计
# 3. 使用Redis工具检查缓存命中率
# 4. 生成性能报告
```

### 场景4: 数据库优化
```python
# 用户输入
"优化数据库查询性能"

# Claude自动行为：
# 1. 加载database-operations技能
# 2. 使用PostgreSQL工具分析慢查询
# 3. 提供索引优化建议
# 4. 生成优化脚本
```

## 💬 对话示例

### 示例1: 预测分析
```
用户: 我想分析切尔西对利物浦的比赛预测

Claude: 🏟️ 正在分析切尔西 vs 利物浦的比赛预测...

📊 使用技能: football-prediction
🔧 使用工具: PostgreSQL数据库查询

📈 历史交锋数据:
- 近5次交锋: 切尔西 1胜2平2负
- 主场优势: 切尔西主场胜率45%
- 进球统计: 平均总进球2.4个

🎯 预测结果:
- 主胜概率: 42%
- 平局概率: 28%
- 客胜概率: 30%

💡 建议: 考虑平局或客胜投注策略
```

### 示例2: 系统监控
```
用户: 系统最近运行怎么样？

Claude: 📊 正在检查系统运行状态...

🔧 使用技能: performance-monitoring
🔧 使用工具: Redis缓存查询 + PostgreSQL统计查询

✅ 系统状态良好:
- 预测准确率: 67.2% (目标65%)
- 缓存命中率: 85% (优秀)
- API响应时间: 89ms (目标<100ms)
- 数据库连接: 正常

⚠️ 需要关注:
- 内存使用率: 78% (建议优化)
- 某些查询较慢，建议添加索引
```

### 示例3: 代码开发
```
用户: 我需要添加新的特征工程模块

Claude: 🔧 正在为您创建特征工程模块...

🛠️ 使用技能: machine-learning-engineering
🔧 使用工具: 文件系统操作

📁 已创建文件:
- src/ml/features/new_feature_engineer.py
- tests/unit/test_new_features.py
- examples/feature_usage.py

✅ 特征模块包含:
- 5个新特征提取函数
- 完整的单元测试
- 性能优化代码
- 详细文档说明

💡 建议: 运行 `python scripts/process_offline_features_full.py` 来测试新特征
```

## 🎮 交互技巧

### 1. 明确任务类型
```
❌ 模糊: "帮我处理一下数据"
✅ 明确: "收集昨天所有英超比赛的实时数据并存储到数据库"
```

### 2. 利用技能专长
```
❌ 一般: "写个测试文件"
✅ 专业: "为predictions API创建完整的单元测试，包含边界情况"
```

### 3. 指定工具使用
```
❌ 被动: "看看有什么问题"
✅ 主动: "用PostgreSQL工具检查最近24小时的错误日志"
```

### 4. 结合多种技能
```
✅ 复合任务: "分析模型性能下降原因，生成优化报告，并创建监控告警"
```

## 🔧 高级使用

### 1. 自定义权限
如果需要更多操作权限，可以修改 `.claude/settings.json`:
```json
{
  "permissions": {
    "allowedTools": [
      "Bash(python:*)",  // 允许所有Python命令
      "Edit(**/*)"        // 允许编辑所有文件
    ]
  }
}
```

### 2. 添加钩子
```json
{
  "hooks": {
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

### 3. 调试模式
```bash
# 启用调试
export CLAUDE_DEBUG=1

# 查看详细日志
tail -f ~/.claude/debug.log
```

## ⚡ 最佳实践

### 1. 任务描述
- 🎯 **具体明确**: 避免模糊描述
- 📋 **分步骤**: 复杂任务分解为小步骤
- 🎪 **上下文**: 提供相关背景信息

### 2. 技能利用
- 🏃 **让技能自动加载**: 不要手动指定技能
- 🎯 **信任专业判断**: 技能会提供最佳方案
- 📚 **学习技能建议**: 技能给出的建议都经过优化

### 3. 工具协同
- 🔗 **工具组合**: 多个MCP工具协同工作
- 💾 **数据流向**: 理解数据在工具间的流动
- 🛡️ **安全边界**: 注意权限和安全限制

## 🆘 故障排除

### 常见问题
1. **MCP服务器未响应**
   ```bash
   # 检查状态
   ./scripts/mcp_manager.sh status

   # 重启服务
   ./scripts/mcp_manager.sh restart
   ```

2. **技能未加载**
   - 重启Claude Code
   - 检查 `.claude/settings.json` 格式

3. **权限被拒绝**
   - 检查 `permissions` 配置
   - 确认操作在允许范围内

### 获取帮助
- 使用 `/help` 查看可用命令
- 查看详细日志: `./scripts/mcp_manager.sh logs`
- 运行诊断: `python scripts/simple_mcp_test.py`

---

## 🎉 开始使用

现在您可以：

1. 🏗️ **开发功能**: 利用专业技能加速开发
2. 📊 **数据分析**: 通过MCP工具直接操作数据库
3. 🔍 **系统监控**: 实时检查系统状态和性能
4. 🚀 **自动化**: 让AI处理重复性任务

祝您使用愉快！🎊