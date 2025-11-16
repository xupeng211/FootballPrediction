# 📋 GitHub Issues 执行指南

## 🎯 **指南概述**

本指南为所有开发者（包括AI编程工具）提供详细的Issue执行流程，确保每个任务都能高质量、高效率地完成。

---

## 🔄 **标准执行流程**

### **Phase 1: 任务准备 (10分钟)**

#### **1.1 Issue 分析**
```bash
# 获取Issue信息
gh issue view <issue-number>

# 查看相关标签和里程碑
gh issue list --label optimization --state open
```

#### **1.2 环境准备**
```bash
# 1. 更新代码
git pull origin main

# 2. 创建功能分支
git checkout -b feat/<issue-short-name>

# 3. 环境检查
make env-check

# 4. 依赖安装
make install
```

#### **1.3 工具准备**
```bash
# 确保所有工具可用
which ruff black pytest make
make help  # 查看可用命令
```

### **Phase 2: 开发执行 (主要时间)**

#### **2.1 代码开发规范**
```python
# 严格遵循CLAUDE.md规范
import os, sys, json  # ✅ 逗号分隔
from typing import Dict, List  # ✅ 类型注解

def process_data(data: Dict) -> Dict:  # ✅ 冒号结束
    """处理数据的函数"""  # ✅ 完整docstring
    if not data:  # ✅ 冒号结束
        return {}

    result = {}  # ✅ 双引号
    for key, value in data.items():  # ✅ 冒号结束
        result[key] = value.strip() if isinstance(value, str) else value

    return result
```

#### **2.2 质量检查循环**
```bash
# 开发过程中定期运行
make fix-code          # 自动修复格式问题
ruff check src/ --fix   # 修复其他问题
make test.unit         # 运行单元测试
make coverage          # 检查覆盖率
```

#### **2.3 测试开发**
```python
# 测试文件命名规范
# tests/unit/services/test_user_management_service.py

import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestUserManagementService:
    """用户管理服务测试类"""

    @pytest.mark.unit
    @pytest.mark.services
    async def test_create_user_success(self, user_service, mock_user_repository):
        """测试成功创建用户"""
        # 准备数据
        mock_user_repository.get_by_email.return_value = None
        mock_user_repository.create.return_value = sample_user

        # 执行测试
        result = await user_service.create_user(request)

        # 验证结果
        assert isinstance(result, UserResponse)
        assert result.email == "test@example.com"
```

### **Phase 3: 验证测试 (30分钟)**

#### **3.1 质量验证**
```bash
# 完整质量检查
make check-quality

# 单独检查各项
ruff check src/ --quiet
black --check src/ tests/
mypy src/ --ignore-missing-imports
bandit -r src/ -q
pip-audit --quiet
```

#### **3.2 测试验证**
```bash
# 运行相关测试
pytest tests/unit/services/test_user_management_service.py -v

# 检查覆盖率
pytest tests/unit/services/test_user_management_service.py \
  --cov=src/services/user_management_service \
  --cov-report=term-missing

# 运行性能测试（如适用）
python3 scripts/performance_benchmark.py
```

#### **3.3 集成验证**
```bash
# 启动应用测试
python -m uvicorn src.main:app --reload &
APP_PID=$!

# 健康检查
curl -f http://localhost:8000/health

# API测试
curl -X POST http://localhost:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"Test123!"}'

# 清理
kill $APP_PID
```

### **Phase 4: 代码提交 (15分钟)**

#### **4.1 代码审查**
```bash
# 查看修改内容
git status
git diff --staged

# 自我检查清单
echo "检查项目:"
echo "✅ 代码质量检查通过"
echo "✅ 测试覆盖率达标"
echo "✅ 功能正常工作"
echo "✅ 文档已更新"
echo "✅ 无安全漏洞"
```

