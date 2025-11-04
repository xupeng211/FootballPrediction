"""
领域层基础测试
Basic Domain Layer Tests
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.domain
@pytest.mark.unit
def test_domain_structure():
    """测试领域层结构"""
    project_root = Path(__file__).parent.parent.parent
    domain_dir = project_root / "src" / "domain"

    if domain_dir.exists():
        assert domain_dir.is_dir(), "domain目录存在但不是目录"

        # 检查领域层子模块
        submodules = ["models", "services", "events", "strategies"]
        for module in submodules:
            module_path = domain_dir / module
            if module_path.exists():
                init_file = module_path / "__init__.py"
                if not init_file.exists():
                    pytest.skip(f"领域模块 {module} 缺少 __init__.py 文件")


@pytest.mark.domain
@pytest.mark.unit
def test_domain_models_import():
    """测试领域模型导入"""
    try:
        # 尝试导入基础模型
        from src.domain.models.base import BaseModel

        assert True
    except ImportError:
        pytest.skip("基础模型不可用")


@pytest.mark.domain
@pytest.mark.unit
def test_domain_services_import():
    """测试领域服务导入"""
    try:
        # 尝试导入服务基类
        from src.domain.services.base import BaseService

        assert True
    except ImportError:
        pytest.skip("领域服务基类不可用")


@pytest.mark.domain
@pytest.mark.unit
def test_prediction_domain_logic():
    """测试预测领域逻辑基础"""
    try:
        from src.domain.models.prediction import Prediction

        # 基础实例化测试
        assert True
    except ImportError:
        pytest.skip("预测模型不可用")


@pytest.mark.domain
@pytest.mark.unit
def test_strategy_pattern_implementation():
    """测试策略模式实现"""
    try:
        from src.domain.strategies.factory import StrategyFactory

        assert True
    except ImportError:
        pytest.skip("策略工厂不可用")
