#!/usr/bin/env python3
"""
Claude Code CLI 包装器

用于集成 Claude Code CLI 到自动修复流程中，避免 API 调用费用。
"""

import subprocess
import json
import re
import tempfile
import os
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TestFailure:
    """测试失败信息"""
    file_path: str
    test_name: str
    error_type: str
    error_message: str
    traceback: str
    line_number: Optional[int] = None


@dataclass
class FixSuggestion:
    """修复建议"""
    original_code: str
    fixed_code: str
    explanation: str
    confidence: float
    file_path: str
    line_range: Tuple[int, int]


class ClaudeCodeWrapper:
    """Claude Code CLI 包装器类"""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="claude_fix_"))
        logger.info(f"Created temporary directory: {self.temp_dir}")

    def __del__(self):
        """清理临时文件"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

    def analyze_test_failure(self, test_failure: TestFailure) -> Dict:
        """
        分析测试失败，调用 Claude Code CLI 获取修复建议

        Args:
            test_failure: 测试失败信息

        Returns:
            分析结果字典
        """
        # 创建分析提示
        prompt = self._create_analysis_prompt(test_failure)

        # 创建临时输入文件
        input_file = self.temp_dir / "analysis_input.txt"
        input_file.write_text(prompt, encoding='utf-8')

        try:
            # 调用 Claude Code CLI 进行分析
            result = self._call_claude_code(
                task="analyze",
                input_file=str(input_file),
                context=f"File: {test_failure.file_path}, Test: {test_failure.test_name}"
            )

            # 解析分析结果
            analysis = self._parse_analysis_result(result)
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze test failure: {e}")
            return {"error": str(e), "suggestions": []}

    def generate_fix(self, test_failure: TestFailure, analysis: Dict) -> FixSuggestion:
        """
        生成具体的代码修复

        Args:
            test_failure: 测试失败信息
            analysis: 分析结果

        Returns:
            修复建议
        """
        # 创建修复提示
        prompt = self._create_fix_prompt(test_failure, analysis)

        # 创建临时输入文件
        input_file = self.temp_dir / "fix_input.txt"
        input_file.write_text(prompt, encoding='utf-8')

        try:
            # 调用 Claude Code CLI 生成修复
            result = self._call_claude_code(
                task="fix",
                input_file=str(input_file),
                context=f"Fix for {test_failure.file_path}"
            )

            # 解析修复结果
            fix_suggestion = self._parse_fix_result(result, test_failure.file_path)
            return fix_suggestion

        except Exception as e:
            logger.error(f"Failed to generate fix: {e}")
            return FixSuggestion(
                original_code="",
                fixed_code="",
                explanation=f"Failed to generate fix: {e}",
                confidence=0.0,
                file_path=test_failure.file_path,
                line_range=(0, 0)
            )

    def validate_fix(self, fix_suggestion: FixSuggestion) -> bool:
        """
        验证修复建议的质量

        Args:
            fix_suggestion: 修复建议

        Returns:
            是否通过验证
        """
        # 基本验证逻辑
        if not fix_suggestion.fixed_code.strip():
            return False

        if fix_suggestion.confidence < 0.5:
            return False

        # 检查修复后的代码语法
        try:
            compile(fix_suggestion.fixed_code, f"<fix_{fix_suggestion.file_path}>", "exec")
            return True
        except SyntaxError:
            return False

    def _call_claude_code(self, task: str, input_file: str, context: str) -> str:
        """
        调用 Claude Code CLI

        Args:
            task: 任务类型 (analyze/fix)
            input_file: 输入文件路径
            context: 上下文信息

        Returns:
            Claude Code CLI 的输出
        """
        # 读取输入文件内容
        with open(input_file, 'r', encoding='utf-8') as f:
            input_content = f.read()

        # 构建 Claude Code CLI 命令 - 使用正确的格式
        if task == "analyze":
            prompt = f"""Analyze this test failure:

{input_content}

Context: {context}

Please provide:
1. Root cause analysis
2. Suggested fix approach
3. Confidence level (0-1)

Respond in JSON format."""
        else:  # fix
            prompt = f"""Generate a fix for this code issue:

{input_content}

Context: {context}

Please provide the fixed code and explanation.

Respond in JSON format with fixed_code and explanation."""

        cmd = [
            "claude", "code",
            "--print",
            "--output-format", "json"
        ]

        # 使用 echo 将 prompt 通过 stdin 传递给 claude code
        full_cmd = f"echo {shlex.quote(prompt)} | {' '.join(cmd)}"

        try:
            logger.info(f"Calling Claude Code CLI with stdin input...")
            # 使用 shell 执行管道命令
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,  # 2分钟超时
                cwd=str(self.temp_dir)
            )

            if result.returncode != 0:
                raise Exception(f"Claude Code CLI failed with return code {result.returncode}: {result.stderr}")

            return result.stdout

        except subprocess.TimeoutExpired:
            raise Exception("Claude Code CLI timed out after 120 seconds")
        except FileNotFoundError:
            # 如果 Claude Code CLI 不可用，使用模拟数据进行开发测试
            logger.warning("Claude Code CLI not found, using mock data for development")
            return self._get_mock_response(task)

    def _get_mock_response(self, task: str) -> str:
        """获取模拟响应（用于开发测试）"""
        if task == "analyze":
            return json.dumps({
                "error_type": "SyntaxError",
                "root_cause": "Missing import statement",
                "affected_functions": ["test_function"],
                "suggestions": ["Add missing import", "Fix indentation"]
            })
        else:  # fix
            return json.dumps({
                "fixed_code": "# Fixed code example\nimport pytest\n\ndef test_example():\n    assert True",
                "explanation": "Added missing import and fixed indentation",
                "confidence": 0.85,
                "line_range": [1, 5]
            })

    def _create_analysis_prompt(self, test_failure: TestFailure) -> str:
        """创建分析提示"""
        return f"""
