"""
端到端测试模块

本模块包含完整业务流程的端到端测试，验证系统的整体功能。

测试覆盖范围：
- API预测功能 (test_api_predictions.py)
- 数据血缘追踪 (test_lineage_tracking.py)
- 回测准确率验证 (test_backtest_accuracy.py)

使用方法：
    pytest tests/e2e/                     # 运行所有端到端测试
    pytest tests/e2e/ --maxfail=1         # 第一个失败后停止
"""

__all__ = ["__version__"]
__version__ = "1.0.0"
