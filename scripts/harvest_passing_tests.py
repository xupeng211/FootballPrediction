#!/usr/bin/env python3
"""
🌾 The Test Harvester - 自动化测试收割工具
Automated Test Recovery Tool

功能：
- 扫描 skipped_tests.txt 中的所有测试文件
- 自动检测哪些测试实际上已经通过
- 从跳过列表中移除"冤假错案"
- 量化技术债务回收成果

作者：自动化测试工程师
版本：v1.0
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse


class TestHarvester:
    """测试收割器 - 自动恢复通过的测试"""

    def __init__(self, skipped_tests_file: str, dry_run: bool = False):
        self.skipped_tests_file = skipped_tests_file
        self.dry_run = dry_run
        self.harvested_files = []
        self.failed_files = []
        self.stats = {
            "total_files_scanned": 0,
            "files_harvested": 0,
            "files_still_failing": 0,
            "total_tests_recovered": 0,
            "execution_time": 0,
        }

    def extract_unique_test_files(self) -> set[str]:
        """从skipped_tests.txt中提取唯一的测试文件路径"""
        if not os.path.exists(self.skipped_tests_file):
            return set()

        test_files = set()

        with open(self.skipped_tests_file, encoding="utf-8") as f:
            for _line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                # 解析不同格式的测试路径
                # 格式1: "ERROR tests/unit/api/test_auth.py::TestClass::test_method"
                # 格式2: "tests/unit/utils/test_formatters.py"
                # 格式3: "FAILED tests/unit/api/test_auth.py::test_method"

                test_path = None
                if line.startswith("ERROR "):
                    test_path = line[6:].strip()
                elif line.startswith("FAILED "):
                    test_path = line[7:].strip()
                elif "::" in line and ".py::" in line:
                    test_path = line
                elif line.endswith(".py") or line.startswith("tests/"):
                    test_path = line

                if test_path:
                    # 提取文件路径（去除测试方法和类）
                    file_path = self._extract_file_path(test_path)
                    if file_path and os.path.exists(file_path):
                        test_files.add(file_path)

        return test_files

    def _extract_file_path(self, test_path: str) -> str | None:
        """从测试路径中提取文件路径"""
        # 移除ERROR/FAILED前缀
        test_path = re.sub(r"^(ERROR|FAILED) ", "", test_path).strip()

        # 如果已经是文件路径，直接返回
        if test_path.endswith(".py") and "::" not in test_path:
            return test_path

        # 如果包含 ::，提取文件部分
        if "::" in test_path:
            file_part = test_path.split("::")[0]
            if file_part.endswith(".py"):
                return file_part

        # 如果以 tests/ 开头但不是完整路径
        if test_path.startswith("tests/"):
            if "::" in test_path:
                return test_path.split("::")[0]
            elif test_path.endswith(".py"):
                return test_path

        return None

    def run_test_file(self, test_file: str) -> tuple[bool, str]:
        """运行单个测试文件并返回结果"""
        try:
            # 运行pytest，静默模式，只关心退出码
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "--tb=no", "-q"],
                capture_output=True,
                text=True,
                timeout=60,  # 60秒超时
            )

            if result.returncode == 0:
                # 测试通过！
                passed_tests = self._count_tests_in_output(result.stdout)
                return True, f"✅ 通过 ({passed_tests} 个测试)"
            else:
                # 测试失败
                failed_tests = self._count_tests_in_output(result.stdout)
                error_msg = (
                    result.stderr.strip() if result.stderr else result.stdout.strip()
                )
                return False, f"❌ 失败 ({failed_tests} 个测试) - {error_msg[:100]}"

        except subprocess.TimeoutExpired:
            return False, "❌ 超时"
        except Exception:
            return False, f"❌ 异常: {str(e)[:50]}"

    def _count_tests_in_output(self, output: str) -> int:
        """从pytest输出中计算测试数量"""
        # pytest输出格式通常包含: "passed", "failed", "skipped", "error"
        count = 0
        patterns = [
            r"(\d+)\s+passed",
            r"(\d+)\s+failed",
            r"(\d+)\s+skipped",
            r"(\d+)\s+error",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, output)
            if matches:
                count += sum(int(m) for m in matches)

        return max(count, 1)  # 至少1个测试

    def harvest_passing_tests(self):
        """执行测试收割"""

        start_time = datetime.now()

        # 获取所有唯一的测试文件
        test_files = self.extract_unique_test_files()
        self.stats["total_files_scanned"] = len(test_files)

        if not test_files:
            return

        # 按模块分组显示进度
        modules = defaultdict(list)
        for test_file in test_files:
            module = self._get_module_name(test_file)
            modules[module].append(test_file)

        for _module, _files in sorted(modules.items()):
            pass

        # 逐个检查测试文件
        for _i, test_file in enumerate(sorted(test_files), 1):
            module = self._get_module_name(test_file)

            success, message = self.run_test_file(test_file)

            if success:
                self.harvested_files.append((test_file, message))
                self.stats["files_harvested"] += 1

                # 如果不是演练模式，立即从跳过列表中移除
                if not self.dry_run:
                    self._remove_file_from_skip_list(test_file)

            else:
                self.failed_files.append((test_file, message))
                self.stats["files_still_failing"] += 1

        end_time = datetime.now()
        self.stats["execution_time"] = (end_time - start_time).total_seconds()

        # 计算恢复的测试总数
        self.stats["total_tests_recovered"] = sum(
            self._extract_test_count_from_message(msg)
            for _, msg in self.harvested_files
        )

    def _get_module_name(self, test_file: str) -> str:
        """从文件路径提取模块名"""
        if "tests/unit/" in test_file:
            parts = test_file.split("tests/unit/")[1].split("/")
            return parts[0] if parts else "unknown"
        elif "tests/integration/" in test_file:
            return "integration"
        elif "tests/e2e/" in test_file:
            return "e2e"
        else:
            return "unknown"

    def _extract_test_count_from_message(self, message: str) -> int:
        """从消息中提取测试数量"""
        match = re.search(r"\((\d+)\s+个测试\)", message)
        return int(match.group(1)) if match else 1

    def _remove_file_from_skip_list(self, test_file: str):
        """从跳过列表中移除文件的所有相关条目"""
        try:
            # 读取原文件内容
            with open(self.skipped_tests_file, encoding="utf-8") as f:
                lines = f.readlines()

            # 过滤掉相关条目
            filtered_lines = []
            removed_count = 0

            for line in lines:
                line = line.strip()
                if line and test_file in line:
                    removed_count += 1
                    continue
                filtered_lines.append(line)

            # 写回文件
            with open(self.skipped_tests_file, "w", encoding="utf-8") as f:
                for line in filtered_lines:
                    if line.strip():  # 只写入非空行
                        f.write(line + "\n")

        except Exception:
            pass

    def print_summary(self):
        """打印收割总结报告"""

        if self.stats["files_harvested"] > 0:
            (self.stats["files_harvested"] / self.stats["total_files_scanned"]) * 100

        if self.harvested_files:
            for test_file, _message in self.harvested_files:
                self._get_module_name(test_file)

        if self.failed_files:
            for test_file, _message in self.failed_files[:10]:
                self._get_module_name(test_file)

            if len(self.failed_files) > 10:
                pass

        # 给出下一步建议
        if self.stats["files_harvested"] > 0:
            pass

        if self.stats["files_still_failing"] > 0:
            pass


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动化测试收割工具")
    parser.add_argument(
        "--dry-run", action="store_true", help="演练模式：只检查不实际修改文件"
    )
    parser.add_argument(
        "--skip-file",
        default="tests/skipped_tests.txt",
        help="跳过测试文件路径 (默认: tests/skipped_tests.txt)",
    )

    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.skip_file):
        sys.exit(1)

    # 创建收割器实例
    harvester = TestHarvester(args.skip_file, args.dry_run)

    try:
        # 执行收割
        harvester.harvest_passing_tests()

        # 打印总结
        harvester.print_summary()

        # 返回适当的退出码
        if harvester.stats["files_harvested"] > 0:
            if args.dry_run:
                pass
            else:
                pass
            sys.exit(0)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        sys.exit(1)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
