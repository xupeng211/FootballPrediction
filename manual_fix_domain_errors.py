#!/usr/bin/env python3
"""
手动修复domain模块剩余的复杂语法错误
"""

import re

def fix_specific_errors():
    """修复特定的语法错误"""

    # 需要修复的文件和对应的错误
    fixes = {
        'src/domain/models/team.py': [
            # 修复未闭合的f-string
            (r'return f"\{self\.matches_played\}场 \{self\.wins\}胜 \{self\.draws\}平 \{self\.losses\}负$',
             r'return f"{self.matches_played}场 {self.wins}胜 {self.draws}平 {self.losses}负"'),
            (r'f"\{self\.current_streak\{self\.streak_type\[0\]\.upper\(\)\}"',
             r'f"{self.current_streak}{self.streak_type[0].upper()}"'),
            (r'return f"状态: \{self\.recent_form_string\} \(\{streak_str\)"',
             r'return f"状态: {self.recent_form_string} ({streak_str})"'),
            (r'return f"\{self\.name\} \(\{self\.code or self\.short_name\}\) - \{self\.rank\}"',
             r'return f"{self.name} ({self.code or self.short_name}) - {self.rank}"'),
        ],
        'src/domain/strategies/factory.py': [
            # 修复字典初始化的括号不匹配
            (r'self\._strategies: Dict\[str, PredictionStrategy\] = \]\]',
             r'self._strategies: Dict[str, PredictionStrategy] = {}'),
            (r'self\._strategy_configs: Dict\[str, Union\[str, Dict\[str, Any\]\] = \[\]',
             r'self._strategy_configs: Dict[str, Union[str, Dict[str, Any]]] = {}'),
            (r'self\._default_config: Dict\[str, Any\] = \]\]',
             r'self._default_config: Dict[str, Any] = {}'),
            (r'self\._environment_overrides: Dict\[str, Any\] = \]\]',
             r'self._environment_overrides: Dict[str, Any] = {}'),
            # 修复类型注解
            (r'Dict\[str, Type\[Any, PredictionStrategy\]\]',
             r'Dict[str, Type[PredictionStrategy]]'),
            # 修复f-string
            (r'f"\{strategy_type\] -> \{strategy_class\.__name__\]\]"',
             r'f"{strategy_type} -> {strategy_class.__name__}"'),
            (r'f"注册策略类型: \{strategy_type\]\}"',
             r'f"注册策略类型: {strategy_type}"'),
            # 修复更多字典初始化
            (r'created_sub_strategies = \]\]',
             r'created_sub_strategies = []'),
            (r'config = \{\]',
             r'config = {}'),
            # 修复其他语法错误
            (r'current\[keys\[-1\] = value',
             r'current[keys[-1]] = value'),
            (r'health_report = \]\]',
             r'health_report = {}'),
            (r'created_strategies = \]\]',
             r'created_strategies = []'),
        ],
        'src/domain/strategies/ensemble.py': [
            # 修复字典初始化
            (r'self\._sub_strategies: Dict\[str, PredictionStrategy\] = \]\]',
             r'self._sub_strategies: Dict[str, PredictionStrategy] = {}'),
            (r'self\._strategy_weights: Dict\[str, StrategyWeight\] = \]\]',
             r'self._strategy_weights: Dict[str, StrategyWeight] = {}'),
            (r'self\._performance_history: Dict\[str, List\[float\]\] = \[\]',
             r'self._performance_history: Dict[str, List[float]] = {}'),
            # 修复其他错误
            (r'strategy_contributions = \]\]',
             r'strategy_contributions = []'),
            (r'predictions = \]\]',
             r'predictions = []'),
            (r'prediction_counts = \]  # type: ignore',
             r'prediction_counts = {}  # type: ignore'),
            (r'away_counts = \]  # type: ignore',
             r'away_counts = {}  # type: ignore'),
            (r'ensemble_probs = \{"home_win": 0, "draw": 0, "away_win": 0\]\]',
             r'ensemble_probs = {"home_win": 0, "draw": 0, "away_win": 0}'),
        ],
        'src/domain/events/base.py': [
            # 修复三引号字符串
            (r'"""', '"""'),
            # 修复f-string
            (r'return f"\{self\.__class__\.__name__\"\(\{self\.event_id\)\)""',
             r'return f"{self.__class__.__name__}({self.event_id})"'),
        ],
    }

    fixed_files = []

    for filepath, patterns in fixes.items():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(filepath)
                print(f"✓ 修复了 {filepath}")
        except Exception as e:
            print(f"✗ 修复 {filepath} 时出错: {e}")

    return fixed_files

if __name__ == "__main__":
    print("开始手动修复domain模块剩余语法错误...")
    fixed = fix_specific_errors()
    print(f"\n修复了 {len(fixed)} 个文件")
    for f in fixed:
        print(f"  - {f}")
