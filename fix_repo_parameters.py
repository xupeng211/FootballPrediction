#!/usr/bin/env python3
"""
修复 repositories.py 中的参数顺序问题
"""

import re


def fix_parameter_order():
    with open("src/api/repositories.py", "r") as f:
        content = f.read()

    # 定义需要修复的模式
    patterns = [
        # pattern: function_name, params_to_reorder
        (
            r"(async def get_prediction\(\s*)(prediction_id: int,\s*repo: ReadOnlyPredictionRepoDep\s*)(\) -> Dict\[str, Any\]:)",
            r"\1repo: ReadOnlyPredictionRepoDep, prediction_id: int\3",
        ),
        (
            r"(async def get_match_predictions\(\s*)(match_id: int,\s*repo: ReadOnlyPredictionRepoDep\s*)(\) -> Dict\[str, Any\]:)",
            r"\1repo: ReadOnlyPredictionRepoDep, match_id: int\3",
        ),
        (
            r"(async def update_prediction\(\s*)(prediction_id: int,\s*update_data: Dict\[str, Any\],\s*repo: PredictionRepoDep\s*)(\) -> Dict\[str, Any\]:)",
            r"\1repo: PredictionRepoDep, prediction_id: int, update_data: Dict[str, Any]\3",
        ),
        (
            r"(async def get_user\(\s*)(user_id: int,\s*repo: ReadOnlyUserRepoDep\s*)(\) -> Dict\[str, Any\]:)",
            r"\1repo: ReadOnlyUserRepoDep, user_id: int\3",
        ),
        (
            r"(async def update_user\(\s*)(user_id: int,\s*repo: UserRepoDep\s*)(\) -> Dict\[str, Any\]:)",
            r"\1repo: UserRepoDep, user_id: int\3",
        ),
        (
            r"(async def get_match\(\s*)(match_id: int,\s*repo: ReadOnlyMatchRepoDep\s*)(\) -> Dict\[str, Any\]:)",
            r"\1repo: ReadOnlyMatchRepoDep, match_id: int\3",
        ),
        (
            r"(async def update_match\(\s*)(match_id: int,\s*repo: MatchRepoDep\s*)(\) -> Dict\[str, Any\]:)",
            r"\1repo: MatchRepoDep, match_id: int\3",
        ),
        (
            r"(async def start_match\(\s*)(match_id: int,\s*repo: MatchRepoDep\s*)(\) -> Dict\[str, Any\]:)",
            r"\1repo: MatchRepoDep, match_id: int\3",
        ),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

    with open("src/api/repositories.py", "w") as f:
        f.write(content)

    print("参数顺序修复完成")


if __name__ == "__main__":
    fix_parameter_order()
