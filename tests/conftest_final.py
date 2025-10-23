"""
最终修复的pytest配置文件
Final Fixed pytest Configuration
"""

import os
import pytest
from fastapi.testclient import TestClient

# 导入主应用
from src.main import app

@pytest.fixture(scope="session")
def test_client():
    """创建测试客户端"""
    return TestClient(app)

@pytest.fixture(scope="session")
def async_client():
    """创建异步测试客户端"""
    from fastapi.testclient import AsyncTestClient
    return AsyncTestClient(app)

# 直接使用标准logging，避免循环导入问题
import logging
def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """获取标准日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

# 简化的测试数据工厂
@pytest.fixture
def sample_prediction_data():
    """返回样例预测数据"""
    return {
        "match_id": 1,
        "home_win_prob": 0.5,
        "draw_prob": 0.3,
        "away_win_prob": 0.2,
        "predicted_outcome": "home",
        "confidence": 0.85,
        "model_version": "1.0.0"
    }

# 设置测试环境
@pytest.fixture(autouse=True)
def setup_test_environment():
    """设置测试环境变量"""
    os.environ["TESTING"] = "true"
    yield
    # 清理
    if "TESTING" in os.environ:
        del os.environ["TESTING"]