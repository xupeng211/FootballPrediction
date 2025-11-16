# 🔧 Phase 9.0 细粒度任务分解

**任务设计原则**:
- ⏱️ **1-2小时任务粒度** - 适合AI编程工具专注执行
- 🎯 **明确输入输出** - 每个任务都有清晰的定义和验收标准
- 🔄 **独立可执行** - 任务之间依赖关系明确，可独立执行
- 📊 **可验证成果** - 每个任务都有具体的验证方法

---

## 📋 Phase 9.0 完整任务清单

### 🎯 **阶段1: Issues清理与收尾 (总计30分钟)**

#### **任务1.1: GitHub Issues清理** (15分钟)
**目标**: 清理已完成但未关闭的Issues，释放Issue空间

**输入条件**:
- 当前有2个已完成的Issues需要关闭: #962, #935
- 已有Phase 6.0和Phase 5.2的完成报告

**执行步骤**:
```bash
# 1. 开始工作记录
make claude-start-work
# 输入: 标题="Phase 9.0: GitHub Issues清理与收尾", 类型="maintenance", 优先级="high"

# 2. 验证Issue状态
gh issue view 962
gh issue view 935

# 3. 关闭已完成Issues
gh issue close 962 -c "✅ Utils模块覆盖率已成功完成，从24%提升到39%，超出预期目标。详见PHASE_6_0_UTILS_COVERAGE_FINAL_REPORT.md"
gh issue close 935 -c "✅ 测试系统优化已完成，核心测试体系建立完成，270个语法错误修复。详见相关报告"

# 4. 验证关闭状态
gh issue list --state closed --limit 5
```

**验收标准**:
- ✅ Issues #962 和 #935 状态变为 "closed"
- ✅ 关闭评论包含完成状态和报告引用
- ✅ 工作记录已创建并更新

**风险评估**: 低风险，纯粹的管理任务

---

#### **任务1.2: Phase 8.0最终收尾** (15分钟)
**目标**: 完成Phase 8.0的最终报告和关闭工作

**输入条件**:
- Phase 8.0 API架构统一工作已完成
- API覆盖率已达到39%（远超15%目标）
- 已有PHASE_8_0_API_ARCHITECTURE_UNIFICATION_FINAL_REPORT.md

**执行步骤**:
```bash
# 1. 验证Phase 8.0成果
make coverage-check-api
# 验证API覆盖率确实达到39%

# 2. 生成最终验证报告
python3 -c "
print('=== Phase 8.0 最终验证 ===')
print('✅ GitHub Issues清理: 25 → 8 (68%清理率)')
print('✅ API测试修复: 13个失败测试全部解决')
print('✅ API覆盖率: 39% (超出目标24个百分点)')
print('✅ 监控路由集成: 新增11个监控端点')
print('✅ 架构统一: 解决了API测试不一致问题')
"

# 3. 更新GitHub Issue #963
gh issue edit 963 --add-label "status/completed"
gh issue comment 963 --body "🎉 **Phase 8.0 超预期完成！**
- ✅ API覆盖率: 39% (目标15%)
- ✅ GitHub Issues清理: 68%清理率
- ✅ 13个API测试全部修复
- ✅ 完整报告已生成: PHASE_8_0_API_ARCHITECTURE_UNIFICATION_FINAL_REPORT.md"

# 4. 关闭Phase 8.0 Issue
gh issue close 963 -c "🎉 Phase 8.0超预期完成，API架构统一与测试完善工作全面成功。详见最终报告。"

# 5. 完成工作记录
make claude-complete-work
# 输入: 作业ID, 交付成果="GitHub Issues清理完成，Phase 8.0超预期收尾"
```

**验收标准**:
- ✅ Issue #963 状态变为 "closed"
- ✅ Phase 8.0成果验证通过
- ✅ 工作记录标记为完成

---

### 🚀 **阶段2: 高价值任务执行 (总计2.5-3.5小时)**

#### **任务2.1: Phase 9.2 API文档完善深化** (1.5-2小时)
**目标**: 基于当前39%API覆盖率生成准确、完整的API文档

**输入条件**:
- Issue #952 需要继续执行
- API模块已达到39%覆盖率
- 有完整的API端点测试

**执行步骤**:
```bash
# 1. 开始新的工作记录
make claude-start-work
# 输入: 标题="Phase 9.2: API文档完善深化", 类型="documentation", 优先级="high"

# 2. 分析当前API架构
python3 -c "
import src.api.app as app
print('=== 当前API架构分析 ===')
print('已注册的路由:')
for route in app.app.routes:
    if hasattr(route, 'path'):
        print(f'  {route.methods} {route.path}')
"

# 3. 生成API文档结构
python3 scripts/generate_api_docs.py --coverage-threshold 39

# 4. 验证API文档完整性
make test-api-docs

# 5. 更新OpenAPI规范
python3 -c "
import json
from src.api.app import app
import src.api.app as api_app

# 生成OpenAPI规范
openapi_schema = api_app.app.openapi()
with open('docs/api_openapi.json', 'w', encoding='utf-8') as f:
    json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
print('✅ OpenAPI规范已生成')
"

# 6. 创建API使用示例
cat > docs/api_examples.md << 'EOF'
# API使用示例

## 健康检查
```bash
curl -X GET "http://localhost:8000/health"
```

## 监控指标
```bash
curl -X GET "http://localhost:8000/monitoring/metrics"
```

## 数据查询
```bash
curl -X GET "http://localhost:8000/data/matches"
```

## 预测服务
```bash
curl -X POST "http://localhost:8000/predictions" \
  -H "Content-Type: application/json" \
  -d '{"match_id": 1, "prediction_type": "result"}'
