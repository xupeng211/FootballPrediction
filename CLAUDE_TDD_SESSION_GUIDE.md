# Claude Code TDD分享会使用指南

## 📋 概述

本项目已经准备好了完整的TDD分享会材料，主题为"Mock与Stub在测试中的艺术"。Claude Code可以通过本指南了解并使用这些材料。

## 📁 分享会材料位置

### 核心文件
- **主演示文稿**：`docs/tdd_presentations/first_tdd_sharing_session.md`
- **实战代码**：`docs/tdd_presentations/workshop_solutions.py`
- **组织清单**：`docs/tdd_presentations/organizing_checklist.md`
- **会议通知**：`ANNOUNCEMENT_First_TDD_Sharing_Session.md`

### 执行工具
- **执行助手**：`scripts/run_tdd_sharing_session.py`
- **准备检查**：`scripts/check_tdd_session_prep.py`
- **启动脚本**：`scripts/launch_tdd_sharing_session.sh`

## 🎯 Claude Code使用方式

### 1. 查看分享会内容

当用户询问TDD分享会时，Claude Code可以：

```bash
# 查看主演示文稿
Read the file: docs/tdd_presentations/first_tdd_sharing_session.md

# 查看实战代码
Read the file: docs/tdd_presentations/workshop_solutions.py
```

### 2. 解释概念

用户询问Mock和Stub的区别时：

```markdown
Mock vs Stub的核心区别：

1. **Stub（存根）**
   - 用途：提供预设的测试数据
   - 特点：只返回固定值，不验证交互
   - 示例：为API调用提供假数据

2. **Mock（模拟）**
   - 用途：验证行为和交互
   - 特点：记录调用历史，可以验证调用次数和参数
   - 示例：验证邮件发送功能是否被正确调用
```

### 3. 提供代码示例

从 `workshop_solutions.py` 中提取相关示例：

```python
# Stub示例
class WeatherApiClientStub:
    def __init__(self, temperature):
        self.temperature = temperature

    def get_weather(self, city):
        return {"temperature": self.temperature}

# Mock示例
from unittest.mock import Mock

email_service = Mock()
email_service.send_welcome_email.assert_called_once()
```

### 4. 运行和验证测试

```bash
# 运行所有示例代码
Run command: python -m pytest docs/tdd_presentations/workshop_solutions.py -v

# 检查准备状态
Run command: python scripts/check_tdd_session_prep.py
```

### 5. 组织分享会

```bash
# 使用执行助手
Run command: python scripts/run_tdd_sharing_session.py

# 一键启动准备
Run command: ./scripts/launch_tdd_sharing_session.sh
```

## 💬 常见用户问题及回答

### Q: 什么是Mock？什么是Stub？
A: 参见 `first_tdd_sharing_session.md` 的"核心概念"部分，提供清晰的定义和对比。

### Q: 如何测试外部依赖？
A: 查看 `workshop_solutions.py` 中的实战案例，包括：
- 天气预报服务测试
- 文件上传功能测试
- 邮件发送服务测试

### Q: 什么时候应该用Mock而不是Stub？
A: 参考演示文稿中的"选择合适的测试替身"部分，提供决策指南。

### Q: 如何组织这次分享会？
A: 使用 `organizing_checklist.md` 作为检查清单，确保所有准备步骤完成。

## 🔧 Claude Code行动指南

### 当用户说"准备TDD分享会"时：

1. 检查当前准备状态
   ```bash
   Run command: python scripts/check_tdd_session_prep.py
   ```

2. 如果未准备好，按照缺失项进行准备

3. 如果已准备好，提供下一步行动：
   - 发送会议通知
   - 使用执行助手
   - 安排会议时间

### 当用户说"解释Mock和Stub"时：

1. 从演示文稿提取核心概念
2. 提供简单易懂的示例
3. 说明使用场景和最佳实践

### 当用户说"运行分享会"时：

1. 提供执行步骤
2. 运行执行助手协助主持
3. 提供计时和议程管理

## 📊 关键信息摘要

### 分享会主题
- **主题**：Mock与Stub在测试中的艺术
- **时长**：45分钟
- **参与人数**：建议15-20人
- **准备状态**：✅ 已完成

### 学习目标
1. 理解Mock和Stub的区别
2. 掌握在Python中使用Mock
3. 学会测试外部依赖
4. 提升测试可维护性

### 核心材料
- 9个测试示例
- 完整的演示文稿
- 组织和执行工具
- 反馈收集机制

## 🚀 快速开始

要让Claude Code开始使用这些材料：

1. 用户可以说："查看TDD分享会准备情况"
2. Claude Code运行准备检查脚本
3. 根据结果提供下一步行动

## 📝 持续改进

分享会后，Claude Code可以：
- 分析反馈数据
- 改进材料质量
- 准备下一次分享会
- 跟踪行动项完成情况

---

*本指南帮助Claude Code更好地理解和利用TDD分享会材料，为团队提供优质的支持。*
