#!/usr/bin/env python3
"""
Claude Code 作业同步系统演示脚本
Claude Code Work Sync System Demo Script

演示完整的作业记录和同步流程：
- 创建测试作业项目
- 模拟开发过程
- 完成作业记录
- 生成同步预览

Author: Claude AI Assistant
Date: 2025-11-06
Version: 1.0.0
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from claude_work_sync import ClaudeWorkSynchronizer, WorkItem


def demo_workflow():
    """演示完整的工作流程"""
    print("🎭 Claude Code 作业同步系统演示")
    print("=" * 60)
    print("这个演示将展示系统的完整使用流程")
    print("=" * 60)

    synchronizer = ClaudeWorkSynchronizer()

    # 步骤1: 模拟开始新作业
    print("\n📝 步骤1: 开始新的作业项目")
    print("-" * 40)

    # 创建示例作业项目
    work_item = WorkItem(
        id=f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        title="演示：实现用户认证功能",
        description="这是一个演示作业，展示如何使用Claude Code作业同步系统记录开发工作。我们将实现一个基础的用户认证系统，包括JWT令牌、登录注册API和权限验证。",
        work_type="feature",
        status="in_progress",
        priority="high",
        completion_percentage=0,
        started_at=datetime.now().isoformat(),
        files_modified=[
            "src/api/auth.py",
            "src/models/user.py",
            "src/middleware/jwt_auth.py",
            "tests/test_auth.py"
        ],
        technical_details={
            "git_branch": "feature/user-auth",
            "latest_commit": "abc123def456",
            "tech_stack": ["FastAPI", "JWT", "Pydantic", "SQLAlchemy"],
            "dependencies_added": ["python-jose[cryptography]", "passlib[bcrypt]"]
        }
    )

    synchronizer.add_work_item(work_item)
    print(f"✅ 作业项目已创建")
    print(f"   ID: {work_item.id}")
    print(f"   标题: {work_item.title}")
    print(f"   类型: {work_item.work_type}")
    print(f"   优先级: {work_item.priority}")
    print(f"   状态: {work_item.status}")
    print(f"   修改文件: {len(work_item.files_modified)}个")

    # 步骤2: 模拟开发过程
    print("\n⚙️ 步骤2: 模拟开发过程")
    print("-" * 40)

    development_steps = [
        "设计数据库用户表结构",
        "实现用户注册API端点",
        "实现JWT令牌生成和验证",
        "创建登录认证中间件",
        "编写权限验证装饰器",
        "添加输入验证和错误处理",
        "编写单元测试用例"
    ]

    for i, step in enumerate(development_steps, 1):
        print(f"   {i}. {step}")
        # 模拟开发时间
        import time
        time.sleep(0.5)

    print("✅ 开发过程完成")

    # 步骤3: 完成作业
    print("\n✅ 步骤3: 完成作业项目")
    print("-" * 40)

    # 模拟交付成果
    deliverables = [
        "JWT认证中间件 - 支持Bearer token验证",
        "用户注册API - /api/auth/register",
        "用户登录API - /api/auth/login",
        "权限验证装饰器 - @require_auth",
        "用户模型和数据库表 - User model",
        "完整的单元测试 - 测试覆盖率85%",
        "API文档更新 - Swagger自动生成"
    ]

    test_results = {
        "unit_tests": {
            "total": 45,
            "passed": 43,
            "failed": 2,
            "coverage": "85.2%"
        },
        "integration_tests": {
            "total": 12,
            "passed": 12,
            "failed": 0
        },
        "security_tests": {
            "sql_injection": "passed",
            "xss_prevention": "passed",
            "jwt_validation": "passed"
        }
    }

    challenges = [
        "JWT令牌刷新逻辑复杂",
        "密码安全性要求高",
        "API性能优化需要考虑",
        "测试数据库隔离配置"
    ]

    solutions = [
        "使用PyJWT库简化JWT处理",
        "采用bcrypt进行密码哈希",
        "实现令牌缓存机制",
        "使用pytest fixtures进行测试隔离"
    ]

    next_steps = [
        "添加多因素认证支持",
        "实现社交登录集成",
        "优化API响应性能",
        "添加审计日志功能"
    ]

    success = synchronizer.complete_work_item(
        work_id=work_item.id,
        completion_percentage=100,
        deliverables=deliverables,
        test_results=test_results,
        challenges=challenges,
        solutions=solutions,
        next_steps=next_steps
    )

    if success:
        print("✅ 作业项目完成")
        print(f"   交付成果: {len(deliverables)}项")
        print(f"   测试结果: {test_results['unit_tests']['passed']}/{test_results['unit_tests']['total']} 单元测试通过")
        print(f"   代码覆盖率: {test_results['unit_tests']['coverage']}")
        print(f"   安全测试: {len(test_results['security_tests'])}项通过")

    # 步骤4: 生成GitHub Issue预览
    print("\n📄 步骤4: 生成GitHub Issue内容预览")
    print("-" * 40)

    # 重新加载更新后的作业项目
    work_items = synchronizer.load_work_log()
    completed_item = next((item for item in work_items if item.id == work_item.id), None)

    if completed_item:
        issue_body = synchronizer.generate_issue_body(completed_item)

        print("📋 GitHub Issue内容预览:")
        print("=" * 50)
        # 只显示前几行
        lines = issue_body.split('\n')
        for i, line in enumerate(lines[:30]):  # 显示前30行
            print(line)
        if len(lines) > 30:
            print("...")
            print(f"(总长度: {len(issue_body)} 字符)")
        print("=" * 50)

    # 步骤5: 显示工作统计
    print("\n📊 步骤5: 工作统计信息")
    print("-" * 40)

    if completed_item and completed_item.time_spent_minutes > 0:
        hours = completed_item.time_spent_minutes // 60
        minutes = completed_item.time_spent_minutes % 60
        print(f"⏱️ 工作时长: {hours}小时{minutes}分钟")

    print(f"📁 修改文件: {len(completed_item.files_modified) if completed_item else 0}个")
    print(f"🎯 交付成果: {len(deliverables)}项")
    print(f"🧪 测试覆盖: {test_results['unit_tests']['coverage']}")
    print(f"🔧 技术栈: {', '.join(completed_item.technical_details.get('tech_stack', [])) if completed_item else 'N/A'}")

    # 步骤6: 同步建议
    print("\n🚀 步骤6: 同步到GitHub")
    print("-" * 40)

    print("💡 现在你可以执行以下命令来同步到GitHub:")
    print()
    print("   make claude-sync")
    print()
    print("这将自动:")
    print("   • 在GitHub上创建或更新Issue")
    print("   • 添加适当的标签 (feature, priority/high, status/completed)")
    print("   • 包含完整的技术细节和交付成果")
    print("   • 由于作业已完成，Issue会自动关闭")
    print()
    print("📋 或者查看当前所有作业:")
    print()
    print("   make claude-list-work")

    # 保存演示结果
    demo_result = {
        "demo_id": work_item.id,
        "title": work_item.title,
        "work_type": work_item.work_type,
        "priority": work_item.priority,
        "deliverables": deliverables,
        "test_results": test_results,
        "files_modified": completed_item.files_modified if completed_item else [],
        "issue_length": len(issue_body) if completed_item else 0,
        "demo_timestamp": datetime.now().isoformat()
    }

    demo_file = project_root / "claude_sync_demo_result.json"
    with open(demo_file, 'w', encoding='utf-8') as f:
        json.dump(demo_result, f, indent=2, ensure_ascii=False)

    print(f"\n📄 演示结果已保存到: {demo_file}")

    # 清理演示数据
    print("\n🧹 清理演示数据")
    print("-" * 40)

    # 移除演示作业
    work_items = synchronizer.load_work_log()
    work_items = [item for item in work_items if not item.id.startswith("demo_")]
    synchronizer.save_work_log(work_items)

    print("✅ 演示数据已清理")

    print("\n" + "=" * 60)
    print("🎉 演示完成！现在你可以开始使用实际的作业记录功能")
    print("=" * 60)

    print("🚀 下一步操作建议:")
    print("   1. 开始你的真实作业: make claude-start-work")
    print("   2. 完成开发工作后: make claude-complete-work")
    print("   3. 同步到GitHub: make claude-sync")
    print("   4. 查看你的作业记录: make claude-list-work")

    return demo_result


def main():
    """主函数"""
    try:
        print("🎭 准备开始Claude Code作业同步系统演示...")

        # 确保环境就绪
        synchronizer = ClaudeWorkSynchronizer()

        print("✅ 环境检查完成，开始演示...")
        result = demo_workflow()

        print(f"\n🎯 演示成功完成！")
        print(f"   演示作业ID: {result['demo_id']}")
        print(f"   生成的Issue内容长度: {result['issue_length']}字符")

        return 0

    except KeyboardInterrupt:
        print("\n⚠️ 演示被用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())