#!/usr/bin/env python3
"""
修复 repositories.py 中所有的参数顺序问题
"""

import re


def fix_all_parameter_order():
    with open("src/api/repositories.py", "r") as f:
        content = f.read()

    # 使用更通用的模式：将所有 RepoDep 参数移到前面
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 检查是否是函数定义行
        if "async def " in line and "(" in line and "RepoDep" in lines[i + 1 : i + 10]:
            # 找到函数开始和结束
            func_lines = []
            j = i
            while j < len(lines) and not (
                lines[j].strip().endswith("]:") and "Dict" in lines[j]
            ):
                func_lines.append(lines[j])
                j += 1
            if j < len(lines):
                func_lines.append(lines[j])  # 添加返回类型行
                j += 1

            # 重新排序参数
            func_text = "\n".join(func_lines)

            # 提取参数列表
            param_match = re.search(
                r"async def \w+\((.*?)\) -> Dict\[str, Any\]:", func_text, re.DOTALL
            )
            if param_match:
                params = param_match.group(1)

                # 分割参数
                param_lines = [p.strip() for p in params.split(",\n") if p.strip()]

                # 分离依赖参数和其他参数
                dep_params = []
                other_params = []

                for param in param_lines:
                    if "RepoDep" in param:
                        dep_params.append(param)
                    else:
                        other_params.append(param)

                # 重新组合：依赖参数在前，然后是其他参数
                new_params = dep_params + other_params
                new_param_text = ",\n    ".join(new_params)

                # 替换函数定义
                new_func_text = re.sub(
                    r"async def \w+\(.*?\) -> Dict\[str, Any\]:",
                    lambda m: m.group(0).replace(params, new_param_text),
                    func_text,
                    flags=re.DOTALL,
                )

                new_lines.extend(new_func_text.split("\n"))
                i = j
            else:
                new_lines.append(line)
                i += 1
        else:
            new_lines.append(line)
            i += 1

    content = "\n".join(new_lines)

    with open("src/api/repositories.py", "w") as f:
        f.write(content)

    print("所有参数顺序修复完成")


if __name__ == "__main__":
    fix_all_parameter_order()