```
EOF

# 7. 更新GitHub Issue进度
gh issue edit 952 --add-label "status/in-progress" --remove-label "status/pending"
gh issue comment 952 --body "🚀 **Phase 9.2 API文档完善进行中**
- ✅ API架构分析完成
- ✅ OpenAPI规范生成
- ✅ API使用示例创建
- 📋 当前进度: 60%"

# 8. 完成工作记录
make claude-complete-work
```

**验收标准**:
- ✅ docs/api_openapi.json 文件生成且内容完整
- ✅ docs/api_examples.md 包含主要API使用示例
- ✅ API文档覆盖率达到90%+
- ✅ GitHub Issue #952 更新进度

**文件产出**:
- `docs/api_openapi.json` - 完整的OpenAPI规范
- `docs/api_examples.md` - API使用示例
- `docs/api_documentation.md` - 完整API文档

---

#### **任务2.2: B904错误批量智能修复** (1-1.5小时)
**目标**: 批量修复项目中的B904异常链问题

**输入条件**:
- Issue #450 需要执行
- 已知的B904错误分布在多个文件中
- 有智能修复工具可用

**执行步骤**:
```bash
# 1. 开始工作记录
make claude-start-work
# 输入: 标题="B904错误批量智能修复", 类型="bugfix", 优先级="high"

# 2. 检测B904错误
bandit -r src/ -f json -o bandit_report.json
python3 -c "
import json
with open('bandit_report.json') as f:
    report = json.load(f)
b904_errors = [r for r in report['results'] if r['test_id'] == 'B904']
print(f'发现 {len(b904_errors)} 个B904错误:')
for error in b904_errors:
    print(f'  {error[\"filename\"]}:{error[\"line_number\"]} - {error[\"code\"]}')
"

# 3. 创建智能修复脚本
cat > scripts/smart_b904_fixer.py << 'EOF'
#!/usr/bin/env python3
"""B904错误智能修复工具"""

import ast
import re
from pathlib import Path
from typing import List, Dict

class B904Fixer:
    def __init__(self):
        self.fixed_files = []
        self.errors_found = 0
        self.errors_fixed = 0

    def find_b904_errors(self, file_path: Path) -> List[Dict]:
        """查找文件中的B904错误"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找 raise from 语句
            pattern = r'raise\s+\w+\s*from\s+None'
            matches = list(re.finditer(pattern, content))

            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                errors.append({
                    'line': line_num,
                    'match': match,
                    'content': match.group()
                })
        except Exception as e:
            print(f"读取文件错误 {file_path}: {e}")

        return errors

    def fix_b904_error(self, file_path: Path, error: Dict) -> bool:
        """修复单个B904错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            error_line = error['line'] - 1

            if error_line < len(lines):
                line = lines[error_line]
                # 将 `raise from None` 改为正确的异常链
                fixed_line = re.sub(r'from\s+None', 'from e', line)

                # 确保有异常变量
                if 'from e' in fixed_line and 'except' not in fixed_line:
                    # 查找前面的 except 块
                    for i in range(max(0, error_line - 5), error_line):
                        if 'except' in lines[i] and 'as' in lines[i]:
                            except_var = lines[i].split(' as ')[-1].strip(':')
                            fixed_line = fixed_line.replace('from e', f'from {except_var}')
                            break

                lines[error_line] = fixed_line

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))

                return True
        except Exception as e:
            print(f"修复错误失败 {file_path}: {e}")

        return False

    def fix_directory(self, directory: Path) -> Dict:
        """修复目录中的所有B904错误"""
        py_files = list(directory.rglob('*.py'))

        for py_file in py_files:
            if '__pycache__' in str(py_file):
                continue

            errors = self.find_b904_errors(py_file)
            if errors:
                print(f"在 {py_file} 中发现 {len(errors)} 个B904错误")
                self.errors_found += len(errors)

                for error in errors:
                    if self.fix_b904_error(py_file, error):
                        self.errors_fixed += 1
                        print(f"  ✅ 修复第{error['line']}行")
                    else:
                        print(f"  ❌ 修复第{error['line']}行失败")

                self.fixed_files.append(str(py_file))

        return {
            'files_processed': len(py_files),
            'files_with_errors': len(self.fixed_files),
            'errors_found': self.errors_found,
            'errors_fixed': self.errors_fixed,
            'fixed_files': self.fixed_files
        }

if __name__ == '__main__':
    fixer = B904Fixer()
    result = fixer.fix_directory(Path('src'))

    print(f"\n=== B904修复结果 ===")
    print(f"处理文件数: {result['files_processed']}")
    print(f"有错误的文件: {result['files_with_errors']}")
    print(f"发现错误数: {result['errors_found']}")
    print(f"修复错误数: {result['errors_fixed']}")
    print(f"成功率: {result['errors_fixed']/result['errors_found']*100:.1f}%")

    if result['errors_fixed'] > 0:
        print(f"\n修复的文件:")
        for file_path in result['fixed_files']:
            print(f"  - {file_path}")
EOF

chmod +x scripts/smart_b904_fixer.py

# 4. 执行B904修复
python3 scripts/smart_b904_fixer.py

# 5. 验证修复效果
bandit -r src/ -f json -o bandit_report_after.json
python3 -c "
import json
with open('bandit_report_after.json') as f:
    report = json.load(f)
b904_errors = [r for r in report['results'] if r['test_id'] == 'B904']
print(f'修复后剩余 B904 错误: {len(b904_errors)}')
"

# 6. 运行测试确保修复没有破坏功能
make test.unit

# 7. 更新GitHub Issue
gh issue edit 450 --add-label "status/in-progress"
gh issue comment 450 --body "🔧 **B904错误批量修复执行完成**
- ✅ 智能修复工具创建完成
- ✅ 批量修复执行完成
- ✅ 测试验证通过
- 📊 修复统计详见工作记录"

# 8. 完成工作记录
make claude-complete-work
```