Please analyze the following test failure:

File: {test_failure.file_path}
Test: {test_failure.test_name}
Error Type: {test_failure.error_type}
Error Message: {test_failure.error_message}
Traceback:
{test_failure.traceback}

Please provide:
1. Root cause analysis
2. Error type classification (syntax, logic, dependency, configuration)
3. Affected code functions/lines
4. Suggested fix approach

Format your response as JSON.
"""

    def _create_fix_prompt(self, test_failure: TestFailure, analysis: Dict) -> str:
        """创建修复提示"""
        return f"""
Based on the following analysis, please generate a fix:

Test Failure:
- File: {test_failure.file_path}
- Test: {test_failure.test_name}
- Error: {test_failure.error_type}
- Message: {test_failure.error_message}

Analysis:
{json.dumps(analysis, indent=2)}

Please provide:
1. The fixed code
2. Explanation of the fix
3. Confidence level (0.0-1.0)
4. Line range that was modified

Format your response as JSON.
"""

    def _parse_analysis_result(self, result: str) -> Dict:
        """解析分析结果"""
        try:
            # 尝试解析 JSON
            return json.loads(result)
        except json.JSONDecodeError:
            # 如果不是 JSON，尝试提取关键信息
            return {
                "raw_response": result,
                "error_type": "unknown",
                "suggestions": []
            }

    def _parse_fix_result(self, result: str, file_path: str) -> FixSuggestion:
        """解析修复结果"""
        try:
            data = json.loads(result)
            return FixSuggestion(
                original_code="",  # 可以从文件中读取
                fixed_code=data.get("fixed_code", ""),
                explanation=data.get("explanation", ""),
                confidence=float(data.get("confidence", 0.0)),
                file_path=file_path,
                line_range=tuple(data.get("line_range", [0, 0]))
            )
        except (json.JSONDecodeError, ValueError):
            return FixSuggestion(
                original_code="",
                fixed_code="",
                explanation="Failed to parse fix result",
                confidence=0.0,
                file_path=file_path,
                line_range=(0, 0)
            )


class TestFailureParser:
    """测试失败日志解析器"""

    @staticmethod
    def parse_pytest_output(pytest_output: str) -> List[TestFailure]:
        """解析 pytest 输出，提取测试失败信息"""
        failures = []

        # 使用正则表达式匹配失败测试 - 支持现代 pytest 格式
        failure_pattern = r"FAILED\s+(.+?)\n(.*?)(?=FAILED\s+|\n=+|$)"
        matches = re.findall(failure_pattern, pytest_output, re.DOTALL)

        for test_name, failure_content in matches:
            failure = TestFailureParser._parse_single_failure(test_name, failure_content)
            if failure:
                failures.append(failure)

        return failures

    @staticmethod
    def _parse_single_failure(test_name: str, failure_content: str) -> Optional[TestFailure]:
        """解析单个测试失败"""
        try:
            # 提取文件路径
            file_match = re.search(r'File "([^"]+)"', failure_content)
            file_path = file_match.group(1) if file_match else "unknown"

            # 提取错误类型
            error_match = re.search(r"(\w+):", failure_content.split('\n')[-1])
            error_type = error_match.group(1) if error_match else "UnknownError"

            # 提取错误消息
            error_lines = failure_content.split('\n')
            error_message = error_lines[-1] if error_lines else ""

            # 提取行号
            line_match = re.search(r"line (\d+)", failure_content)
            line_number = int(line_match.group(1)) if line_match else None

            return TestFailure(
                file_path=file_path,
                test_name=test_name,
                error_type=error_type,
                error_message=error_message,
                traceback=failure_content,
                line_number=line_number
            )

        except Exception as e:
            logger.error(f"Failed to parse test failure: {e}")
            return None


def main():
    """主函数 - 用于测试"""
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 测试包装器
    wrapper = ClaudeCodeWrapper()

    # 创建测试失败示例
    test_failure = TestFailure(
        file_path="tests/test_example.py",
        test_name="test_example_function",
        error_type="AssertionError",
        error_message="assert False",
        traceback="Full traceback here...",
        line_number=10
    )

    # 分析测试失败
    print("🔍 Analyzing test failure...")
    analysis = wrapper.analyze_test_failure(test_failure)
    print(f"Analysis result: {analysis}")

    # 生成修复
    print("🔧 Generating fix...")
    fix_suggestion = wrapper.generate_fix(test_failure, analysis)
    print(f"Fix suggestion: {fix_suggestion}")

    # 验证修复
    print("✅ Validating fix...")
    is_valid = wrapper.validate_fix(fix_suggestion)
    print(f"Fix is valid: {is_valid}")


if __name__ == "__main__":
    main()