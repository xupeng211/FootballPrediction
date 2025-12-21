# V7.0 项目交接备忘录

## 核心状态
本项目 V7.0 已实现 FotMob 数据实心化。

## 关键逻辑

### 1. API 请求策略
API 请求必须伪装 User-Agent 以获取 300KB+ 完整报文。

### 2. 唯一特征提取器
BulletproofFeatureExtractor (`src/data_access/processors/bulletproof_feature_extractor.py`) 是系统唯一特征提取入口点。

### 3. 核心维度
180 维特征集（含事件流与衍生指标）：

#### 事件解析能力
- ✅ 红牌检测：通过 `matchFacts.events.events[].type` 匹配 "card"
- ✅ 点球检测：通过 `shotmapEvent.situation` 包含 "penalty"
- ✅ 换人检测：通过 `matchFacts.events.events[].type` 匹配 "substitution"
- ✅ 早场进球：15分钟内进球事件标记

#### 衍生特征计算
- ✅ `rating_diff`: 主客队阵容平均评分差值
- ✅ `xg_per_shot`: 单次射门质量 (xG/射门次数)

#### 鲁棒性保证
使用 `.get()` 链式调用和异常处理，防止 JSON 结构变化导致崩溃。

### 4. 数据质量
- 黄金数据集：`data/final_v7_solid_features.csv`
- 生产资产：`data/production/` 目录下存放核心模型和数据
- 特征完整性：100% (168场比赛, 30维核心特征已固化)
- 事件覆盖率：红牌、点球、换人、早场进球全覆盖

### 5. 核心生产资产 (V7.1)
- **模型文件**: `data/production/lightgbm_v7.model` (78.79%准确率)
- **训练数据**: `data/production/final_v7_solid_features.csv` (168场英超数据)
- **特征缩放器**: `data/production/lightgbm_v7_scaler.pkl`
- **标签编码器**: `data/production/lightgbm_v7_encoder.pkl`

### 6. Docker 配置
- ✅ `.dockerignore` 已创建，忽略 `data/`, `venv/`, `.git`, `__pycache__`
- ✅ `docker-compose.yml` 已移除过时的 `version` 标签
- ✅ `Dockerfile` 使用 `python:3.11-slim` 轻量化生产镜像

### 7. 工作区清理
已清理根目录临时文件，保留核心CLI入口 `cli.py`

### 8. V7.1 状态
- ✅ 模块化重构完成 (96/100评分)
- ✅ 全量数据收割 (168场比赛)
- ✅ LightGBM模型训练 (78.79%准确率)
- ✅ 统一CLI接口 (harvest/predict/train/status)

---

**交接时间**: 2025-12-21
**版本**: V7.1 生产就绪版
**状态**: ✅ 模块化架构完成，可投入生产使用