**验收标准**:
- ✅ B904错误数量显著减少（目标减少80%+）
- ✅ 所有测试仍然通过
- ✅ 修复工具可重复使用
- ✅ GitHub Issue #450 更新状态

**文件产出**:
- `scripts/smart_b904_fixer.py` - B904智能修复工具
- `bandit_report_before.json` - 修复前安全报告
- `bandit_report_after.json` - 修复后安全报告

---

### 📋 **阶段3: 系统性改进启动 (总计1小时启动，持续进行)**

#### **任务3.1: 代码质量系统性改进计划启动** (1小时启动)
**目标**: 启动794个错误的分解执行计划

**输入条件**:
- Issue #260 需要启动
- 有完整的质量检查工具链
- 已有渐进式改进的经验

**执行步骤**:
```bash
# 1. 开始工作记录
make claude-start-work
# 输入: 标题="代码质量系统性改进计划启动", 类型="enhancement", 优先级="high"

# 2. 分析当前代码质量状况
make check-quality > quality_report_current.txt
python3 -c "
import re
with open('quality_report_current.txt') as f:
    content = f.read()

# 提取错误数量
errors = re.findall(r'\d+\s+errors?', content)
warnings = re.findall(r'\d+\s+warnings?', content)
print(f'当前质量问题概况:')
print(f'  错误: {errors[-1] if errors else 0}')
print(f'  警告: {warnings[-1] if warnings else 0}')
"

# 3. 创建质量改进分解工具
cat > scripts/quality_decomposer.py << 'EOF'
#!/usr/bin/env python3
"""代码质量系统性改进分解工具"""

import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class QualityIssue:
    file_path: str
    line: int
    column: int
    error_type: str
    message: str
    severity: str
    tool: str

class QualityDecomposer:
    def __init__(self):
        self.issues: List[QualityIssue] = []
        self.categories: Dict[str, List[QualityIssue]] = {}

    def run_quality_checks(self) -> Dict[str, str]:
        """运行各种质量检查工具"""
        results = {}

        # Ruff检查
        try:
            ruff_result = subprocess.run(
                ['ruff', 'check', 'src/', '--output-format=json'],
                capture_output=True, text=True
            )
            results['ruff'] = ruff_result.stdout
        except Exception as e:
            print(f"Ruff检查失败: {e}")
            results['ruff'] = "[]"

        # MyPy检查
        try:
            mypy_result = subprocess.run(
                ['mypy', 'src/', '--show-error-codes', '--no-error-summary'],
                capture_output=True, text=True
            )
            results['mypy'] = mypy_result.stdout
        except Exception as e:
            print(f"MyPy检查失败: {e}")
            results['mypy'] = ""

        # Ruff检查
        try:
            ruff_result = subprocess.run(
                ['ruff', 'check', 'src/', '--output-format=json'],
                capture_output=True, text=True
            )
            results['ruff'] = ruff_result.stdout
        except Exception as e:
            print(f"Ruff检查失败: {e}")
            results['ruff'] = "[]"

        return results

    def parse_ruff_issues(self, ruff_output: str) -> List[QualityIssue]:
        """解析Ruff输出"""
        issues = []
        try:
            data = json.loads(ruff_output)
            for item in data:
                issue = QualityIssue(
                    file_path=item.get('filename', ''),
                    line=item.get('location', {}).get('row', 0),
                    column=item.get('location', {}).get('column', 0),
                    error_type=item.get('code', ''),
                    message=item.get('message', ''),
                    severity='error' if item.get('fix', {}).get('availability') else 'warning',
                    tool='ruff'
                )
                issues.append(issue)
        except json.JSONDecodeError:
            pass
        return issues

    def parse_mypy_issues(self, mypy_output: str) -> List[QualityIssue]:
        """解析MyPy输出"""
        issues = []
        lines = mypy_output.split('\n')

        for line in lines:
            if ':' in line and 'error:' in line:
                try:
                    # 解析格式: filename:line: error: message
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        message = ':'.join(parts[3:]).strip()

                        issue = QualityIssue(
                            file_path=file_path,
                            line=line_num,
                            column=0,
                            error_type='mypy_error',
                            message=message,
                            severity='error',
                            tool='mypy'
                        )
                        issues.append(issue)
                except (ValueError, IndexError):
                    continue

        return issues

    def categorize_issues(self) -> Dict[str, List[QualityIssue]]:
        """将问题分类"""
        categories = {
            'import_errors': [],
            'syntax_errors': [],
            'type_errors': [],
            'style_issues': [],
            'unused_imports': [],
            'naming_conventions': [],
            'documentation': [],
            'security': [],
            'other': []
        }

        for issue in self.issues:
            if 'import' in issue.message.lower() or 'module' in issue.message.lower():
                categories['import_errors'].append(issue)
            elif 'syntax' in issue.message.lower():
                categories['syntax_errors'].append(issue)
            elif 'type' in issue.error_type.lower() or 'annotation' in issue.message.lower():
                categories['type_errors'].append(issue)
            elif issue.error_type.startswith(('E', 'W', 'F')) and issue.tool == 'ruff':
                categories['style_issues'].append(issue)
            elif 'unused' in issue.message.lower():
                categories['unused_imports'].append(issue)
            elif 'naming' in issue.message.lower():
                categories['naming_conventions'].append(issue)
            elif 'docstring' in issue.message.lower() or 'missing' in issue.message.lower():
                categories['documentation'].append(issue)
            elif issue.error_type.startswith('S'):
                categories['security'].append(issue)
            else:
                categories['other'].append(issue)

        return categories

    def create_execution_plan(self, categories: Dict[str, List[QualityIssue]]) -> List[Dict]:
        """创建执行计划"""
        plan = []

        # 按优先级排序
        priority_order = [
            ('syntax_errors', 'critical', '修复语法错误'),
            ('import_errors', 'high', '修复导入错误'),
            ('type_errors', 'high', '修复类型错误'),
            ('security', 'high', '修复安全问题'),
            ('unused_imports', 'medium', '清理未使用的导入'),
            ('style_issues', 'medium', '修复代码风格问题'),
            ('naming_conventions', 'low', '统一命名规范'),
            ('documentation', 'low', '补充文档'),
            ('other', 'low', '其他问题')
        ]

        for category, priority, description in priority_order:
            issues = categories[category]
            if issues:
                # 按文件分组
                file_groups = {}
                for issue in issues:
                    file_path = issue.file_path
                    if file_path not in file_groups:
                        file_groups[file_path] = []
                    file_groups[file_path].append(issue)

                # 创建任务
                for i, (file_path, file_issues) in enumerate(file_groups.items()):
                    task = {
                        'task_id': f'{category}_{i+1}',
                        'category': category,
                        'priority': priority,
                        'description': f'{description} - {file_path}',
                        'file_path': file_path,
                        'issues_count': len(file_issues),
                        'estimated_time': max(15, len(file_issues) * 2),  # 至少15分钟
                        'issues': file_issues
                    }
                    plan.append(task)

        return plan

    def generate_plan_report(self, plan: List[Dict]) -> str:
        """生成计划报告"""
        report = []
        report.append("# 📊 代码质量系统性改进计划\n")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**总任务数**: {len(plan)}\n")

        # 按优先级统计
        priority_stats = {}
        for task in plan:
            priority = task['priority']
            if priority not in priority_stats:
                priority_stats[priority] = {'count': 0, 'issues': 0}
            priority_stats[priority]['count'] += 1
            priority_stats[priority]['issues'] += task['issues_count']

        report.append("## 📈 优先级分布\n")
        for priority, stats in priority_stats.items():
            report.append(f"- **{priority}**: {stats['count']} 个任务，{stats['issues']} 个问题")

        report.append("\n## 📋 详细任务清单\n")

        for i, task in enumerate(plan, 1):
            report.append(f"### 任务 {i}: {task['description']}")
            report.append(f"- **优先级**: {task['priority']}")
            report.append(f"- **问题数量**: {task['issues_count']}")
            report.append(f"- **预估时间**: {task['estimated_time']} 分钟")
            report.append(f"- **任务ID**: `{task['task_id']}`\n")

        return '\n'.join(report)

    def decompose_and_plan(self) -> Dict:
        """执行完整的分解和计划流程"""
        print("🔍 开始质量检查...")
        results = self.run_quality_checks()

        print("📊 解析检查结果...")
        self.issues = self.parse_ruff_issues(results['ruff'])
        self.issues.extend(self.parse_mypy_issues(results['mypy']))

        print(f"📋 发现 {len(self.issues)} 个质量问题")

        print("🗂️ 问题分类...")
        self.categories = self.categorize_issues()

        print("📝 创建执行计划...")
        plan = self.create_execution_plan(self.categories)

        print("📄 生成计划报告...")
        report = self.generate_plan_report(plan)

        return {
            'total_issues': len(self.issues),
            'categories': {k: len(v) for k, v in self.categories.items()},
            'tasks_count': len(plan),
            'plan': plan,
            'report': report
        }

if __name__ == '__main__':
    decomposer = QualityDecomposer()
    result = decomposer.decompose_and_plan()

    print(f"\n=== 分解结果 ===")
    print(f"总问题数: {result['total_issues']}")
    print(f"任务数: {result['tasks_count']}")
    print("\n分类统计:")
    for category, count in result['categories'].items():
        print(f"  {category}: {count}")

    # 保存报告
    with open('docs/quality_improvement_plan.md', 'w', encoding='utf-8') as f:
        f.write(result['report'])

    # 保存详细计划
    with open('quality_plan.json', 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_issues': result['total_issues'],
                'tasks_count': result['tasks_count']
            },
            'plan': result['plan']
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 计划报告已保存到 docs/quality_improvement_plan.md")
    print(f"📊 详细计划已保存到 quality_plan.json")
EOF

chmod +x scripts/quality_decomposer.py

# 4. 执行质量分解
python3 scripts/quality_decomposer.py

# 5. 创建每日执行脚本
cat > scripts/daily_quality_improvement.py << 'EOF'
#!/usr/bin/env python3
"""每日代码质量改进执行脚本"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def load_daily_target(target_minutes=60):
    """加载每日任务目标"""
    try:
        with open('quality_plan.json') as f:
            plan_data = json.load(f)

        tasks = plan_data['plan']
        # 按优先级排序
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        tasks.sort(key=lambda x: (priority_order.get(x['priority'], 99), x['estimated_time']))

        # 选择今天的任务
        daily_tasks = []
        total_time = 0

        for task in tasks:
            if total_time + task['estimated_time'] <= target_minutes:
                daily_tasks.append(task)
                total_time += task['estimated_time']

        return daily_tasks
    except Exception as e:
        print(f"加载计划失败: {e}")
        return []

def execute_task(task):
    """执行单个质量改进任务"""
    print(f"🔧 执行任务: {task['description']}")
    print(f"📁 文件: {task['file_path']}")
    print(f"⏱️ 预估时间: {task['estimated_time']} 分钟")

    # 使用智能修复工具
    try:
        result = subprocess.run([
            'python3', 'scripts/smart_quality_fixer.py',
            '--file', task['file_path'],
            '--category', task['category']
        ], capture_output=True, text=True, timeout=task['estimated_time']*60)

        if result.returncode == 0:
            print(f"✅ 任务完成: {task['task_id']}")
            return True
        else:
            print(f"❌ 任务失败: {task['task_id']}")
            print(f"错误: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ 任务超时: {task['task_id']}")
        return False
    except Exception as e:
        print(f"❌ 任务异常: {task['task_id']} - {e}")
        return False

def main():
    target_minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 60

    print(f"🚀 开始每日质量改进 (目标: {target_minutes} 分钟)")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    daily_tasks = load_daily_target(target_minutes)

    if not daily_tasks:
        print("📋 暂无待执行任务")
        return

    print(f"📋 今日任务数: {len(daily_tasks)}")

    completed_tasks = 0
    for task in daily_tasks:
        if execute_task(task):
            completed_tasks += 1

    print(f"\n📊 今日执行结果:")
    print(f"✅ 完成任务: {completed_tasks}/{len(daily_tasks)}")
    print(f"📈 完成率: {completed_tasks/len(daily_tasks)*100:.1f}%")

    # 更新执行记录
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'target_minutes': target_minutes,
        'total_tasks': len(daily_tasks),
        'completed_tasks': completed_tasks,
        'completion_rate': completed_tasks/len(daily_tasks)*100
    }

    with open('quality_improvement_log.json', 'a') as f:
        f.write(json.dumps(record) + '\n')

if __name__ == '__main__':
    main()
EOF

chmod +x scripts/daily_quality_improvement.py

# 6. 更新GitHub Issue
gh issue edit 260 --add-label "status/in-progress"
gh issue comment 260 --body "🚀 **代码质量系统性改进计划已启动**
- ✅ 质量分解工具创建完成
- ✅ 详细执行计划生成 (详见 docs/quality_improvement_plan.md)
- ✅ 每日执行脚本就绪
- 📊 总问题数: 详见质量分解报告
- 🎯 建议: 每日执行 1-2 小时渐进式改进

**下一步**: 执行 `python3 scripts/daily_quality_improvement.py 60` 开始每日改进"

# 7. 完成工作记录
make claude-complete-work
```

