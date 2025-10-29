#!/usr/bin/env python3
"""
LSTM时间序列预测模型
LSTM Time Series Prediction Model

基于长短期记忆网络的质量指标时间序列预测和异常检测
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
except ImportError:
    print("警告: TensorFlow未安装，LSTM功能将不可用")
    tf = None

from src.core.logging_system import get_logger
from src.core.config import get_config
from src.timeseries.influxdb_client import influxdb_manager

logger = get_logger(__name__)


@dataclass
class PredictionResult:
    """预测结果数据模型"""
    timestamp: datetime
    predicted_values: List[float]
    confidence_intervals: List[Tuple[float, float]]  # (lower, upper)
    actual_values: Optional[List[float]] = None
    model_version: str = "1.0"
    prediction_horizon: int = 12  # 预测未来12个时间点
    mae: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.actual_values:
            data['actual_values'] = self.actual_values
        return data


@dataclass
class TrainingConfig:
    """LSTM训练配置"""
    sequence_length: int = 24  # 使用过去24个时间点
    prediction_horizon: int = 12  # 预测未来12个时间点
    lstm_units: List[int] = (64, 32)  # LSTM层单元数
    dropout_rate: float = 0.2
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    validation_split: float = 0.2
    early_stopping_patience: int = 10


class LSTMPredictor:
    """LSTM时间序列预测器"""

    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.logger = get_logger(self.__class__.__name__)

        # 模型组件
        self.model = None
        self.scaler_X = MinMaxScaler()
        self.scaler_y = MinMaxScaler()
        self.is_trained = False

        # 数据缓存
        self.training_data = None
        self.validation_data = None
        self.feature_columns = []

        # 模型存储路径
        self.model_dir = Path("models/lstm")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.model_dir / "lstm_quality_predictor.h5"
        self.scaler_path = self.model_dir / "scalers.pkl"

    def prepare_data(self, data: List[Dict[str, Any]],
                      target_column: str = "overall_score") -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据"""
        try:
            # 转换为DataFrame
            df = pd.DataFrame(data)

            # 确保时间排序
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values('time')

            # 选择特征列
            feature_columns = []
            for col in df.columns:
                if col != target_column and df[col].dtype in ['float64', 'int64']:
                    feature_columns.append(col)

            self.feature_columns = feature_columns

            # 提取特征和目标
            features = df[feature_columns].values
            target = df[target_column].values.reshape(-1, 1)

            # 数据标准化
            features_scaled = self.scaler_X.fit_transform(features)
            target_scaled = self.scaler_y.fit_transform(target)

            # 创建序列数据
            X, y = self._create_sequences(features_scaled, target_scaled)

            self.logger.info(f"数据准备完成: 特征维度={features.shape}, 序列数量={len(X)}")
            return X, y

        except Exception as e:
            self.logger.error(f"数据准备失败: {e}")
            raise

    def _create_sequences(self, features: np.ndarray, target: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """创建时间序列数据"""
        X, y = [], []

        for i in range(len(features) - self.config.sequence_length - self.config.prediction_horizon + 1):
            # 输入序列
            X.append(features[i:i + self.config.sequence_length])
            # 目标序列
            y.append(target[i + self.config.sequence_length:i + self.config.sequence_length + self.config.prediction_horizon])

        return np.array(X), np.array(y)

    def build_model(self, input_shape: Tuple[int, int]) -> None:
        """构建LSTM模型"""
        if tf is None:
            raise ImportError("TensorFlow未安装，无法构建LSTM模型")

        try:
            self.model = Sequential()

            # 第一层LSTM
            self.model.add(LSTM(
                self.config.lstm_units[0],
                return_sequences=True,
                input_shape=input_shape
            ))
            self.model.add(Dropout(self.config.dropout_rate))
            self.model.add(BatchNormalization())

            # 第二层LSTM
            if len(self.config.lstm_units) > 1:
                self.model.add(LSTM(
                    self.config.lstm_units[1],
                    return_sequences=False
                ))
                self.model.add(Dropout(self.config.dropout_rate))
                self.model.add(BatchNormalization())

            # 输出层
            self.model.add(Dense(self.config.prediction_horizon))

            # 编译模型
            self.model.compile(
                optimizer=Adam(learning_rate=self.config.learning_rate),
                loss='mse',
                metrics=['mae']
            )

            self.logger.info(f"LSTM模型构建完成: input_shape={input_shape}")

        except Exception as e:
            self.logger.error(f"模型构建失败: {e}")
            raise

    def train(self, X: np.ndarray, y: np.ndarray,
              validation_data: Optional[Tuple[np.ndarray, np.ndarray]] = None) -> Dict[str, Any]:
        """训练LSTM模型"""
        if self.model is None:
            self.build_model(input_shape=(X.shape[1], X.shape[2]))

        try:
            # 分割训练和验证数据
            if validation_data is None:
                split_idx = int(len(X) * (1 - self.config.validation_split))
                X_train, X_val = X[:split_idx], X[split_idx:]
                y_train, y_val = y[:split_idx], y[split_idx:]
                validation_data = (X_val, y_val)
            else:
                X_train, y_train = X, y

            # 设置回调函数
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=self.config.early_stopping_patience,
                    restore_best_weights=True,
                    verbose=1
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=5,
                    min_lr=1e-7,
                    verbose=1
                )
            ]

            # 训练模型
            history = self.model.fit(
                X_train, y_train,
                validation_data=validation_data,
                epochs=self.config.epochs,
                batch_size=self.config.batch_size,
                callbacks=callbacks,
                verbose=1
            )

            self.is_trained = True
            self.training_data = (X_train, y_train)
            self.validation_data = validation_data

            # 评估模型
            train_loss, train_mae = self.model.evaluate(X_train, y_train, verbose=0)
            val_loss, val_mae = self.model.evaluate(validation_data[0], validation_data[1], verbose=0)

            training_stats = {
                'train_loss': train_loss,
                'train_mae': train_mae,
                'val_loss': val_loss,
                'val_mae': val_mae,
                'epochs_trained': len(history.history['loss']),
                'best_epoch': np.argmin(history.history['val_loss']) + 1
            }

            self.logger.info(f"模型训练完成: {training_stats}")
            return training_stats

        except Exception as e:
            self.logger.error(f"模型训练失败: {e}")
            raise

    def predict(self, input_sequence: np.ndarray,
                 return_confidence: bool = True) -> PredictionResult:
        """进行预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")

        try:
            # 确保输入形状正确
            if input_sequence.shape[0] != self.config.sequence_length:
                raise ValueError(f"输入序列长度必须为 {self.config.sequence_length}")

            # 标准化输入
            input_scaled = self.scaler_X.transform(input_sequence)

            # 添加批次维度
            input_batch = np.expand_dims(input_scaled, axis=0)

            # 预测
            prediction_scaled = self.model.predict(input_batch, verbose=0)

            # 反标准化
            prediction = self.scaler_y.inverse_transform(prediction_scaled)[0]

            # 计算置信区间 (使用历史预测误差)
            confidence_intervals = []
            if return_confidence and self.validation_data:
                # 在验证集上计算预测误差
                val_X, val_y = self.validation_data
                val_pred_scaled = self.model.predict(val_X, verbose=0)
                val_pred = self.scaler_y.inverse_transform(val_pred_scaled)

                # 计算每个时间点的预测误差标准差
                errors = []
                for i in range(self.config.prediction_horizon):
                    error = np.abs(val_pred[:, i] - val_y[:, i])
                    errors.append(np.std(error))

                # 生成95%置信区间
                for i, pred_val in enumerate(prediction):
                    std_error = errors[i] if i < len(errors) else np.mean(errors)
                    margin = 1.96 * std_error  # 95%置信区间
                    confidence_intervals.append((
                        max(0, pred_val - margin),
                        min(10, pred_val + margin)  # 假设分数范围0-10
                    ))
            else:
                # 如果没有验证数据，使用默认置信区间
                for pred_val in prediction:
                    margin = 0.5  # 默认置信区间±0.5
                    confidence_intervals.append((
                        max(0, pred_val - margin),
                        min(10, pred_val + margin)
                    ))

            # 创建预测结果
            result = PredictionResult(
                timestamp=datetime.now(),
                predicted_values=prediction.tolist(),
                confidence_intervals=confidence_intervals,
                prediction_horizon=self.config.prediction_horizon
            )

            self.logger.info(f"预测完成: 预测值={prediction[:3].tolist()}...")
            return result

        except Exception as e:
            self.logger.error(f"预测失败: {e}")
            raise

    async def predict_future(self, hours_ahead: int = 6) -> PredictionResult:
        """预测未来质量指标"""
        try:
            # 获取最近的历史数据
            recent_data = await influxdb_manager.get_quality_metrics_history(
                hours=self.config.sequence_length + 24
            )

            if len(recent_data) < self.config.sequence_length:
                raise ValueError(f"历史数据不足，需要至少 {self.config.sequence_length} 个数据点")

            # 提取特征数据
            features_data = []
            for point in recent_data:
                feature_vector = [
                    point.get('value', 0) if point.get('field') == 'overall_score' else 0,
                    point.get('cpu_usage', 0) if point.get('field') == 'cpu_usage' else 0,
                    point.get('memory_usage', 0) if point.get('field') == 'memory_usage' else 0,
                    point.get('active_connections', 0) if point.get('field') == 'active_connections' else 0
                ]
                features_data.append(feature_vector)

            # 如果特征数据不足，使用默认值填充
            while len(features_data) < self.config.sequence_length:
                features_data.insert(0, [7.0, 50.0, 60.0, 10])  # 默认值

            # 取最近的数据点
            input_sequence = np.array(features_data[-self.config.sequence_length:])

            # 进行预测
            result = self.predict(input_sequence)

            self.logger.info(f"未来预测完成: {hours_ahead}小时")
            return result

        except Exception as e:
            self.logger.error(f"未来预测失败: {e}")
            raise

    def evaluate_model(self, test_X: np.ndarray, test_y: np.ndarray) -> Dict[str, float]:
        """评估模型性能"""
        try:
            # 预测
            predictions_scaled = self.model.predict(test_X, verbose=0)
            predictions = self.scaler_y.inverse_transform(predictions_scaled)
            actuals = self.scaler_y.inverse_transform(test_y)

            # 计算指标
            mae = mean_absolute_error(actuals, predictions)
            mse = mean_squared_error(actuals, predictions)
            rmse = np.sqrt(mse)
            r2 = r2_score(actuals.flatten(), predictions.flatten())

            metrics = {
                'mae': mae,
                'mse': mse,
                'rmse': rmse,
                'r2': r2
            }

            self.logger.info(f"模型评估完成: {metrics}")
            return metrics

        except Exception as e:
            self.logger.error(f"模型评估失败: {e}")
            return {}

    def save_model(self) -> bool:
        """保存模型和标准化器"""
        try:
            if self.model is None:
                self.logger.warning("没有可保存的模型")
                return False

            # 保存Keras模型
            self.model.save(self.model_path)

            # 保存标准化器
            with open(self.scaler_path, 'wb') as f:
                pickle.dump({
                    'scaler_X': self.scaler_X,
                    'scaler_y': self.scaler_y,
                    'feature_columns': self.feature_columns,
                    'config': self.config
                }, f)

            self.logger.info(f"模型已保存: {self.model_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存模型失败: {e}")
            return False

    def load_model(self) -> bool:
        """加载模型和标准化器"""
        try:
            if not self.model_path.exists():
                self.logger.warning(f"模型文件不存在: {self.model_path}")
                return False

            # 加载Keras模型
            self.model = tf.keras.models.load_model(self.model_path)

            # 加载标准化器
            with open(self.scaler_path, 'rb') as f:
                scalers_data = pickle.load(f)
                self.scaler_X = scalers_data['scaler_X']
                self.scaler_y = scalers_data['scaler_y']
                self.feature_columns = scalers_data['feature_columns']
                self.config = scalers_data['config']

            self.is_trained = True
            self.logger.info(f"模型已加载: {self.model_path}")
            return True

        except Exception as e:
            self.logger.error(f"加载模型失败: {e}")
            return False

    async def train_with_historical_data(self, days: int = 30) -> Dict[str, Any]:
        """使用历史数据训练模型"""
        try:
            self.logger.info(f"开始使用历史数据训练模型 (过去{days}天)")

            # 获取历史数据
            historical_data = await influxdb_manager.get_quality_metrics_history(hours=days*24)

            if len(historical_data) < 100:
                raise ValueError(f"历史数据不足，只有 {len(historical_data)} 个数据点")

            # 准备数据
            X, y = self.prepare_data(historical_data)

            if len(X) < 50:
                raise ValueError("准备后的训练数据不足")

            # 训练模型
            training_stats = self.train(X, y)

            # 保存模型
            self.save_model()

            # 评估模型
            metrics = self.evaluate_model(X, y)
            training_stats.update(metrics)

            self.logger.info(f"历史数据训练完成: {training_stats}")
            return training_stats

        except Exception as e:
            self.logger.error(f"历史数据训练失败: {e}")
            raise


# 全局LSTM预测器实例
lstm_predictor = LSTMPredictor()


# 辅助函数
async def train_lstm_model(days: int = 30) -> Dict[str, Any]:
    """训练LSTM模型"""
    return await lstm_predictor.train_with_historical_data(days)


async def predict_quality_trend(hours_ahead: int = 6) -> PredictionResult:
    """预测质量趋势"""
    return await lstm_predictor.predict_future(hours_ahead)


if __name__ == "__main__":
    import asyncio

    async def test_lstm_predictor():
        """测试LSTM预测器"""
        print("🧪 测试LSTM时间序列预测模型...")

        # 生成模拟历史数据
        np.random.seed(42)
        n_points = 200
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(n_points, 0, -1)]

        mock_data = []
        for i, timestamp in enumerate(timestamps):
            # 模拟质量分数趋势 (带噪声)
            base_score = 8.0 + 0.5 * np.sin(i * 0.1) + np.random.normal(0, 0.2)
            base_score = np.clip(base_score, 6.0, 10.0)

            mock_data.append({
                'time': timestamp.isoformat(),
                'value': base_score,
                'field': 'overall_score',
                'cpu_usage': 40 + 20 * np.sin(i * 0.05) + np.random.normal(0, 5),
                'memory_usage': 60 + 15 * np.cos(i * 0.08) + np.random.normal(0, 3),
                'active_connections': 10 + 5 * np.sin(i * 0.03) + np.random.randint(-2, 3)
            })

        print(f"✅ 生成了 {len(mock_data)} 个模拟数据点")

        # 训练模型
        lstm_predictor.prepare_data(mock_data)
        X, y = lstm_predictor.prepare_data(mock_data)

        print(f"✅ 数据准备完成: X.shape={X.shape}, y.shape={y.shape}")

        # 构建和训练模型
        lstm_predictor.build_model(input_shape=(X.shape[1], X.shape[2]))
        training_stats = lstm_predictor.train(X, y)

        print(f"✅ 模型训练完成: {training_stats}")

        # 进行预测
        test_sequence = X[-1]  # 使用最后一个序列进行测试
        prediction_result = lstm_predictor.predict(test_sequence)

        print("✅ 预测完成:")
        print(f"  预测值: {prediction_result.predicted_values[:3]}")
        print(f"  置信区间: {prediction_result.confidence_intervals[:3]}")

        # 保存模型
        lstm_predictor.save_model()
        print("✅ 模型已保存")

        print("🎉 LSTM预测器测试完成!")

    # 运行测试
    asyncio.run(test_lstm_predictor())