#!/usr/bin/env python3
"""
手动逐个修复domain模块的语法错误
"""

import os

def fix_file_content(filepath, fixes):
    """应用修复到文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for i in range(0, len(fixes), 2):
        old = fixes[i]
        new = fixes[i+1]
        content = content.replace(old, new)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ 修复了 {filepath}")
    else:
        print(f"○ 无需修复 {filepath}")

def fix_domain_module():
    """修复domain模块"""

    # 1. 修复 league.py
    print("\n1. 修复 league.py...")
    fix_file_content('src/domain/models/league.py', [
        'name: Optional[str] ] = None,',
        'name: Optional[str] = None,',
        'short_name: Optional[str] ] = None,',
        'short_name: Optional[str] = None,',
        'website: Optional[str] ] = None,',
        'website: Optional[str] = None,',
    ])

    # 2. 修复 match.py
    print("\n2. 修复 match.py...")
    fix_file_content('src/domain/models/match.py', [
        'reason: Optional[str] ] = None',
        'reason: Optional[str] = None',
    ])

    # 3. 修复 strategies/config.py
    print("\n3. 修复 strategies/config.py...")
    fix_file_content('src/domain/strategies/config.py', [
        '-> Optional[Dict[str, Any]:',
        '-> Optional[Dict[str, Any]]:',
    ])

    # 4. 修复 strategies/base.py
    print("\n4. 修复 strategies/base.py...")
    fix_file_content('src/domain/strategies/base.py', [
        'probability_distribution: Optional[Dict[str, float] = None',
        'probability_distribution: Optional[Dict[str, float]] = None',
        'feature_importance: Optional[Dict[str, float] = None',
        'feature_importance: Optional[Dict[str, float]] = None',
        'metadata: Optional[Dict[str, Any] = field(default_factory=dict[str, Any])',
        'metadata: Optional[Dict[str, Any]] = field(default_factory=dict[str, Any])',
    ])

    # 5. 修复 strategies/historical.py
    print("\n5. 修复 strategies/historical.py...")
    fix_file_content('src/domain/strategies/historical.py', [
        'self, predictions: Dict[str, Optional[Tuple[int, int]]]',
        'self, predictions: Dict[str, Optional[Tuple[int, int]]]]',
    ])

    # 6. 修复 strategies/ensemble.py
    print("\n6. 修复 strategies/ensemble.py...")
    fix_file_content('src/domain/strategies/ensemble.py', [
        'self._sub_strategies: Dict[str, PredictionStrategy] = {}]',
        'self._sub_strategies: Dict[str, PredictionStrategy] = {}',
        'self._strategy_weights: Dict[str, StrategyWeight] = {}]',
        'self._strategy_weights: Dict[str, StrategyWeight] = {}',
        'self._performance_history: Dict[str, List[float] = {}',
        'self._performance_history: Dict[str, List[float]] = {}',
    ])

    # 7. 修复 strategies/statistical.py
    print("\n7. 修复 strategies/statistical.py...")
    fix_file_content('src/domain/strategies/statistical.py', [
        'self, predictions: Dict[str, Tuple[int, int]]]',
        'self, predictions: Dict[str, Tuple[int, int]]',
    ])

    # 8. 修复 strategies/ml_model.py
    print("\n8. 修复 strategies/ml_model.py...")
    fix_file_content('src/domain/strategies/ml_model.py', [
        'self, actual_results: List[Tuple[Prediction, Dict[str, Any]]]',
        'self, actual_results: List[Tuple[Prediction, Dict[str, Any]]]]',
    ])

    # 9. 修复 strategies/factory.py
    print("\n9. 修复 strategies/factory.py...")
    fix_file_content('src/domain/strategies/factory.py', [
        'self._strategies: Dict[str, PredictionStrategy] = {}]',
        'self._strategies: Dict[str, PredictionStrategy] = {}',
        'self._strategy_configs: Dict[str, Union[str, Dict[str, Any] = {}',
        'self._strategy_configs: Dict[str, Union[str, Dict[str, Any]]] = {}',
        'self._default_config: Dict[str, Any] = {}]',
        'self._default_config: Dict[str, Any] = {}',
        'self._environment_overrides: Dict[str, Any] = {}]',
        'self._environment_overrides: Dict[str, Any] = {}',
        'Dict[str, Type[Any, PredictionStrategy]]',
        'Dict[str, Type[PredictionStrategy]]',
        '-> Dict[str, Dict[str, Any]:',
        '-> Dict[str, Dict[str, Any]]:',
    ])

    # 10. 修复 services/scoring_service.py
    print("\n10. 修复 services/scoring_service.py...")
    fix_file_content('src/domain/services/scoring_service.py', [
        'scoring_config: Optional[Dict[str, Any] ] ] = None',
        'scoring_config: Optional[Dict[str, Any]] = None',
    ])

    # 11. 修复 services/team_service.py
    print("\n11. 修复 services/team_service.py...")
    fix_file_content('src/domain/services/team_service.py', [
        'repository: Optional[TeamRepositoryProtocol] ] = None',
        'repository: Optional[TeamRepositoryProtocol] = None',
    ])

    # 12. 修复 events/prediction_events.py
    print("\n12. 修复 events/prediction_events.py...")
    fix_file_content('src/domain/events/prediction_events.py', [
        'confidence: Optional[float] ] = None,',
        'confidence: Optional[float] = None,',
    ])

    # 13. 手动修复 events/base.py 的特殊问题
    print("\n13. 修复 events/base.py...")
    with open('src/domain/events/base.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复未闭合的字符串
    content = content.replace(
        'return f"{self.__class__.__name__"({self.event_id})""',
        'return f"{self.__class__.__name__}({self.event_id})"'
    )

    with open('src/domain/events/base.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ 修复了 src/domain/events/base.py")

if __name__ == "__main__":
    print("开始手动修复domain模块...")
    fix_domain_module()
    print("\nDomain模块修复完成！")