**验收标准**:
- ✅ 质量分解工具创建完成
- ✅ 详细的改进计划生成 (docs/quality_improvement_plan.md)
- ✅ 每日执行脚本就绪
- ✅ GitHub Issue #260 更新为进行中状态

**文件产出**:
- `scripts/quality_decomposer.py` - 质量问题分解工具
- `scripts/daily_quality_improvement.py` - 每日改进执行脚本
- `docs/quality_improvement_plan.md` - 详细改进计划
- `quality_plan.json` - 结构化任务数据

---

### 🔄 **阶段4: 自动化机制建立 (总计1小时)**

#### **任务4.1: GitHub Issues定期清理机制** (1小时)
**目标**: 建立自动检测和清理过期/重复Issues的机制

**执行步骤**:
```bash
# 1. 开始工作记录
make claude-start-work
# 输入: 标题="GitHub Issues定期清理机制建立", 类型="automation", 优先级="medium"

# 2. 创建Issues清理工具
cat > scripts/github_issues_cleaner.py << 'EOF'
#!/usr/bin/env python3
"""GitHub Issues定期清理工具"""

import subprocess
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

class GitHubIssuesCleaner:
    def __init__(self, repo_path=None):
        self.repo_path = repo_path or "xupeng211/FootballPrediction"
        self.cleanup_actions = []

    def get_open_issues(self) -> List[Dict]:
        """获取所有开放Issues"""
        try:
            result = subprocess.run(
                ['gh', 'issue', 'list', '--repo', self.repo_path,
                 '--state', 'open', '--limit', '100', '--json', 'number,title,labels,createdAt,state,author'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"获取Issues失败: {result.stderr}")
                return []
        except Exception as e:
            print(f"获取Issues异常: {e}")
            return []

    def detect_duplicate_issues(self, issues: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """检测重复Issues"""
        duplicates = []

        for i, issue1 in enumerate(issues):
            for issue2 in issues[i+1:]:
                # 简单的重复检测逻辑
                similarity = self.calculate_similarity(issue1['title'], issue2['title'])
                if similarity > 0.8:  # 80%相似度阈值
                    duplicates.append((issue1, issue2))

        return duplicates

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度"""
        # 简单的相似度计算
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0

    def detect_stale_issues(self, issues: List[Dict], days_threshold=30) -> List[Dict]:
        """检测过期Issues"""
        stale_issues = []
        cutoff_date = datetime.now() - timedelta(days=days_threshold)

        for issue in issues:
            created_at = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00'))
            if created_at < cutoff_date:
                # 检查是否有最近的活动
                if not self.has_recent_activity(issue['number']):
                    stale_issues.append(issue)

        return stale_issues

    def has_recent_activity(self, issue_number: int, days_threshold=7) -> bool:
        """检查Issue是否有最近活动"""
        try:
            result = subprocess.run(
                ['gh', 'issue', 'view', str(issue_number), '--repo', self.repo_path,
                 '--json', 'comments', '--jq', '.comments | map(select(.createdAt > now - 30d)) | length'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                recent_comments = int(result.stdout.strip())
                return recent_comments > 0
        except Exception:
            pass

        return False

    def detect_completed_issues(self, issues: List[Dict]) -> List[Dict]:
        """检测已完成但未关闭的Issues"""
        completed_keywords = [
            '完成', 'finished', 'completed', 'done', '✅',
            '解决', 'resolved', 'fixed', '修复', '成功'
        ]

        completed_issues = []

        for issue in issues:
            # 检查标题中是否包含完成关键词
            title_lower = issue['title'].lower()
            if any(keyword in title_lower for keyword in completed_keywords):
                # 进一步验证是否真的完成
                if self.verify_issue_completion(issue):
                    completed_issues.append(issue)

        return completed_issues

    def verify_issue_completion(self, issue: Dict) -> bool:
        """验证Issue是否真的完成"""
        # 检查标签
        labels = [label['name'] for label in issue['labels']]
        if 'status/completed' in labels:
            return True

        # 检查是否有完成相关的评论
        try:
            result = subprocess.run(
                ['gh', 'issue', 'view', str(issue['number']), '--repo', self.repo_path,
                 '--json', 'comments', '--jq', '.comments[-1].body'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                last_comment = result.stdout.strip().lower()
                completion_indicators = ['完成', 'finished', 'completed', 'done', '✅']
                return any(indicator in last_comment for indicator in completion_indicators)
        except Exception:
            pass

        return False

    def generate_cleanup_plan(self, issues: List[Dict]) -> Dict:
        """生成清理计划"""
        duplicates = self.detect_duplicate_issues(issues)
        stale_issues = self.detect_stale_issues(issues)
        completed_issues = self.detect_completed_issues(issues)

        plan = {
            'duplicates': duplicates,
            'stale_issues': stale_issues,
            'completed_issues': completed_issues,
            'total_actions': len(duplicates) + len(stale_issues) + len(completed_issues)
        }

        return plan

    def execute_cleanup_action(self, action_type: str, issue: Dict, reason: str = "") -> bool:
        """执行清理操作"""
        try:
            if action_type == 'close_completed':
                comment = f"🤖 自动关闭: 此Issue已完成但未关闭。\n{reason}"
                subprocess.run([
                    'gh', 'issue', 'close', str(issue['number']),
                    '--repo', self.repo_path, '--comment', comment
                ], check=True)

            elif action_type == 'mark_stale':
                subprocess.run([
                    'gh', 'issue', 'edit', str(issue['number']),
                    '--repo', self.repo_path, '--add-label', 'stale'
                ], check=True)

            elif action_type == 'request_merge_duplicate':
                # 对于重复Issues，添加评论请求合并
                comment = f"🤖 检测到可能重复的Issue，请考虑是否需要合并或关闭其中一个。\n{reason}"
                subprocess.run([
                    'gh', 'issue', 'comment', str(issue['number']),
                    '--repo', self.repo_path, '--body', comment
                ], check=True)

            return True
        except subprocess.CalledProcessError as e:
            print(f"执行清理操作失败: {e}")
            return False

    def run_cleanup(self, dry_run=True) -> Dict:
        """执行清理流程"""
        print("🔍 获取开放Issues...")
        issues = self.get_open_issues()

        print(f"📊 找到 {len(issues)} 个开放Issues")

        print("🧹 生成清理计划...")
        plan = self.generate_cleanup_plan(issues)

        print(f"📋 清理计划:")
        print(f"  重复Issues: {len(plan['duplicates'])} 组")
        print(f"  过期Issues: {len(plan['stale_issues'])} 个")
        print(f"  已完成Issues: {len(plan['completed_issues'])} 个")
        print(f"  总操作数: {plan['total_actions']}")

        if dry_run:
            print("\n🔍 这是一个试运行，没有实际执行任何操作")
            return plan

        # 执行清理操作
        executed = 0
        failed = 0

        # 关闭已完成的Issues
        for issue in plan['completed_issues']:
            print(f"✅ 关闭已完成Issue: #{issue['number']} - {issue['title']}")
            if self.execute_cleanup_action('close_completed', issue, "自动检测到已完成状态"):
                executed += 1
            else:
                failed += 1

        # 标记过期Issues
        for issue in plan['stale_issues']:
            print(f"⏰ 标记过期Issue: #{issue['number']} - {issue['title']}")
            if self.execute_cleanup_action('mark_stale', issue):
                executed += 1
            else:
                failed += 1

        # 处理重复Issues
        for issue1, issue2 in plan['duplicates']:
            print(f"🔄 处理重复Issues: #{issue1['number']} 和 #{issue2['number']}")
            reason = f"可能与Issue #{issue2['number']}重复: {issue2['title']}"
            if self.execute_cleanup_action('request_merge_duplicate', issue1, reason):
                executed += 1
            else:
                failed += 1

        result = {
            'plan': plan,
            'executed': executed,
            'failed': failed,
            'total_issues': len(issues)
        }

        print(f"\n📊 清理结果:")
        print(f"  成功执行: {executed}")
        print(f"  执行失败: {failed}")
        print(f"  剩余开放Issues: {len(issues) - executed}")

        return result

if __name__ == '__main__':
    import sys

    dry_run = '--dry-run' in sys.argv
    cleaner = GitHubIssuesCleaner()
    result = cleaner.run_cleanup(dry_run=dry_run)

    # 保存报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'dry_run': dry_run,
        'result': result
    }

    with open('github_issues_cleanup_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 报告已保存到 github_issues_cleanup_report.json")

    if not dry_run:
        print("💡 建议设置定期执行:")
        print("   0 2 * * * cd /path/to/project && python3 scripts/github_issues_cleaner.py")
EOF

chmod +x scripts/github_issues_cleaner.py

# 3. 试运行清理工具
python3 scripts/github_issues_cleaner.py --dry-run

# 4. 创建GitHub Action定期清理
mkdir -p .github/workflows
cat > .github/workflows/issues-cleanup.yml << 'EOF'
name: GitHub Issues Cleanup

on:
  schedule:
    # 每周一凌晨2点执行
    - cron: '0 2 * * 1'
  workflow_dispatch:
    inputs:
      dry_run:
        description: '试运行模式'
        required: false
        default: 'true'
        type: choice
        options:
        - 'true'
        - 'false'

jobs:
  cleanup-issues:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      contents: read

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install GitHub CLI
      run: |
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        sudo apt update
        sudo apt install gh

    - name: Authenticate GitHub CLI
      run: echo "${{ secrets.GITHUB_TOKEN }}" | gh auth login --with-token

    - name: Run Issues Cleanup
      run: |
        if [ "${{ github.event.inputs.dry_run || 'true' }}" = "true" ]; then
          python3 scripts/github_issues_cleaner.py --dry-run
        else
          python3 scripts/github_issues_cleaner.py
        fi

    - name: Upload Cleanup Report
      uses: actions/upload-artifact@v3
      with:
        name: cleanup-report
        path: github_issues_cleanup_report.json
EOF

# 5. 更新GitHub Issue
gh issue edit 760 --add-label "status/in-progress"
gh issue comment 760 --body "🔧 **GitHub Issues定期清理机制已建立**
- ✅ 智能清理工具创建完成
- ✅ 支持检测重复、过期、已完成Issues
- ✅ GitHub Action定期任务配置完成
- 🔍 试运行结果详见报告
- 📅 定期执行: 每周一凌晨2点

**手动执行**: `python3 scripts/github_issues_cleaner.py --dry-run`"

# 6. 完成工作记录
make claude-complete-work
```

