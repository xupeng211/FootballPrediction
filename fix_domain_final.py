#!/usr/bin/env python3
"""
最终修复domain模块所有语法错误
"""

import re

def fix_remaining_errors():
    """修复剩余的语法错误"""

    fixes = {
        'src/domain/models/team.py': [
            # 修复未闭合的字符串
            (r'return f"状态: \{self\.recent_form_string\} \(\{streak_str\})$',
             r'return f"状态: {self.recent_form_string} ({streak_str})"'),
        ],
        'src/domain/strategies/factory.py': [
            # 修复字典初始化
            (r'current\[k\] = \{\]',
             r'current[k] = {}'),
        ],
        'src/domain/strategies/ensemble.py': [
            # 修复字典初始化
            (r'self\._sub_strategies: Dict\[str, PredictionStrategy\] = \]\]',
             r'self._sub_strategies: Dict[str, PredictionStrategy] = {}'),
            (r'self\._strategy_weights: Dict\[str, StrategyWeight\] = \]\]',
             r'self._strategy_weights: Dict[str, StrategyWeight] = {}'),
            (r'self\._performance_history: Dict\[str, List\[float\]\] = \[\]',
             r'self._performance_history: Dict[str, List[float]] = {}'),
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
            # 修复未闭合的字符串
            (r'return f"\{self\.__class__\.__name__\}\(\{self\.event_id\}\)""',
             r'return f"{self.__class__.__name__}({self.event_id})"'),
        ],
        # 修复其他文件
        'src/domain/models/prediction.py': [
            (r'(\w+: Optional\[.*?)\] = None',
             r'\1] = None'),
        ],
        'src/domain/models/match.py': [
            (r'(\w+: Optional\[.*?)\] = None',
             r'\1] = None'),
        ],
        'src/domain/strategies/config.py': [
            (r'(\w+: Optional\[.*?)\] = None',
             r'\1] = None'),
        ],
        'src/domain/strategies/base.py': [
            (r'(\w+: Optional\[.*?)\] = None',
             r'\1] = None'),
        ],
        'src/domain/strategies/historical.py': [
            (r'(\w+: Dict\[.*?)\]',
             r'\1]'),
        ],
        'src/domain/strategies/statistical.py': [
            (r'(\w+: Dict\[.*?)\]',
             r'\1]'),
        ],
        'src/domain/strategies/ml_model.py': [
            # 修复语法错误
            (r'except \(ValueError, TypeError, AttributeError, KeyError, RuntimeError\) as e:',
             r'except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:'),
        ],
        'src/domain/services/scoring_service.py': [
            (r'(\w+: Optional\[.*?)\] = None',
             r'\1] = None'),
        ],
        'src/domain/services/team_service.py': [
            (r'(\w+: Optional\[.*?)\] = None',
             r'\1] = None'),
        ],
        'src/domain/events/prediction_events.py': [
            (r'(\w+: Optional\[.*?)\] = None',
             r'\1] = None'),
        ],
    }

    fixed_files = []

    for filepath, patterns in fixes.items():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            for pattern, replacement in patterns:
                new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                if new_content != content:
                    content = new_content

            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(filepath)
                print(f"✓ 修复了 {filepath}")
        except FileNotFoundError:
            print(f"✗ 文件不存在: {filepath}")
        except Exception as e:
            print(f"✗ 修复 {filepath} 时出错: {e}")

    return fixed_files

if __name__ == "__main__":
    print("开始最终修复domain模块语法错误...")
    fixed = fix_remaining_errors()
    print(f"\n修复了 {len(fixed)} 个文件")
    for f in fixed:
        print(f"  - {f}")
