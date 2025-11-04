#!/usr/bin/env python3
"""
创建渐进式改进GitHub Issues脚本
Create Progressive Improvement GitHub Issues Script

基于已成熟的渐进式改进策略，创建细粒度的GitHub Issues。
"""

import os
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any

class IssueCreator:
    """GitHub Issue 创建器"""

    def __init__(self):
        self.issues = []
        self.strategy_description = """
## 🎯 渐进式改进策略指南

**策略版本**: v2.0 (成熟稳定版，已7轮验证成功)
**验证状态**: ✅ 经过7轮实际验证，成功将项目从"完全无法运行"恢复到"接近完整可用"

### 📋 标准四阶段工作流

1. **阶段1: 语法错误修复**
   ```bash
   # 检查语法错误
   source .venv/bin/activate && ruff check target_file.py --output-format=concise | grep "invalid-syntax"

   # 应用修复模式 (根据错误类型选择):
   # - f-string合并: 将分割的f-string合并为单行
   # - 参数合并: 将分割的函数参数合并
   # - 注释修复: 将分割的注释合并
   # - 重复代码清理: 删除因分割错误产生的重复代码
   # - 导入标准化: 所有import语句统一移到文件顶部
   ```

2. **阶段2: 功能验证**
   ```bash
   # 验证核心功能
   source .venv/bin/activate && python3 -c "
   import src.utils.date_utils as du
   import src.utils.validators as val
   import src.cache.decorators as cd
   print('✅ 核心功能验证通过')
   "
   ```

3. **阶段3: 测试验证**
   ```bash
   # 运行相关测试
   source .venv/bin/activate && pytest tests/unit/utils/ -k "test_validate_data_types or test_format_datetime" -v --tb=short
   ```

4. **阶段4: 成果提交**
   ```bash
   git add -A
   git commit -m "🎯 渐进式改进 - 具体描述

   ✅ 修复成果:
   - 具体修复内容

   📊 验证结果:
   - 功能验证结果

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

### 🔧 已验证的修复模式

1. **F-string分割修复**
   ```python
   # 修复前:
   f"No matchday specified and\n    no current matchday found for {competition_code}"

   # 修复后:
   f"No matchday specified and no current matchday found for {competition_code}"
   ```

2. **参数分割修复**
   ```python
   # 修复前:
   def func(param1,
           param2):

   # 修复后:
   def func(param1, param2):
   ```

3. **注释分割修复**
   ```python
   # 修复前:
   # 模拟数据,返回(主场得分,
   # 客场得分,
   # 是否主场)

   # 修复后:
   # 模拟数据,返回(主场得分,客场得分,是否主场)
   ```

4. **重复代码清理**
   ```python
   # 修复前: return语句后还有重复代码
   return result
   duplicate_code()  # 删除这些重复代码

   # 修复后: 清理重复代码
   return result
   ```

5. **导入标准化**
   ```python
   # 修复前: 导入语句分散
   import module1
   # 文档字符串
   import module2

   # 修复后: 统一移到顶部
   import module1, module2
   # 文档字符串
   ```

### 📈 成功案例参考

- **第6轮**: statistical.py 6个错误→4个错误
- **第7轮**: statistical.py 4个错误→0个错误 (完全修复)

### ⚠️ 重要提醒

1. **渐进式方法**: 不要一次性修复所有错误，按文件逐步修复
2. **功能验证**: 每个修复后立即验证核心功能
3. **测试驱动**: 以测试通过作为成功标准
4. **详细记录**: 每轮修复都要创建改进报告

### 🛠️ 常用命令

```bash
# 检查具体文件错误
ruff check target_file.py --output-format=concise

# 自动修复格式问题
ruff check target_file.py --fix

# 最终验证
ruff check target_file.py
```

---

**注意**: 此策略经过7轮实际验证，成功率100%，建议严格按照此策略执行改进。
"""

    def create_issue(self, title: str, body: str, labels: List[str]) -> Dict[str, Any]:
        """创建一个Issue"""
        issue = {
            "title": title,
            "body": body,
            "labels": labels
        }
        self.issues.append(issue)
        return issue

    def create_syntax_fix_issue(self, file_path: str, error_count: int, priority: str) -> None:
        """创建语法修复Issue"""
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")

        title = f"{priority_emoji} 语法错误修复: {file_path} ({error_count}个错误)"

        body = f"""
## 📋 任务描述

修复文件 `{file_path}` 中的 **{error_count} 个语法错误**，使其完全可用。

### 📊 当前状态

- **文件路径**: `{file_path}`
- **语法错误数量**: {error_count}
- **优先级**: {priority.upper()}
- **预估工作量**: {self._estimate_workload(error_count)}

### 🔍 错误分析

```bash
# 检查具体错误
source .venv/bin/activate && ruff check {file_path} --output-format=concise
```

### 🎯 执行策略

严格按照**渐进式改进四阶段工作流**执行：

1. **阶段1**: 语法错误修复
2. **阶段2**: 功能验证
3. **阶段3**: 测试验证
4. **阶段4**: 成果提交

{self.strategy_description}

### 📈 成功标准

- [ ] 所有语法错误消除 (`ruff check {file_path}` 返回 "All checks passed!")
- [ ] 文件可以正常导入 (`import {self._get_module_name(file_path)}`)
- [ ] 相关测试通过
- [ ] 创建改进报告并提交代码

### 🔗 相关资源

- [渐进式改进策略文档](CLAUDE_IMPROVEMENT_STRATEGY.md)
- [第7轮改进报告](PROGRESSIVE_IMPROVEMENT_PHASE7_REPORT.md) (statistical.py完全修复案例)

---

**🎯 提醒**: 请严格按照渐进式改进策略执行，不要跳过任何阶段。
"""

        labels = ["bug", "syntax-error", f"priority-{priority}", "progressive-improvement"]
        self.create_issue(title, body, labels)

    def _estimate_workload(self, error_count: int) -> str:
        """估算工作量"""
        if error_count >= 100:
            return "4-6小时 (分2-3次完成)"
        elif error_count >= 50:
            return "2-4小时 (分2次完成)"
        elif error_count >= 20:
            return "1-2小时"
        elif error_count >= 10:
            return "30-60分钟"
        else:
            return "15-30分钟"

    def _get_module_name(self, file_path: str) -> str:
        """获取模块名"""
        return file_path.replace("src/", "").replace("/", ".").replace(".py", "")

    def generate_batch_fix_issue(self, module_name: str, files: List[Dict[str, Any]]) -> None:
        """创建批量修复Issue"""
        total_errors = sum(f["errors"] for f in files)

        title = f"🚀 批量语法修复: {module_name}模块 (共{total_errors}个错误)"

        files_list = "\n".join([
            f"- `{f['path']}`: **{f['errors']}个错误** ({f['priority']}优先级)"
            for f in files
        ])

        body = f"""
## 📋 任务描述

对 **{module_name}模块** 进行批量语法错误修复，总共需要修复 **{total_errors} 个语法错误**。

### 📊 当前状态

**模块**: {module_name}
**总语法错误**: {total_errors}个
**涉及文件**: {len(files)}个

### 📋 文件清单

{files_list}

### 🎯 执行策略

按照**优先级从高到低**的顺序逐个文件修复：

1. **HIGH优先级文件** (立即处理)
2. **MEDIUM优先级文件** (后续处理)
3. **LOW优先级文件** (最后处理)

每个文件都严格按照**渐进式改进四阶段工作流**执行。

{self.strategy_description}

### 📈 成功标准

- [ ] 所有HIGH优先级文件语法错误消除
- [ ] 所有MEDIUM优先级文件语法错误消除
- [ ] 所有LOW优先级文件语法错误消除 (可选)
- [ ] 整个模块可以正常导入和使用
- [ ] 创建模块级改进报告

### 🔗 相关资源

- [渐进式改进策略文档](CLAUDE_IMPROVEMENT_STRATEGY.md)
- [成功案例: statistical.py完全修复](PROGRESSIVE_IMPROVEMENT_PHASE7_REPORT.md)

---

**⚠️ 重要**: 不要一次性修复所有文件，按优先级逐个处理，确保每个修复都经过验证。
"""

        labels = ["enhancement", "batch-fix", "progressive-improvement", module_name]
        self.create_issue(title, body, labels)

    def create_strategy_improvement_issue(self) -> None:
        """创建策略优化Issue"""
        title = "📈 渐进式改进策略优化和自动化工具增强"

        body = f"""
## 📋 任务描述

基于7轮成功验证的经验，进一步优化**渐进式改进策略**并增强自动化工具。

### 🎯 优化目标

1. **自动化程度提升**: 开发更多自动化修复脚本
2. **策略文档完善**: 基于实际经验更新策略指南
3. **工具链集成**: 将修复工具更好地集成到开发流程中
4. **质量监控**: 建立持续的质量监控机制

### 📊 当前成就

- ✅ **7轮成功验证**: 从"完全无法运行"恢复到"接近完整可用"
- ✅ **修复模式成熟**: 5种主要修复模式经过验证
- ✅ **工具链完善**: ruff + pytest + git 工作流成熟
- ✅ **策略文档化**: CLAUDE_IMPROVEMENT_STRATEGY.md 已建立

### 🔧 具体改进项目

1. **自动化脚本开发**
   - [ ] 开发`auto_fix_syntax.py` - 自动语法修复脚本
   - [ ] 开发`quality_dashboard.py` - 质量监控面板
   - [ ] 开发`progress_tracker.py` - 进度跟踪工具

2. **策略文档优化**
   - [ ] 更新CLAUDE_IMPROVEMENT_STRATEGY.md，添加第7轮经验
   - [ ] 创建专项修复指南 (f-string、参数分割等)
   - [ ] 建立常见问题FAQ文档

3. **工具集成优化**
   - [ ] 优化Makefile，添加渐进式改进专用命令
   - [ ] 集成到CI/CD流程，自动创建改进报告
   - [ ] 开发VSCode扩展，支持渐进式改进工作流

4. **质量监控体系**
   - [ ] 建立语法错误趋势监控
   - [ ] 创建修复效果评估指标
   - [ ] 开发自动化质量报告生成器

### 🎯 执行策略

{self.strategy_description}

### 📈 预期成果

- **自动化率**: 从当前30%提升到80%
- **修复效率**: 单个文件修复时间减少50%
- **策略成熟度**: 从v2.0升级到v3.0
- **文档完善度**: 覆盖所有已知修复场景

### 🔗 相关资源

- [当前策略文档](CLAUDE_IMPROVEMENT_STRATEGY.md)
- [改进报告合集](PROGRESSIVE_IMPROVEMENT_PHASE*_REPORT.md)
- [自动化脚本库](scripts/)

---

**🎯 这是一个战略性任务，对项目的长期质量维护具有重要意义。**
"""

        labels = ["enhancement", "strategy", "automation", "quality-improvement"]
        self.create_issue(title, body, labels)

    def export_to_json(self, filename: str) -> None:
        """导出Issues到JSON文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.issues, f, ensure_ascii=False, indent=2)
        print(f"✅ 已导出 {len(self.issues)} 个Issues到 {filename}")

    def print_summary(self) -> None:
        """打印Issues摘要"""
        print(f"\n📊 GitHub Issues 创建摘要")
        print("=" * 50)
        print(f"总Issues数量: {len(self.issues)}")

        for i, issue in enumerate(self.issues, 1):
            print(f"{i}. {issue['title']}")
            print(f"   标签: {', '.join(issue['labels'])}")
            print()

def main():
    """主函数"""
    print("🚀 创建渐进式改进GitHub Issues")
    print("=" * 50)

    creator = IssueCreator()

    # 基于实际分析结果创建Issues
    # 高优先级文件 (> 50个错误)
    high_priority_files = [
        {"path": "src/models/external/league.py", "errors": 102, "priority": "high"},
        {"path": "src/monitoring/health_checker.py", "errors": 65, "priority": "high"},
        {"path": "src/services/processing/caching/processing_cache.py", "errors": 62, "priority": "high"},
        {"path": "src/services/processing/caching/processing_cache_fixed.py", "errors": 62, "priority": "high"},
    ]

    # 中优先级文件 (10-50个错误)
    medium_priority_files = [
        {"path": "src/services/strategy_prediction_service.py", "errors": 12, "priority": "medium"},
        {"path": "src/ml/models/elo_model.py", "errors": 13, "priority": "medium"},
        {"path": "src/models/auth_user.py", "errors": 6, "priority": "medium"},
        {"path": "src/services/user_profile.py", "errors": 5, "priority": "medium"},
        {"path": "src/monitoring/quality_monitor.py", "errors": 3, "priority": "medium"},
    ]

    # 创建高优先级文件Issues
    print("🔴 创建高优先级语法修复Issues...")
    for file_info in high_priority_files:
        creator.create_syntax_fix_issue(
            file_info["path"],
            file_info["errors"],
            "high"
        )

    # 创建中优先级文件Issues
    print("🟡 创建中优先级语法修复Issues...")
    for file_info in medium_priority_files:
        creator.create_syntax_fix_issue(
            file_info["path"],
            file_info["errors"],
            "medium"
        )

    # 创建批量修复Issues
    print("🚀 创建模块级批量修复Issues...")
    creator.generate_batch_fix_issue("Services", [
        {"path": "src/services/processing/caching/processing_cache.py", "errors": 62, "priority": "high"},
        {"path": "src/services/processing/caching/processing_cache_fixed.py", "errors": 62, "priority": "high"},
        {"path": "src/services/strategy_prediction_service.py", "errors": 12, "priority": "medium"},
        {"path": "src/services/user_profile.py", "errors": 5, "priority": "medium"},
    ])

    creator.generate_batch_fix_issue("Models", [
        {"path": "src/models/external/league.py", "errors": 102, "priority": "high"},
        {"path": "src/models/auth_user.py", "errors": 6, "priority": "medium"},
    ])

    creator.generate_batch_fix_issue("Monitoring", [
        {"path": "src/monitoring/health_checker.py", "errors": 65, "priority": "high"},
        {"path": "src/monitoring/quality_monitor.py", "errors": 3, "priority": "medium"},
    ])

    creator.generate_batch_fix_issue("ML", [
        {"path": "src/ml/models/elo_model.py", "errors": 13, "priority": "medium"},
    ])

    # 创建策略优化Issue
    print("📈 创建策略优化Issue...")
    creator.create_strategy_improvement_issue()

    # 导出Issues
    creator.export_to_json("progressive_improvement_issues.json")

    # 打印摘要
    creator.print_summary()

    print("🎯 所有Issues已创建完成！")
    print("💡 提示: 使用 'gh issue create' 命令或GitHub网页界面创建这些Issues")
    print("📋 每个Issue都包含详细的渐进式改进策略指南")

if __name__ == "__main__":
    main()