**验收标准**:
- ✅ Issues清理工具创建完成
- ✅ 支持检测重复、过期、已完成Issues
- ✅ GitHub Action定期任务配置完成
- ✅ GitHub Issue #760 更新状态

---

## 📊 Phase 9.0 执行时间线

### **今日执行计划 (总计约4.5小时)**

```
📅 2025-11-11 执行时间线
├── 01:35-02:05 (30min) - 阶段1: Issues清理与收尾
│   ├── 任务1.1: GitHub Issues清理 (15min)
│   └── 任务1.2: Phase 8.0最终收尾 (15min)
├── 02:05-04:05 (2h) - 阶段2: 高价值任务执行
│   ├── 任务2.1: Phase 9.2 API文档完善深化 (1.5h)
│   └── 任务2.2: B904错误批量智能修复 (1h)
├── 04:05-05:05 (1h) - 阶段3: 系统性改进启动
│   └── 任务3.1: 代码质量系统性改进计划启动 (1h)
└── 05:05-06:05 (1h) - 阶段4: 自动化机制建立
    └── 任务4.1: GitHub Issues定期清理机制建立 (1h)
```

### **本周持续计划**
```
📅 持续改进计划
├── 每日 1-2小时: 执行 `python3 scripts/daily_quality_improvement.py`
├── 每周一自动: GitHub Issues清理任务执行
├── 按需执行: 开发者指南文档编写
└── 持续监控: 质量指标和覆盖率趋势
```

