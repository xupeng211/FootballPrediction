#!/usr/bin/env python3
"""
第三阶段启动：架构改进
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print("=" * 60)

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ 成功!")
        if result.stdout:
            print(result.stdout[:500])
            if len(result.stdout) > 500:
                print("...(输出截断)")
    else:
        print("❌ 失败!")
        if result.stderr:
            print(result.stderr[:500])

    return result.returncode == 0


def check_current_status():
    """检查当前状态"""
    print("\n📊 当前项目状态检查:")

    # 统计F401错误
    run_command("ruff check --select F401 src/ | wc -l", "统计F401错误数量")

    # 统计except Exception
    run_command(
        "grep -r 'except Exception' --include='*.py' src/ | wc -l",
        "统计except Exception数量",
    )

    # 统计TODO
    run_command(
        "grep -r 'TODO\\|FIXME' --include='*.py' src/ | wc -l", "统计TODO项数量"
    )

    # 查找长文件
    print("\n📊 最长的文件:")
    os.system(
        "find src -name '*.py' -not -path '*/__pycache__/*' -exec wc -l {} + | sort -n | tail -5"
    )

    # 统计文档
    print("\n📊 文档统计:")
    run_command(
        "find src -name '*.py' -exec grep -l '\"\"\"' {} \\; | wc -l",
        "有文档字符串的文件数",
    )

    # 类型注解检查
    print("\n📊 类型注解:")
    run_command(
        "find src -name '*.py' -exec grep -l 'def.*->' {} \\; | wc -l",
        "有类型注解的函数数",
    )


def show_phase3_tasks():
    """显示第三阶段任务"""
    print("\n" + "=" * 80)
    print("🏗️ 第三阶段：架构改进")
    print("=" * 80)

    print("\n📋 任务列表:")
    print("\n1. 📚 模块文档完善")
    print("   - 添加模块级文档字符串")
    print("   - 重点模块优先")
    print("   - API文档完善")

    print("\n2. 📦 依赖管理简化")
    print("   - 分析当前依赖（18个文件）")
    print("   - 设计新结构（简化为4个文件）")
    print("   - 合并重复依赖")

    print("\n3. 🎯 代码规范统一")
    print("   - 命名规范检查")
    print("   - 修复循环变量")
    print("   - 类型注解完善")

    print("\n4. 📝 文件重构")
    print("   - 继续重构长文件")
    print("   - 函数长度优化")
    print("   - 代码组织改进")


def start_phase3_task1():
    """开始第三阶段任务1：模块文档完善"""
    print("\n🚀 开始第三阶段任务1：模块文档完善")

    # 查找没有文档的文件
    print("\n📋 查找缺少文档的文件...")
    cmd = "find src -name '*.py' -not -path '*/__pycache__/*' | head -20"
    result = os.popen(cmd).read().strip()

    if result:
        files = result.split("\n")
        no_doc_files = []

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read(1000)  # 只读前1000个字符
                    if '"""' not in content:
                        no_doc_files.append(file_path)
            except Exception:
                pass

        print(f"\n发现 {len(no_doc_files)} 个文件缺少文档:")
        for f in no_doc_files[:10]:
            print(f"  - {f}")

        # 创建文档添加脚本
        print("\n📝 创建文档添加脚本...")
        create_documentation_script()
    else:
        print("\n✅ 所有文件都有文档！")


def create_documentation_script():
    """创建文档添加脚本"""
    script_content = '''#!/usr/bin/env python3
"""
为缺少文档的文件添加文档字符串
"""

import os
from pathlib import Path


def add_module_docstring(file_path):
    """为模块添加文档字符串"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 检查是否已有文档
        first_10_lines = ''.join(lines[:10])
        if '"""' in first_10_lines:
            print(f"  - {file_path}: 已有文档")
            return False

        # 找到第一个导入或类/函数定义
        first_code_line = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and (stripped.startswith(('import ', 'from ', 'class ', 'def ', 'async def '))):
                first_code_line = i
                break

        # 模块名
        module_name = file_path.replace('/', '.').replace('.py', '').replace('src.', '')
        module_name = module_name.replace('_', ' ').title()

        # 创建文档
        docstring = f'"""{module_name}

{generate_description(module_name)}

主要功能：
- [待补充]

使用示例：
    from {module_name} import [Class/Function]
    # [使用示例]

注意事项：
- [注意事项]
"""

        # 插入文档
        lines.insert(first_code_line, docstring + '\n\n')

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"  ❌ {file_path}: 错误 - {e}")
        return False


def generate_description(module_name):
    """生成模块描述"""
    descriptions = {
        'Api': 'API模块',
        'Core': '核心模块',
        'Database': '数据库模块',
        'Services': '服务模块',
        'Utils': '工具模块',
        'Cache': '缓存模块',
        'Monitoring': '监控模块',
        'Data': '数据处理模块',
        'Features': '特征工程模块',
        'Patterns': '设计模式模块',
        'Repositories': '仓储模块',
        'Adapters': '适配器模块',
        'Domain': '领域模型模块',
        'Tasks': '任务调度模块',
        'Scheduler': '调度器模块',
        'Streaming': '流处理模块',
        'Performance': '性能模块',
        'Realtime': '实时处理模块',
        'Stubs': '存根模块',
    }

    return descriptions.get(module_name, f'{module_name}模块')


def main():
    """主函数"""
    import sys
    if len(sys.argv) > 1:
        # 处理特定文件
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            add_module_docstring(file_path)
    else:
        # 处理所有文件
        src_path = Path("src")
        python_files = list(src_path.rglob("*.py"))

        fixed_count = 0
        for file_path in python_files:
            if add_module_docstring(file_path):
                fixed_count += 1
                print(f"✅ 已添加文档: {file_path}")

        print(f"\\n总计添加了 {fixed_count} 个文档")
'''

    script_path = Path("scripts/add_documentation.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    os.chmod(script_path, 0o755)
    print("  ✅ 创建脚本: scripts/add_documentation.py")
    print("\n💡 使用方法:")
    print("  python scripts/add_documentation.py")


def main():
    """主函数"""
    print("=" * 80)
    print("🏗️ 第三阶段启动：架构改进")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 检查当前状态
    check_current_status()

    # 显示任务
    show_phase3_tasks()

    # 开始任务1
    start_phase3_task1()

    print("\n" + "=" * 80)
    print("✅ 第三阶段已准备就绪！")
    print("=" * 80)

    print("\n📝 建议的下一步:")
    print("1. 运行: python scripts/add_documentation.py")
    print("2. 手动完善重要模块的文档")
    print("3. 开始依赖管理简化")
    print("4. 统一代码规范")


if __name__ == "__main__":
    main()
