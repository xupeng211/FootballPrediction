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
    print("🧪 测试1: 作业项目创建")
    print("-" * 40)

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
        print("✅ 作业项目创建成功")
        print(f"   ID: {work_item.id}")
        print(f"   标题: {work_item.title}")
        print(f"   类型: {work_item.work_type}")
        print(f"   状态: {work_item.status}")

        return work_item

    except Exception as e:
        print(f"❌ 作业项目创建失败: {e}")
        return None


def test_work_item_completion():
    """测试作业项目完成"""
    print("\n🧪 测试2: 作业项目完成")
    print("-" * 40)

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
            print("✅ 作业项目完成成功")

            # 验证完成状态
            work_items = synchronizer.load_work_log()
            completed_item = next((item for item in work_items if item.id == "test_work_001"), None)

            if completed_item:
                print(f"   状态: {completed_item.status}")
                print(f"   完成度: {completed_item.completion_percentage}%")
                print(f"   工作时长: {completed_item.time_spent_minutes}分钟")
                print(f"   交付成果: {len(completed_item.deliverables)}项")
                return True
            else:
                print("❌ 无法找到已完成的作业项目")
                return False
        else:
            print("❌ 作业项目完成失败")
            return False

    except Exception as e:
        print(f"❌ 作业项目完成测试失败: {e}")
        return False


def test_issue_body_generation():
    """测试Issue正文生成"""
    print("\n🧪 测试3: Issue正文生成")
    print("-" * 40)

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
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"   {status} {check_name}")
                if not passed:
                    all_passed = False

            if all_passed:
                print("✅ Issue正文生成成功，包含所有必需元素")
                print(f"   正文长度: {len(issue_body)}字符")
                return True
            else:
                print("❌ Issue正文生成不完整")
                return False
        else:
            print("❌ 无法找到测试作业项目")
            return False

    except Exception as e:
        print(f"❌ Issue正文生成测试失败: {e}")
        return False


def test_data_persistence():
    """测试数据持久化"""
    print("\n🧪 测试4: 数据持久化")
    print("-" * 40)

    try:
        # 检查文件是否存在
        work_log_file = project_root / "claude_work_log.json"

        if work_log_file.exists():
            print("✅ 作业日志文件存在")

            # 验证文件内容
            with open(work_log_file, encoding='utf-8') as f:
                data = json.load(f)

            print(f"   记录数量: {len(data)}")

            # 检查测试数据
            test_item = next((item for item in data if item["id"] == "test_work_001"), None)
            if test_item:
                print("✅ 测试作业项目持久化成功")
                print(f"   ID: {test_item['id']}")
                print(f"   标题: {test_item['title']}")
                print(f"   状态: {test_item['status']}")
                return True
            else:
                print("❌ 测试作业项目未在持久化数据中找到")
                return False
        else:
            print("❌ 作业日志文件不存在")
            return False

    except Exception as e:
        print(f"❌ 数据持久化测试失败: {e}")
        return False