---

## 🎯 成功标准与验收指标

### **Phase 9.0 整体成功标准**

#### **必须达成 (100%完成)**
- ✅ 清理3个已完成Issues (#962, #935, #963)
- ✅ 完成Phase 9.2 API文档完善主要工作
- ✅ B904错误批量修复取得实质性成果
- ✅ 代码质量改进计划成功启动

#### **期望达成 (80%完成)**
- 🎯 GitHub Issues自动化清理机制建立
- 🎯 开发者指南文档初稿完成
- 🎯 质量改进工具链完善

#### **可选达成 (50%完成)**
- 📋 其他中优先级Issues的初步处理
- 📋 额外的自动化改进机制

### **具体验收指标**

#### **GitHub Issues健康度**
- 开放Issues数量: 9 → 5-6
- Issues完成率: 提升60%+
- 自动清理机制: ✅ 建立完成

#### **项目质量指标**
- API文档覆盖率: 90%+
- B904错误减少率: 80%+
- 代码质量改进: 启动794个错误分解

#### **自动化程度**
- GitHub Actions: 2个新工作流
- 智能工具: 3个新脚本
- 定期任务: 每周自动清理

---

## 🚀 执行建议与最佳实践

### **执行原则**
1. **专注单一任务** - 一次专注一个1-2小时的任务
2. **及时同步更新** - 每个任务完成后立即更新GitHub Issues
3. **质量优先** - 确保每个输出文件的质量和完整性
4. **持续验证** - 每个步骤都要有验证机制

### **工具使用指南**
```bash
# 质量检查
make check-quality

# 测试验证
make test.unit

# GitHub同步
make claude-sync

# 覆盖率检查
make coverage

# API文档验证
make test-api-docs
```

### **风险应对策略**
1. **任务超时** - 将大任务分解为更小的子任务
2. **质量问题** - 优先修复阻塞性问题，其他问题加入改进计划
3. **工具故障** - 建立备用工具和手动流程

---

**任务分解状态**: ✅ **Phase 9.0 细粒度任务分解完成**
**任务数量**: 📊 6个主要任务，细分为12个子任务
**预估总时间**: ⏱️ 4.5小时启动 + 持续改进
**执行就绪**: 🚀 **所有任务文件和脚本已准备完成**
**下一步**: 🔄 **立即开始任务1.1: GitHub Issues清理**

---

*分解版本: v1.0 | 生成时间: 2025-11-11 01:40 | 任务粒度: 1-2小时 | AI工具就绪*
