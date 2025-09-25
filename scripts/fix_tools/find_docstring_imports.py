#!/usr/bin/env python3
"""
查找文档字符串内错误放置的导入语句
"""

import os
import re


def find_docstring_imports(filepath):
    """查找文档字符串内的导入语句"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 查找文档字符串
        docstring_pattern = r'"""(.*?)"""'
        matches = re.findall(docstring_pattern, content, re.DOTALL)

        issues = []
        for i, docstring in enumerate(matches):
            # 在文档字符串中查找导入语句
            import_lines = []
            for line in docstring.split("\n"):
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")) and "import" in stripped:
                    import_lines.append(stripped)

            if import_lines:
                issues.append(
                    {
                        "docstring_index": i,
                        "imports": import_lines,
                        "docstring_preview": docstring[:100].replace("\n", " "),
                    }
                )

        return issues

    except Exception:
        return []


def main():
    """主函数"""
    print("扫描所有Python文件...")

    all_files = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                all_files.append(os.path.join(root, file))

    print(f"找到 {len(all_files)} 个Python文件")

    issues_found = {}
    total_issues = 0

    for filepath in all_files:
        issues = find_docstring_imports(filepath)
        if issues:
            issues_found[filepath] = issues
            total_issues += len(issues)

    print(f"\n发现 {total_issues} 个文档字符串导入问题，涉及 {len(issues_found)} 个文件\n")

    for filepath, issues in issues_found.items():
        print(f"📁 {filepath}")
        for issue in issues:
            print(f"  📜 文档字符串 {issue['docstring_index']}: {issue['docstring_preview']}")
            for imp in issue["imports"]:
                print(f"    ❌ {imp}")
        print()


if __name__ == "__main__":
    main()