def test_github_cli_connection():
    """测试GitHub CLI连接"""
    print("\n🧪 测试5: GitHub CLI连接")
    print("-" * 40)

    try:
        synchronizer = ClaudeWorkSynchronizer()

        # 测试基本命令
        result = synchronizer.run_gh_command(["--version"])
        if result["success"]:
            print("✅ GitHub CLI可访问")
            print(f"   版本: {result['stdout']}")
        else:
            print("❌ GitHub CLI不可访问")
            return False

        # 测试认证状态
        auth_result = synchronizer.run_gh_command(["auth", "status"])
        if auth_result["success"]:
            print("✅ GitHub CLI已认证")
            print("   认证状态: 正常")
        else:
            print("❌ GitHub CLI未认证")
            print(f"   错误: {auth_result['stderr']}")
            return False

        # 测试仓库访问
        repo_result = synchronizer.run_gh_command(["repo", "view", "--json", "name"])
        if repo_result["success"]:
            repo_data = json.loads(repo_result["stdout"])
            print("✅ 仓库访问正常")
            print(f"   仓库名称: {repo_data.get('name', 'Unknown')}")
            return True
        else:
            print("❌ 仓库访问失败")
            print(f"   错误: {repo_result['stderr']}")
            return False

    except Exception as e:
        print(f"❌ GitHub CLI连接测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试6: 错误处理")
    print("-" * 40)

    error_tests = []

    try:
        synchronizer = ClaudeWorkSynchronizer()

        # 测试1: 无效作业ID
        print("   测试无效作业ID...")
        result = synchronizer.complete_work_item("invalid_id")
        error_tests.append(("无效作业ID处理", not result))

        # 测试2: 空作业日志
        print("   测试空作业日志...")
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

        print("✅ 错误处理测试完成")
        print(f"   通过: {passed}/{total}")

        for test_name, result in error_tests:
            status = "✅" if result else "❌"
            print(f"   {status} {test_name}")

        return passed == total

    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


def cleanup_test_data():
    """清理测试数据"""
    print("\n🧹 清理测试数据")
    print("-" * 40)

    try:
        synchronizer = ClaudeWorkSynchronizer()
        work_items = synchronizer.load_work_log()

        # 移除测试数据
        original_count = len(work_items)
        work_items = [item for item in work_items if not item.id.startswith("test_")]
        synchronizer.save_work_log(work_items)

        removed_count = original_count - len(work_items)
        print(f"✅ 清理完成，移除了 {removed_count} 个测试作业项目")

        return True

    except Exception as e:
        print(f"❌ 清理测试数据失败: {e}")
        return False


def run_validation_suite():
    """运行完整的验证测试套件"""
    print("🔍 Claude Code 作业同步系统验证测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目路径: {project_root}")
    print("=" * 80)

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
    print("\n" + "=" * 80)
    print("📊 验证测试总结报告")
    print("=" * 80)

    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    failed_tests = total_tests - passed_tests

    print("📈 测试统计:")
    print(f"   总测试数: {total_tests}")
    print(f"   通过测试: {passed_tests}")
    print(f"   失败测试: {failed_tests}")
    print(f"   成功率: {(passed_tests/total_tests*100):.1f}%")

    print("\n📋 详细结果:")
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        test_display_name = {
            "work_creation": "作业项目创建",
            "work_completion": "作业项目完成",
            "issue_generation": "Issue正文生成",
            "data_persistence": "数据持久化",
            "github_cli": "GitHub CLI连接",
            "error_handling": "错误处理"
        }
        print(f"   {status} {test_display_name.get(test_name, test_name)}")

    # 总体评估
    print("\n🎯 系统可用性评估:")
    if failed_tests == 0:
        print("   🎉 系统完全可用，所有功能正常")
        overall_status = "EXCELLENT"
    elif failed_tests <= 2:
        print("   ✅ 系统基本可用，有小问题需要注意")
        overall_status = "GOOD"
    else:
        print("   ⚠️ 系统存在多个问题，需要修复后使用")
        overall_status = "NEEDS_ATTENTION"

    print("\n🚀 建议:")
    if overall_status == "EXCELLENT":
        print("   🎯 可以开始使用: make claude-start-work")
        print("   📋 查看帮助: make claude-list-work")
        print("   🔗 同步作业: make claude-sync")
    elif overall_status == "GOOD":
        print("   🔧 解决小问题后即可正常使用")
        print("   🎯 可以尝试基础功能")
    else:
        print("   🔧 请先解决关键问题")
        print("   📖 查看详细错误信息")
        print("   🛠️ 考虑重新安装依赖")

    print(f"\n🕐 验证完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

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

        print(f"\n📄 详细验证报告已保存到: {report_file}")

        # 返回适当的退出码
        if results["status"] == "EXCELLENT":
            sys.exit(0)
        elif results["status"] == "GOOD":
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 验证过程被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 验证过程失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
