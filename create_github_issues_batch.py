#!/usr/bin/env python3
"""
批量创建GitHub Issues工具
根据质量检查结果自动生成标准化的Issues
"""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class IssueData:
    """Issue数据结构"""
    title: str
    body: str
    labels: list[str]
    issue_type: str


class GitHubIssuesCreator:
    """GitHub Issues创建器"""

    def __init__(self):
        self.issues = []
        self.templates = self._load_templates()

    def _load_templates(self) -> dict[str, str]:
        """加载Issue模板"""
        return {
            "syntax_fix": """
## 🚨 语法修复任务: {error_type}

### 📊 问题概述
- **错误代码**: {error_code}
- **影响文件**: {affected_files}
- **错误数量**: {error_count}
- **严重级别**: {severity_level}

### 🔧 执行步骤
1. **环境检查**
   ```bash
   source .venv/bin/activate
   ruff check {file_pattern} --output-format=concise
   ```

2. **错误定位**
   ```bash
   # 查看具体错误
   ruff check {file_pattern} --output-format=detailed
   # 或使用行号定位
   sed -n '[line_number]p' [file_path]
   ```

3. **修复工具**
   ```bash
   # 自动修复（如果支持）
   ruff check {file_pattern} --fix

   # 手动修复指南
   # 根据错误代码查阅: https://docs.astral.sh/ruff/rules/
   ```

4. **验证修复**
   ```bash
   # 重新检查该错误类型
   ruff check src/ --select={error_code} | grep {file_pattern}

   # 运行相关测试
   pytest tests/unit/{related_tests} -v
   ```

### ✅ 完成标准
- [ ] 所有目标错误已修复
- [ ] 相关测试通过
- [ ] 无新增错误
- [ ] 代码可以正常导入

### 📚 参考资料
- [Ruff规则文档](https://docs.astral.sh/ruff/rules/)
- [Python语法指南](https://docs.python.org/3/reference/)
- [项目编码规范](./DEVELOPMENT_GUIDELINES.md)

---
*自动生成时间: {timestamp}*
""",

            "code_quality": """
## 🔍 代码质量改进: {problem_type}

### 📊 问题概述
- **质量指标**: {quality_metric}
- **影响范围**: {affected_scope}
- **当前状态**: {current_status}
- **目标状态**: {target_status}

### 🛠️ 标准工具链
1. **检查工具**: `ruff check {file_pattern}`
2. **格式化工具**: `ruff format {file_pattern}`
3. **类型检查**: `mypy {file_pattern}`
4. **测试验证**: `pytest tests/unit/{related_tests}`

### 📋 执行清单
- [ ] 运行质量检查确认问题
- [ ] 使用自动化工具修复（如可能）
- [ ] 手动修复剩余问题
- [ ] 运行完整测试套件
- [ ] 检查代码覆盖率影响

### 🎯 质量标准
- 代码符合PEP8规范
- 函数/变量命名清晰
- 类型注解完整
- 文档字符串齐全
- 测试覆盖率达标

---
*自动生成时间: {timestamp}*
"""
        }

    def analyze_quality_issues(self) -> dict[str, Any]:
        """分析质量问题"""
        try:
            # 运行ruff检查获取JSON输出
            result = subprocess.run(
                ["ruff", "check", "src/", "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0 and result.stdout:
                errors = json.loads(result.stdout)
            else:
                errors = []

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # 如果无法运行ruff，使用模拟数据
            errors = self._get_mock_error_data()

        # 统计错误分布
        error_stats = {}
        for error in errors:
            code = error.get("code", "UNKNOWN")
            error_stats[code] = error_stats.get(code, 0) + 1

        return {
            "total_errors": len(errors),
            "error_stats": error_stats,
            "sample_errors": errors[:10]  # 取前10个作为样本
        }

    def _get_mock_error_data(self) -> list[dict[str, Any]]:
        """获取模拟错误数据（当无法运行ruff时使用）"""
        return [
            {
                "code": "F821",
                "filename": "/home/user/projects/FootballPrediction/src/api/auth_dependencies_messy.py",
                "location": {"row": 79, "column": 16},
                "message": "Undefined name `e`"
            },
            {
                "code": "E402",
                "filename": "/home/user/projects/FootballPrediction/src/api/betting_api.py",
                "location": {"row": 19, "column": 1},
                "message": "Module level import not at top of file"
            },
            {
                "code": "B904",
                "filename": "/home/user/projects/FootballPrediction/src/api/betting_api.py",
                "location": {"row": 180, "column": 9},
                "message": "Within an `except` clause, raise exceptions with `raise ... from err`"
            },
            {
                "code": "invalid-syntax",
                "filename": "/home/user/projects/FootballPrediction/src/config/fastapi_config.py",
                "location": {"row": 41, "column": 1},
                "message": "Unexpected indentation"
            },
            {
                "code": "N801",
                "filename": "/home/user/projects/FootballPrediction/src/api/some_file.py",
                "location": {"row": 25, "column": 8},
                "message": "Class name `someclass` should use PascalCase"
            }
        ]

    def create_syntax_fix_issues(self, analysis: dict[str, Any]) -> list[IssueData]:
        """创建语法修复类Issues"""
        issues = []

        # Critical级别的语法错误
        critical_errors = ["invalid-syntax", "F821", "E999"]

        for error_code in critical_errors:
            count = analysis["error_stats"].get(error_code, 0)
            if count > 0:
                # 获取受影响的文件样本
                affected_files = []
                for error in analysis["sample_errors"]:
                    if error.get("code") == error_code:
                        file_path = error.get("filename", "")
                        if "src/" in file_path:
                            relative_path = file_path.split("src/")[-1]
                            if relative_path not in affected_files:
                                affected_files.append(relative_path)

                # 根据错误数量确定Issue粒度
                if count <= 10:
                    # 小数量，创建一个Issue
                    issue = self._create_single_syntax_issue(error_code, count, affected_files)
                    issues.append(issue)
                else:
                    # 大数量，分批创建Issues
                    batch_size = 20
                    for i in range(0, count, batch_size):
                        batch_count = min(batch_size, count - i)
                        issue = self._create_batch_syntax_issue(
                            error_code, batch_count, i + 1, affected_files
                        )
                        issues.append(issue)

        return issues

    def _create_single_syntax_issue(self, error_code: str, count: int, files: list[str]) -> IssueData:
        """创建单个语法修复Issue"""
        error_info = self._get_error_info(error_code)

        title = f"🚨 语法修复: {error_info['name']} ({count}个错误)"

        body = self.templates["syntax_fix"].format(
            error_type=error_info['name'],
            error_code=error_code,
            affected_files=", ".join(files[:5]) + ("..." if len(files) > 5 else ""),
            error_count=count,
            severity_level=error_info['severity'],
            file_pattern=f"--select={error_code}",
            related_tests=self._get_related_tests(files),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        labels = ["bug", "syntax-fix", error_info['severity'], error_code]

        return IssueData(title, body, labels, "syntax_fix")

    def _create_batch_syntax_issue(self, error_code: str, count: int, batch_num: int, files: list[str]) -> IssueData:
        """创建批量语法修复Issue"""
        error_info = self._get_error_info(error_code)

        title = f"🚨 语法修复: {error_info['name']} - 批次{batch_num} ({count}个错误)"

        body = self.templates["syntax_fix"].format(
            error_type=f"{error_info['name']} (批次{batch_num})",
            error_code=error_code,
            affected_files="多个文件 (详见ruff检查结果)",
            error_count=count,
            severity_level=error_info['severity'],
            file_pattern=f"--select={error_code}",
            related_tests="tests/unit/",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        labels = ["bug", "syntax-fix", error_info['severity'], error_code, "batch"]

        return IssueData(title, body, labels, "syntax_fix")

    def create_code_quality_issues(self, analysis: dict[str, Any]) -> list[IssueData]:
        """创建代码质量类Issues"""
        issues = []

        # 代码质量相关的错误
        quality_errors = {
            "E402": {"name": "模块导入位置", "severity": "high"},
            "B904": {"name": "异常处理规范", "severity": "high"},
            "N801": {"name": "类名命名规范", "severity": "medium"},
            "N806": {"name": "变量名命名规范", "severity": "medium"},
            "W293": {"name": "空白行处理", "severity": "low"},
            "UP045": {"name": "类型注解优化", "severity": "low"}
        }

        for error_code, info in quality_errors.items():
            count = analysis["error_stats"].get(error_code, 0)
            if count > 0:
                issue = self._create_quality_issue(error_code, info, count)
                issues.append(issue)

        return issues

    def _create_quality_issue(self, error_code: str, info: dict[str, Any], count: int) -> IssueData:
        """创建代码质量Issue"""
        title = f"🔍 代码质量改进: {info['name']} ({count}个问题)"

        body = self.templates["code_quality"].format(
            problem_type=info['name'],
            quality_metric=error_code,
            affected_scope="全项目",
            current_status=f"发现{count}个{info['name']}问题",
            target_status="所有{info['name']}问题已修复",
            file_pattern=f"--select={error_code}",
            related_tests="tests/unit/",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        labels = ["enhancement", "code-quality", info['severity'], error_code]

        return IssueData(title, body, labels, "code_quality")

    def _get_error_info(self, error_code: str) -> dict[str, str]:
        """获取错误信息"""
        error_map = {
            "invalid-syntax": {"name": "语法错误", "severity": "critical"},
            "F821": {"name": "未定义名称", "severity": "critical"},
            "E999": {"name": "语法错误", "severity": "critical"},
            "E402": {"name": "模块导入位置", "severity": "high"},
            "B904": {"name": "异常处理规范", "severity": "high"},
            "N801": {"name": "类名命名规范", "severity": "medium"},
            "N806": {"name": "变量名命名规范", "severity": "medium"},
            "W293": {"name": "空白行处理", "severity": "low"},
            "UP045": {"name": "类型注解优化", "severity": "low"}
        }
        return error_map.get(error_code, {"name": "未知错误", "severity": "medium"})

    def _get_related_tests(self, files: list[str]) -> str:
        """获取相关测试路径"""
        if not files:
            return "tests/unit/"

        # 根据文件路径推断相关测试
        test_paths = []
        for file_path in files[:3]:  # 只取前3个文件
            if "api/" in file_path:
                test_paths.append("tests/unit/api/")
            elif "utils/" in file_path:
                test_paths.append("tests/unit/utils/")
            elif "cache/" in file_path:
                test_paths.append("tests/unit/cache/")
            else:
                test_paths.append("tests/unit/")

        return " ".join(list(set(test_paths))) if test_paths else "tests/unit/"

    def generate_issues(self) -> list[IssueData]:
        """生成所有Issues"""
        analysis = self.analyze_quality_issues()


        # 创建语法修复Issues
        syntax_issues = self.create_syntax_fix_issues(analysis)

        # 创建代码质量Issues
        quality_issues = self.create_code_quality_issues(analysis)

        all_issues = syntax_issues + quality_issues

        return all_issues

    def save_issues_to_file(self, issues: list[IssueData], filename: str = "generated_issues.json"):
        """保存Issues到文件"""
        issues_data = []
        for issue in issues:
            issues_data.append({
                "title": issue.title,
                "body": issue.body,
                "labels": issue.labels,
                "type": issue.issue_type
            })

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(issues_data, f, ensure_ascii=False, indent=2)


    def print_issues_summary(self, issues: list[IssueData]):
        """打印Issues摘要"""

        # 按类型统计
        sum(1 for i in issues if i.issue_type == "syntax_fix")
        sum(1 for i in issues if i.issue_type == "code_quality")


        sum(1 for i in issues if "critical" in i.labels)
        sum(1 for i in issues if "high" in i.labels)
        sum(1 for i in issues if "medium" in i.labels)
        sum(1 for i in issues if "low" in i.labels)


        for _i, _issue in enumerate(issues[:5], 1):
            pass

        if len(issues) > 5:
            pass


def main():
    """主函数"""

    creator = GitHubIssuesCreator()
    issues = creator.generate_issues()

    # 保存到文件
    creator.save_issues_to_file(issues)

    # 打印摘要
    creator.print_issues_summary(issues)



if __name__ == "__main__":
    main()