#### **4.2 提交代码**
```bash
# 添加文件
git add .

# 生成提交信息
cat > commit_message.txt << EOF
feat: 实现用户管理性能优化

- 添加Redis缓存层，提升查询性能50%
- 优化数据库索引，减少查询时间
- 实现缓存失效策略，保证数据一致性
- 添加性能监控和基准测试

影响: 用户管理模块性能显著提升
测试: 所有测试通过，覆盖率35%

🤖 Generated with [Claude Code](https://claude.ai/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF

# 提交
git commit -F commit_message.txt

# 推送
git push origin feat/<issue-short-name>
```

#### **4.3 创建Pull Request**
```bash
# 使用GitHub CLI创建PR
gh pr create --title "feat: 实现用户管理性能优化" \
  --body "This PR implements performance optimizations for the user management module." \
  --assignee @your-username \
  --label optimization,performance,caching
```

---

## 🛠️ **具体任务执行示例**

### **示例1: 代码质量修复任务**
```markdown
## Issue: [OPT] 修复Ruff检查的15个质量问题

### 执行步骤:

#### Step 1: 运行质量检查
```bash
ruff check src/ --output-format=json > issues.json
```

#### Step 2: 分析问题类型
```bash
# 查看问题统计
cat issues.json | jq '.[].code' | sort | uniq -c
```

#### Step 3: 自动修复
```bash
ruff check src/ --fix
```

#### Step 4: 手动修复剩余问题
```python
# 典型修复：异常处理
# 修复前：
except Exception as e:
    raise HTTPException(detail=str(e))

# 修复后：
except Exception as e:
    raise HTTPException(detail=str(e)) from e
```

#### Step 5: 验证修复
```bash
ruff check src/ --quiet
```
```

### **示例2: 测试覆盖率提升任务**
```markdown
## Issue: [OPT] 提升用户管理模块测试覆盖率至30%

### 执行步骤:

#### Step 1: 分析当前覆盖率
```bash
pytest tests/unit/services/test_user_management_service.py \
  --cov=src/services/user_management_service \
  --cov-report=html
```

#### Step 2: 识别未覆盖代码
```python
# 使用覆盖率优化器
python3 scripts/coverage_optimizer.py

# 输出建议：
# - 添加函数 validate_create_request 的测试
# - 添加第45行异常情况的测试
# - 添加返回值验证的测试
```

#### Step 3: 编写缺失测试
```python
@pytest.mark.unit
@pytest.mark.services
async def test_validate_create_request_invalid_email(self, user_service):
    """测试创建用户时邮箱无效"""
    request = UserCreateRequest(
        username="testuser",
        email="invalid-email",  # 无效邮箱
        password="SecurePass123!",
        full_name="Test User"
    )

    with pytest.raises(ValueError, match="邮箱格式无效"):
        user_service._validate_create_request(request)
```

#### Step 4: 验证覆盖率提升
```bash
pytest tests/unit/services/test_user_management_service.py \
  --cov=src/services/user_management_service \
  --cov-report=term-missing
```
```

---

## 🚨 **常见问题和解决方案**

### **问题1: 测试失败**
```bash
# 诊断步骤
pytest tests/unit/services/test_user_management_service.py -v --tb=short

# 常见解决方案
# 1. 模拟对象配置错误
mock_user_repository.get_by_email.return_value = None

# 2. 异步测试缺少await
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()  # 别忘了await

# 3. 导入路径问题
from src.services.user_management_service import UserManagementService
```

### **问题2: 代码质量检查失败**
```bash
# 诊断步骤
ruff check src/ --output-format=long

# 常见修复
# 1. 异常处理链
raise HTTPException(detail=str(e)) from e

# 2. 未使用导入
# 删除或注释掉未使用的import

# 3. 类型注解缺失
def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    # 添加类型注解
```

### **问题3: 性能测试失败**
```bash
# 诊断步骤
python3 scripts/performance_benchmark.py

# 优化建议
# 1. 添加缓存
@lru_cache(maxsize=128)
def expensive_function():
    pass

# 2. 优化数据库查询
# 添加索引，使用select_related/prefetch_related

# 3. 异步优化
# 确保所有I/O操作都是异步的
```

---

## 📊 **进度追踪工具**

