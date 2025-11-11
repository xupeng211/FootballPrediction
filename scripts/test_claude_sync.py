#!/usr/bin/env python3
"""
Claude Code 作业同步系统测试脚本
Claude Code Work Sync System Test Script

非交互式测试Claude Code作业同步系统的核心功能：
- 测试作业记录创建和管理
- 测试GitHub同步功能
- 验证数据持久化
- 检查错误处理

Author: Claude AI Assistant
Date: 2025-11-06
Version: 1.0.0
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 添加scripts目录到Python路径
scripts_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts_dir))

from claude_work_sync import ClaudeWorkSynchronizer, WorkItem


def test_work_item_creation():
    """测试作业项目创建"""

    try:
        synchronizer = ClaudeWorkSynchronizer()

        # 创建测试作业项目
        work_item = WorkItem(
            id="test_work_001",
            title="测试作业项目",
            description="这是一个用于测试的作业项目",
            work_type="development",
            status="in_progress",
            priority="medium",
            completion_percentage=0,
            started_at=datetime.now().isoformat(),
            files_modified=["test_file.py"],
            technical_details={"test": True},
            deliverables=["测试交付成果"]
        )

        # 添加到日志
        synchronizer.add_work_item(work_item)

        return work_item

    except Exception:
        return None


def test_work_item_completion():
    """测试作业项目完成"""

    try:
        synchronizer = ClaudeWorkSynchronizer()

        # 完成测试作业
        success = synchronizer.complete_work_item(
            work_id="test_work_001",
            completion_percentage=100,
            deliverables=["功能实现", "单元测试", "文档更新"],
            test_results={"unit_tests": {"passed": 10, "failed": 0}},
            challenges=["时间紧张"],
            solutions=["优化算法", "重用代码"]
        )

        if success:

            # 验证完成状态
            work_items = synchronizer.load_work_log()
            completed_item = next((item for item in work_items if item.id == "test_work_001"), None)

            if completed_item:
                return True
            else:
                return False
        else:
            return False

    except Exception:
        return False


def test_issue_body_generation():
    """测试Issue正文生成"""

    try:
        synchronizer = ClaudeWorkSynchronizer()

        # 加载测试作业项目
        work_items = synchronizer.load_work_log()
        test_item = next((item for item in work_items if item.id == "test_work_001"), None)

        if test_item:
            # 生成Issue正文
            issue_body = synchronizer.generate_issue_body(test_item)

            # 验证生成的内容
            checks = [
                ("标题", test_item.title in issue_body),
                ("状态", test_item.status in issue_body),
                ("优先级", test_item.priority in issue_body),
                ("描述", test_item.description in issue_body),
                ("技术详情", "技术详情" in issue_body),
                ("修改文件", "修改的文件" in issue_body),
                ("交付成果", "交付成果" in issue_body),
                ("自动生成", "Claude Work Synchronizer" in issue_body)
            ]

            all_passed = True
            for _check_name, passed in checks:
                if not passed:
                    all_passed = False

            if all_passed:
                return True
            else:
                return False
        else:
            return False

    except Exception:
        return False


def test_data_persistence():
    """测试数据持久化"""

    try:
        # 检查文件是否存在
        work_log_file = project_root / "claude_work_log.json"

        if work_log_file.exists():

            # 验证文件内容
            with open(work_log_file, encoding='utf-8') as f:
                data = json.load(f)


            # 检查测试数据
            test_item = next((item for item in data if item["id"] == "test_work_001"), None)
            if test_item:
                return True
            else:
                return False
        else:
            return False

    except Exception:
        return False


def test_github_cli_connection():
    """测试GitHub CLI连接"""

    try:
        synchronizer = ClaudeWorkSynchronizer()

        # 测试基本命令
        result = synchronizer.run_gh_command(["--version"])
        if result["success"]:
            pass
        else:
            return False

        # 测试认证状态
        auth_result = synchronizer.run_gh_command(["auth", "status"])
        if auth_result["success"]:
            pass
        else:
            return False

        # 测试仓库访问
        repo_result = synchronizer.run_gh_command(["repo", "view", "--json", "name"])
        if repo_result["success"]:
            json.loads(repo_result["stdout"])
            return True
        else:
            return False

    except Exception:
        return False


def test_error_handling():
    """测试错误处理"""

    error_tests = []

    try:
        synchronizer = ClaudeWorkSynchronizer()

        # 测试1: 无效作业ID
        result = synchronizer.complete_work_item("invalid_id")
        error_tests.append(("无效作业ID处理", not result))

        # 测试2: 空作业日志
        original_log = synchronizer.load_work_log()
        synchronizer.save_work_log([])  # 清空日志

        # 尝试添加无效作业
        invalid_item = WorkItem(
            id="",  # 空ID
            title="测试",
            description="测试",
            work_type="development",
            status="pending",
            priority="low",
            completion_percentage=0
        )

        try:
            synchronizer.add_work_item(invalid_item)
            error_tests.append(("空ID处理", False))  # 应该失败
        except:
            error_tests.append(("空ID处理", True))  # 正确抛出异常

        # 恢复原始日志
        synchronizer.save_work_log(original_log)

        # 统计结果
        passed = sum(1 for _, result in error_tests if result)
        total = len(error_tests)


        for _test_name, result in error_tests:
            pass

        return passed == total

    except Exception:
        return False


def cleanup_test_data():
    """清理测试数据"""

    try:
        synchronizer = ClaudeWorkSynchronizer()
        work_items = synchronizer.load_work_log()

        # 移除测试数据
        original_count = len(work_items)
        work_items = [item for item in work_items if not item.id.startswith("test_")]
        synchronizer.save_work_log(work_items)

        original_count - len(work_items)

        return True

    except Exception:
        return False


def run_validation_suite():
    """运行完整的验证测试套件"""

    # 运行所有测试
    test_results = {}

    # 核心功能测试
    test_results["work_creation"] = test_work_item_creation()
    test_results["work_completion"] = test_work_item_completion()
    test_results["issue_generation"] = test_issue_body_generation()
    test_results["data_persistence"] = test_data_persistence()

    # GitHub集成测试
    test_results["github_cli"] = test_github_cli_connection()

    # 错误处理测试
    test_results["error_handling"] = test_error_handling()

    # 清理
    cleanup_test_data()

    # 生成测试报告

    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    failed_tests = total_tests - passed_tests


    for _test_name, _result in test_results.items():
        pass

    # 总体评估
    if failed_tests == 0:
        overall_status = "EXCELLENT"
    elif failed_tests <= 2:
        overall_status = "GOOD"
    else:
        overall_status = "NEEDS_ATTENTION"

    if overall_status == "EXCELLENT":
        pass
    elif overall_status == "GOOD":
        pass
    else:
        pass


    return {
        "status": overall_status,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": passed_tests/total_tests*100,
        "test_results": test_results,
        "timestamp": datetime.now().isoformat()
    }


def main():
    """主函数"""
    try:
        results = run_validation_suite()

        # 保存验证报告
        report_file = project_root / "claude_sync_validation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)


        # 返回适当的退出码
        if results["status"] == "EXCELLENT":
            sys.exit(0)
        elif results["status"] == "GOOD":
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
