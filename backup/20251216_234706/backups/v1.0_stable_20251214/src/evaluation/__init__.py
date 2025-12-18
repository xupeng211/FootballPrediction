"""
Football Prediction Model Evaluation System

This package provides comprehensive evaluation capabilities for football prediction models,
including metrics calculation, probability calibration, backtesting, and visualization.

Modules:
- metrics: Core evaluation metrics (accuracy, logloss, calibration, EV, etc.)
- calibration: Probability calibration methods (Isotonic, Platt)
- backtest: Betting simulation and backtesting engine
- visualizer: Chart and report generation
- report_builder: HTML/PDF report compilation
"""

from .metrics import Metrics
from .calibration import IsotonicCalibrator, PlattCalibrator
from .backtest import Backtester
from .visualizer import EvaluationVisualizer
from .report_builder import ReportBuilder

__version__ = "1.0.0"
__all__ = [
    "Metrics",
    "IsotonicCalibrator",
    "PlattCalibrator",
    "Backtester",
    "EvaluationVisualizer",
    "ReportBuilder",
]