### **每日进度检查脚本**
```bash
# daily_progress.sh
#!/bin/bash

echo "📊 $(date) - Issues进度检查"

# 获取开放的优化Issues
OPEN_ISSUES=$(gh issue list --label optimization --state open --limit 20 | wc -l)
echo "🔄 进行中的优化Issues: $OPEN_ISSUES"

# 获取本周完成的Issues
COMPLETED_THIS_WEEK=$(gh issue list --label optimization --closed --since="1 week ago" | wc -l)
echo "✅ 本周完成的Issues: $COMPLETED_THIS_WEEK"

# 检查代码质量
if ruff check src/ --quiet; then
    echo "✅ 代码质量检查通过"
else
    echo "❌ 代码质量有问题"
fi

# 检查测试状态
if pytest tests/unit/services/test_user_management_service.py -q --tb=no > /dev/null 2>&1; then
    echo "✅ 核心测试通过"
else
    echo "❌ 核心测试失败"
fi
```

### **Issue进度追踪器**
```python
# issue_tracker.py
import subprocess
import json
from datetime import datetime

class IssueTracker:
    def __init__(self):
        self.issues = self.get_issues()

    def get_issues(self):
        """获取所有优化Issues"""
        result = subprocess.run([
            "gh", "issue", "list",
            "--label", "optimization",
            "--state", "all",
            "--limit", "100",
            "--json", "title,state,labels,assignees"
        ], capture_output=True, text=True)

        return json.loads(result.stdout)

    def get_progress_summary(self):
        """获取进度摘要"""
        total = len(self.issues)
        open_issues = [i for i in self.issues if i["state"] == "OPEN"]
        closed_issues = [i for i in self.issues if i["state"] == "CLOSED"]

        # 按标签统计
        by_label = {}
        for issue in self.issues:
            for label in issue.get("labels", []):
                if "optimization" not in label:
                    by_label[label] = by_label.get(label, 0) + 1

        return {
            "date": datetime.now().isoformat(),
            "total_issues": total,
            "open_issues": len(open_issues),
            "closed_issues": len(closed_issues),
            "completion_rate": (len(closed_issues) / total * 100) if total > 0 else 0,
            "issues_by_label": by_label
        }

    def generate_report(self):
        """生成进度报告"""
        summary = self.get_progress_summary()

        report = f"""
📊 Issues进度报告 - {summary['date'][:10]}
{'='*50}
总Issues数: {summary['total_issues']}
开放Issues数: {summary['open_issues']}
已完成Issues数: {summary['closed_issues']}
完成率: {summary['completion_rate']:.1f}%

按标签分类:
"""
        for label, count in summary['issues_by_label'].items():
            report += f"  {label}: {count}个Issues\n"

        return report

# 使用示例
if __name__ == "__main__":
    tracker = IssueTracker()
    print(tracker.generate_report())
```

---

## 🎯 **最佳实践建议**

### **1. 时间管理**
- **小型Issue** (1-3天): 专注完成，避免多任务
- **中型Issue** (1周): 拆分成子任务，每天跟踪
- **大型Issue** (2-3周): 制定详细计划，分阶段执行

### **2. 质量保证**
- 每次提交前运行 `make fix-code`
- 定期运行 `make check-quality`
- 保持测试覆盖率持续提升

### **3. 文档维护**
- 及时更新相关文档
- 记录重要决策和变更
- 分享经验和最佳实践

### **4. 协作沟通**
- 遇到问题及时在Issue中讨论
- 定期更新Issue进度
- 完成后关闭Issue并总结经验

---

## 🎊 **成功标准**

### **个人标准**
- ✅ 每个Issue都能按时高质量完成
- ✅ 代码质量检查100%通过
- ✅ 测试覆盖率持续提升
- ✅ 文档完整准确

### **团队标准**
- ✅ Issues拆分合理，粒度适中
- ✅ 执行指南清晰，易于遵循
- ✅ 进度追踪及时，信息透明
- ✅ 经验分享充分，共同成长

**遵循这个执行指南，每个开发者（包括AI）都能高效、高质量地完成项目优化任务！** 🚀
