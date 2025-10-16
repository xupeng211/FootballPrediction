#!/usr/bin/env python3
"""
精确修复domain模块剩余的语法错误
"""

import os

def fix_remaining_errors():
    """修复剩余的具体错误"""

    # 1. 修复 prediction.py 第259行
    print("1. 修复 src/domain/models/prediction.py...")
    with open('src/domain/models/prediction.py', 'r') as f:
        lines = f.readlines()

    # 查找并修复第259行附近的错误
    for i, line in enumerate(lines):
        if 'metadata: Dict[str, Any] = field(default_factory=dict' in line and not line.strip().endswith(')'):
            lines[i] = line.replace('field(default_factory=dict', 'field(default_factory=dict)')

    with open('src/domain/models/prediction.py', 'w') as f:
        f.writelines(lines)
    print("✓ 修复了 prediction.py")

    # 2. 修复 team.py 第463行
    print("\n2. 修复 src/domain/models/team.py...")
    with open('src/domain/models/team.py', 'r') as f:
        lines = f.readlines()

    # 查找未闭合的字符串
    for i, line in enumerate(lines):
        if 'return f"' in line and not line.strip().endswith('"'):
            if i >= 460:  # 确保是第463行附近
                lines[i] = line.rstrip() + '"\n'

    with open('src/domain/models/team.py', 'w') as f:
        f.writelines(lines)
    print("✓ 修复了 team.py")

    # 3. 修复 match.py 第179行
    print("\n3. 修复 src/domain/models/match.py...")
    with open('src/domain/models/match.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'postponed_until: Optional[datetime] ] = None,',
        'postponed_until: Optional[datetime] = None,'
    )

    with open('src/domain/models/match.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 match.py")

    # 4. 修复 strategies/config.py 第277行
    print("\n4. 修复 src/domain/strategies/config.py...")
    with open('src/domain/strategies/config.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'def get(self, key: str, default: Any = None) -> Optional[Dict[str, Any]',
        'def get(self, key: str, default: Any = None) -> Optional[Dict[str, Any]]'
    )

    with open('src/domain/strategies/config.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 strategies/config.py")

    # 5. 修复 strategies/base.py 第113行
    print("\n5. 修复 src/domain/strategies/base.py...")
    with open('src/domain/strategies/base.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'metrics_data: Dict[str, Any]',
        'metrics_data: Dict[str, Any]]'
    )

    with open('src/domain/strategies/base.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 strategies/base.py")

    # 6. 修复 strategies/historical.py 第440行
    print("\n6. 修复 src/domain/strategies/historical.py...")
    with open('src/domain/strategies/historical.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'self, predictions: Dict[str, Optional[Tuple[int, int]]]]',
        'self, predictions: Dict[str, Optional[Tuple[int, int]]]]'
    )

    with open('src/domain/strategies/historical.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 strategies/historical.py")

    # 7. 修复 strategies/ensemble.py 第101行
    print("\n7. 修复 src/domain/strategies/ensemble.py...")
    with open('src/domain/strategies/ensemble.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'await self._initialize_sub_strategies(config.get("sub_strategies", [])',
        'await self._initialize_sub_strategies(config.get("sub_strategies", []))'
    )

    with open('src/domain/strategies/ensemble.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 strategies/ensemble.py")

    # 8. 修复 strategies/statistical.py 第450行
    print("\n8. 修复 src/domain/strategies/statistical.py...")
    with open('src/domain/strategies/statistical.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'away_goals = max(0, int(avg_goals - home_goals) * 0.8))',
        'away_goals = max(0, int(avg_goals - home_goals) * 0.8)'
    )

    with open('src/domain/strategies/statistical.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 strategies/statistical.py")

    # 9. 修复 strategies/ml_model.py 第382行
    print("\n9. 修复 src/domain/strategies/ml_model.py...")
    with open('src/domain/strategies/ml_model.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'self, actual_results: List[Tuple[Prediction, Dict[str, Any]]]]',
        'self, actual_results: List[Tuple[Prediction, Dict[str, Any]]]]'
    )

    with open('src/domain/strategies/ml_model.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 strategies/ml_model.py")

    # 10. 修复 strategies/factory.py 第63行
    print("\n10. 修复 src/domain/strategies/factory.py...")
    with open('src/domain/strategies/factory.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'self._strategy_registry: Dict[str, Type[Any, PredictionStrategy]]',
        'self._strategy_registry: Dict[str, Type[PredictionStrategy]]'
    )

    with open('src/domain/strategies/factory.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 strategies/factory.py")

    # 11. 修复 services/scoring_service.py 第38行
    print("\n11. 修复 src/domain/services/scoring_service.py...")
    with open('src/domain/services/scoring_service.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'return self.config.get("accuracy_weight", 0.4))',
        'return self.config.get("accuracy_weight", 0.4)'
    )

    with open('src/domain/services/scoring_service.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 services/scoring_service.py")

    # 12. 修复 services/team_service.py 第70行
    print("\n12. 修复 src/domain/services/team_service.py...")
    with open('src/domain/services/team_service.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'self._events.append(event)',
        'self._events.append(event)'
    )

    with open('src/domain/services/team_service.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 services/team_service.py")

    # 13. 修复 events/base.py 第38行
    print("\n13. 修复 src/domain/events/base.py...")
    with open('src/domain/events/base.py', 'r') as f:
        lines = f.readlines()

    # 修复未闭合的字符串
    for i, line in enumerate(lines):
        if '"version": self.version,' in line and not line.strip().endswith(','):
            lines[i] = line.rstrip() + ',\n'

    with open('src/domain/events/base.py', 'w') as f:
        f.writelines(lines)
    print("✓ 修复了 events/base.py")

    # 14. 修复 events/prediction_events.py 第87行
    print("\n14. 修复 src/domain/events/prediction_events.py...")
    with open('src/domain/events/prediction_events.py', 'r') as f:
        content = f.read()

    content = content.replace(
        'metadata: Optional[Dict[str, Any]] = None,',
        'metadata: Optional[Dict[str, Any]] = None,'
    )

    with open('src/domain/events/prediction_events.py', 'w') as f:
        f.write(content)
    print("✓ 修复了 events/prediction_events.py")

    print("\nDomain模块剩余错误修复完成！")

if __name__ == "__main__":
    fix_remaining_errors()
