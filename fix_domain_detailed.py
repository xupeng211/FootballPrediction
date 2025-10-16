#!/usr/bin/env python3
"""
详细修复domain模块的剩余语法错误
"""

import os
import re

def fix_domain_errors():
    """逐个修复domain模块的语法错误"""

    # 1. 修复 league.py
    print("修复 src/domain/models/league.py...")
    filepath = 'src/domain/models/league.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复括号不匹配问题
    content = re.sub(
        r'(\w+: Optional\[str]\] = None,)',
        r'\1',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 2. 修复 prediction.py
    print("修复 src/domain/models/prediction.py...")
    filepath = 'src/domain/models/prediction.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复未闭合的f-string
    content = re.sub(
        r'return f"\{self\.value\:\.2f" \(\{self\.level\}\)',
        r'return f"{self.value:.2f} ({self.level})"',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 3. 修复 team.py 的未闭合字符串
    print("修复 src/domain/models/team.py...")
    filepath = 'src/domain/models/team.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复最后的未闭合字符串
    content = re.sub(
        r'return f"\{self\.name\} \(\{self\.code or self\.short_name\}\) - \{self\.rank\}"$',
        r'return f"{self.name} ({self.code or self.short_name}) - {self.rank}"',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 4. 修复 match.py
    print("修复 src/domain/models/match.py...")
    filepath = 'src/domain/models/match.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复括号不匹配
    content = re.sub(
        r'(\w+: Optional\[.*?\]] = None)',
        r'\1',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 5. 修复 strategies/config.py
    print("修复 src/domain/strategies/config.py...")
    filepath = 'src/domain/strategies/config.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复返回类型注解
    content = re.sub(
        r'-> Optional\[Dict\[str, Any]\]:',
        r'-> Optional[Dict[str, Any]]:',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 6. 修复 strategies/base.py
    print("修复 src/domain/strategies/base.py...")
    filepath = 'src/domain/strategies/base.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复类型注解
    content = re.sub(
        r'(\w+: Optional\[.*?\]] = None)',
        r'\1',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 7. 修复 strategies/historical.py
    print("修复 src/domain/strategies/historical.py...")
    filepath = 'src/domain/strategies/historical.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复参数类型
    content = re.sub(
        r'(\w+: Dict\[str, Optional\[Tuple\[int, int\]\]\)',
        r'\1]',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 8. 修复 strategies/ensemble.py
    print("修复 src/domain/strategies/ensemble.py...")
    filepath = 'src/domain/strategies/ensemble.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复字典初始化
    content = re.sub(
        r': Dict\[str, PredictionStrategy\] = }\]',
        r': Dict[str, PredictionStrategy] = {}',
        content
    )
    content = re.sub(
        r': Dict\[str, StrategyWeight\] = }\]',
        r': Dict[str, StrategyWeight] = {}',
        content
    )
    content = re.sub(
        r': Dict\[str, List\[float\]\] = {]',
        r': Dict[str, List[float]] = {}',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 9. 修复 strategies/statistical.py
    print("修复 src/domain/strategies/statistical.py...")
    filepath = 'src/domain/strategies/statistical.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复参数类型
    content = re.sub(
        r'(\w+: Dict\[str, Tuple\[int, int\]\]\)',
        r'\1]',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 10. 修复 strategies/ml_model.py
    print("修复 src/domain/strategies/ml_model.py...")
    filepath = 'src/domain/strategies/ml_model.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复无效语法
    content = re.sub(
        r'(\w+: List\[Tuple\[Prediction, Dict\[str, Any\]\]\)',
        r'\1]',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 11. 修复 strategies/factory.py
    print("修复 src/domain/strategies/factory.py...")
    filepath = 'src/domain/strategies/factory.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复字典初始化
    content = re.sub(
        r'self\._strategies: Dict\[str, PredictionStrategy\] = }\]',
        r'self._strategies: Dict[str, PredictionStrategy] = {}',
        content
    )
    content = re.sub(
        r'self\._strategy_configs: Dict\[str, Union\[str, Dict\[str, Any\]\]\] = {]',
        r'self._strategy_configs: Dict[str, Union[str, Dict[str, Any]]] = {}',
        content
    )
    content = re.sub(
        r'self\._default_config: Dict\[str, Any\] = }\]',
        r'self._default_config: Dict[str, Any] = {}',
        content
    )
    content = re.sub(
        r'self\._environment_overrides: Dict\[str, Any\] = }\]',
        r'self._environment_overrides: Dict[str, Any] = {}',
        content
    )
    # 修复类型注解
    content = re.sub(
        r'Dict\[str, Type\[Any, PredictionStrategy\]\]',
        r'Dict[str, Type[PredictionStrategy]]',
        content
    )
    # 修复返回类型
    content = re.sub(
        r'-> Dict\[str, Dict\[str, Any\]:',
        r'-> Dict[str, Dict[str, Any]]:',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 12. 修复 services/scoring_service.py
    print("修复 src/domain/services/scoring_service.py...")
    filepath = 'src/domain/services/scoring_service.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复参数类型
    content = re.sub(
        r'(\w+: Optional\[Dict\[str, Any\]\]\]) = None',
        r'\1 = None',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 13. 修复 services/team_service.py
    print("修复 src/domain/services/team_service.py...")
    filepath = 'src/domain/services/team_service.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复参数类型
    content = re.sub(
        r'(\w+: Optional\[.*?\]\]) = None',
        r'\1 = None',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 14. 修复 events/base.py
    print("修复 src/domain/events/base.py...")
    filepath = 'src/domain/events/base.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复未闭合的字符串
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '"event_id": self.event_id,' in line:
            lines[i] = line.rstrip().rstrip(',') + ','
        if '"data": self._get_event_data(),' in line:
            lines[i] = line.rstrip().rstrip(',') + ','
        if 'return f"' in line and not line.strip().endswith('"'):
            if '{self.__class__.__name__}' in line:
                lines[i] = line.rstrip() + f'({{self.event_id}})"'

    content = '\n'.join(lines)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 15. 修复 events/prediction_events.py
    print("修复 src/domain/events/prediction_events.py...")
    filepath = 'src/domain/events/prediction_events.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复参数类型
    content = re.sub(
        r'(\w+: Optional\[.*?\]\]) = None',
        r'\1 = None',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\nDomain模块修复完成！")

if __name__ == "__main__":
    fix_domain_errors()
