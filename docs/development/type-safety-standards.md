# 足球预测系统类型安全标准

## 概述

本文档定义了足球预测系统的类型安全标准，确保代码质量和可维护性。

## 核心原则

### 1. 类型注解要求
- **所有公共函数**必须包含完整的类型注解
- **类方法**必须包含参数和返回值类型注解
- **变量**在复杂情况下应包含类型注解
- **Optional类型**必须明确标注可能为None的情况

### 2. 导入标准
```python
# 推荐的typing导入顺序
from typing import (
    Optional,  # 用于可能为None的值
    Union,     # 用于多种类型
    List,      # 用于列表
    Dict,      # 用于字典
    Tuple,     # 用于元组
    Any,       # 仅在必要时使用
)
```

### 3. 函数签名标准
```python
# ✅ 正确示例
def process_prediction(
    match_id: int,
    team_data: Dict[str, Any],
    include_features: bool = False
) -> Optional[Dict[str, float]]:
    """处理比赛预测数据"""
    pass

# ❌ 错误示例
def process_prediction(match_id, team_data, include_features=False):
    """处理比赛预测数据"""
    pass
```

### 4. 错误处理标准
```python
# ✅ 正确的错误处理
def safe_divide(a: float, b: float) -> Optional[float]:
    """安全除法操作"""
    if b == 0:
        return None
    return a / b

# ❌ 错误：不处理None情况
def safe_divide(a: float, b: float) -> float:
    """安全除法操作"""
    return a / b  # 可能抛出ZeroDivisionError
```

## 具体规范

### 1. 基础类型使用

#### 字符串处理
```python
def format_team_name(name: Optional[str]) -> str:
    """格式化球队名称"""
    if name is None:
        return "Unknown"
    return name.strip().title()
```

#### 数值处理
```python
def calculate_win_probability(
    home_score: float,
    away_score: float
) -> float:
    """计算胜率概率"""
    total = home_score + away_score
    if total == 0:
        return 0.5  # 默认平局概率
    return home_score / total
```

#### 集合类型
```python
def get_active_teams(
    league_id: int,
    season: Optional[int] = None
) -> List[Dict[str, Any]]:
    """获取活跃球队列表"""
    return []
```

### 2. 复杂类型示例

#### 嵌套结构
```python
from typing import TypedDict

class MatchResult(TypedDict):
    """比赛结果类型定义"""
    match_id: int
    home_score: int
    away_score: int
    winner: Optional[str]
    timestamp: str

def process_match_results(
    matches: List[Dict[str, Any]]
) -> List[MatchResult]:
    """处理比赛结果"""
    pass
```

#### 回调函数
```python
from typing import Callable, Any

def register_prediction_handler(
    handler: Callable[[Dict[str, Any]], bool]
) -> None:
    """注册预测处理器"""
    pass
```

### 3. 类定义标准

```python
from typing import ClassVar

class PredictionService:
    """预测服务类"""

    def __init__(
        self,
        model_path: str,
        config: Dict[str, Any],
        cache_enabled: bool = True
    ) -> None:
        self.model_path = model_path
        self.config = config
        self.cache_enabled = cache_enabled

    def predict(
        self,
        match_data: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        """执行预测"""
        if not self._validate_input(match_data):
            return None
        return self._run_prediction(match_data)

    def _validate_input(self, data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_keys = ["home_team", "away_team", "match_date"]
        return all(key in data for key in required_keys)

    def _run_prediction(self, data: Dict[str, Any]) -> Dict[str, float]:
        """执行实际预测逻辑"""
        return {"home_win": 0.6, "draw": 0.25, "away_win": 0.15}
```

## MyPy配置

### 1. 严格模式设置
```ini
[mypy]
python_version = 3.11
strict = True
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
```

### 2. 特定模块配置
```ini
[mypy-tests.*]
disallow_untyped_defs = False

[mypy-migrations.*]
ignore_errors = True

[mypy-external_libs.*]
ignore_missing_imports = True
```

## 代码审查清单

### 1. 函数级别检查
- [ ] 所有参数都有类型注解
- [ ] 返回值类型明确
- [ ] Optional类型正确处理
- [ ] 无类型ignore注释（除非必要）

### 2. 类级别检查
- [ ] 方法签名完整
- [ ] 属性类型明确
- [ ] 继承关系类型安全

### 3. 模块级别检查
- [ ] 导入语句规范
- [ ] 全局变量类型明确
- [ ] __all__列表类型标注

## 常见问题解决

### 1. 处理None值
```python
# ✅ 正确处理
def get_team_name(team_id: Optional[int]) -> str:
    if team_id is None:
        return "Unknown Team"
    return team_names.get(team_id, "Unknown Team")

# ❌ 错误：直接使用可能为None的值
def get_team_name(team_id: Optional[int]) -> str:
    return team_names[team_id]  # 可能在team_id为None时报错
```

### 2. 避免Any类型
```python
# ✅ 使用具体类型
def process_data(data: Dict[str, Union[str, int]]) -> Dict[str, str]:
    return {k: str(v) for k, v in data.items()}

# ❌ 过度使用Any
def process_data(data: Any) -> Any:
    return data
```

### 3. 类型转换
```python
# ✅ 明确类型转换
def calculate_average(scores: List[Union[str, int]]) -> float:
    numeric_scores = [float(s) for s in scores]
    return sum(numeric_scores) / len(numeric_scores)

# ❌ 隐式类型转换
def calculate_average(scores):
    return sum(scores) / len(scores)  # 类型不明确
```

## 工具和自动化

### 1. 开发工具配置
- **VS Code**: 启用类型检查
- **PyCharm**: 启用严格类型检查
- **Pre-commit**: 集成MyPy检查

### 2. CI/CD集成
```yaml
# .github/workflows/quality-check.yml
- name: Type Check
  run: |
    make type-check
```

### 3. 本地验证
```bash
# 完整类型检查
make type-check

# 严格模式检查
mypy --strict src/

# 生成类型报告
mypy --txt-report reports src/
```

## 培训和文档

### 1. 团队培训
- 类型注解基础
- MyPy使用指南
- 常见问题解决

### 2. 代码示例
- 提供完整示例代码
- 最佳实践案例
- 反模式警告

### 3. 定期审查
- 月度类型安全审查
- 代码质量报告
- 改进建议

## 版本控制

- **当前版本**: 1.0.0
- **更新日期**: 2025-10-21
- **维护者**: 开发团队

## 相关文档

- [MyPy官方文档](https://mypy.readthedocs.io/)
- [PEP 484 - 类型注解](https://peps.python.org/pep-0484/)
- [Python typing模块文档](https://docs.python.org/3/library/typing.html)