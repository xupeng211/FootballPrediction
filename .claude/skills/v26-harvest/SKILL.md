---
name: v26-harvest
description: V26.1 production-grade data harvesting pipeline with zero defects. Use when running data collection, monitoring pipeline health, or managing batch processing for football prediction system.
---

# V26.1 收割流水线技能

## 技能概述
V26.1 生产级"零缺陷"收割流水线，专为足球预测系统设计的高性能、容错、可监控的数据采集架构。

## 核心能力
- **自动分批收割**: 内存监控、断点续传、失败重试
- **全量收割**: 4进程并行提取、特征剪枝、幂等性保证
- **流水线监控**: 健康评分、吞吐量统计、告警机制
- **特征工程**: 48维 → 12061维自适应提取
- **数据质量**: 稀疏度过滤、维度硬限制(8000维)

## 当前版本信息
- **版本**: V26.1 (生产级"零缺陷"收割流水线)
- **基线准确率**: 65.52% (V19.4.1)
- **数据量**: 13,129+ 场历史比赛
- **特征维度**: 48 → 12061 维 (V25.1 自适应引擎)

## 快速开始

### 方式一：自动分批收割（推荐）
```bash
# 自动分批收割（支持断点续传）
python scripts/auto_harvest_batches.py

# 指定批次大小
python scripts/auto_harvest_batches.py --batch-size 100

# 查看进度
tail -f logs/auto_harvest.log
```

### 方式二：全量收割
```bash
# 全量收割（内存自适应）
python scripts/run_v26_full_harvest.py

# 限制收割数量
python scripts/run_v26_full_harvest.py --limit 100

# 指定并行进程数
python scripts/run_v26_full_harvest.py --workers 4
```

### 方式三：监控流水线健康
```bash
# 查看流水线健康状态
cat data/monitoring/pipeline_health.json | jq '.health_status'

# 检查健康评分
cat data/monitoring/pipeline_health.json | jq '.health_score'

# 查看告警信息
cat data/monitoring/pipeline_health.json | jq '.alerts'
```

## 核心脚本说明

### 1. auto_harvest_batches.py（自动分批收割）
**用途**: 生产环境推荐使用，支持大规模数据处理

**核心特性**:
- 批次大小: 200场/批
- 内存监控: 超过7GB自动等待
- 断点续传: 进度持久化
- 失败重试: 最多2次

**参数说明**:
```bash
--batch-size     批次大小（默认: 200）
--memory-limit   内存限制（默认: 7GB）
--max-retries    最大重试次数（默认: 2）
--resume         从上次中断处继续
```

### 2. run_v26_full_harvest.py（全量收割）
**用途**: 大规模数据处理，性能优先

**核心特性**:
- 4进程并行提取
- 动态批次大小（内存自适应）
- 特征剪枝（控制在8000维）
- 幂等性保证（可重启不重不漏）

**参数说明**:
```bash
--limit       处理比赛数量限制
--workers     并行进程数（默认: 4）
--max-features 最大特征维度（默认: 8000）
```

### 3. run_v26_full_pipeline.py（完整流水线）
**用途**: 端到端测试

**核心功能**:
- L1数据采集
- L2特征解析
- L3特征提取
- 模型训练

## 流水线健康监控

### 健康指标说明
```json
{
  "health_score": 85,          // 健康评分 (0-100)
  "health_status": "healthy",  // 健康状态: healthy/degraded/critical
  "pipeline_stats": {
    "throughput_per_hour": 1200,     // 每小时处理场次
    "feature_dimension_counts": {    // 特征维度分布
      "min": 48,
      "max": 8000,
      "avg": 3500
    }
  },
  "alerts": [                   // 告警列表
    {
      "level": "warning",
      "message": "内存使用率超过80%"
    }
  ]
}
```

### 监控命令
```bash
# 实时监控收割进度
tail -f logs/auto_harvest.log

# 查看流水线处理日志
tail -f logs/pipeline.log

# 检查批次处理日志
ls -la logs/v26_batch*.log

# 使用监控脚本
./scripts/monitor_pipeline.sh     # 实时监控
./scripts/check_v26_progress.sh   # 检查进度
```

## V25.1 万能自适应特征提取引擎

### 核心突破
- **零硬编码**: 自动发现并提取所有数值型特征
- **递归打平**: 处理任意深度的嵌套 JSON 结构
- **全量吞噬**: 48维 → 12061维（251倍增长）
- **动态类型发现**: 自动转换 int/float/百分比/布尔值
- **特征对齐**: NaN 填充确保特征矩阵一致性

### 使用方式
```bash
# L2 特征解析（使用 V25.1 自适应引擎）
python main_production.py l2-parse --extractor-version V25.1

# 批量处理
python main_production.py l2-parse --batch --limit 50

# 单场比赛
python main_production.py l2-parse --match-id 123456
```

### 核心文件
- `src/processors/v25_production_extractor.py` - V25.1 自适应提取器

## 数据文件说明

| 文件路径 | 说明 | 格式 |
|----------|------|------|
| `data/processed/V26_Baseline_40D.parquet` | V26 基线特征数据（40维） | Parquet |
| `data/processed/V26_Gold_9305.parquet` | V26 黄金数据集（9305场） | Parquet |
| `data/processed/V26_Feature_Distribution.png` | 特征分布可视化 | PNG |
| `data/monitoring/pipeline_health.json` | 流水线健康状态 | JSON |

## 收割脚本对比

| 脚本 | 用途 | 特性 | 推荐场景 |
|------|------|------|----------|
| `auto_harvest_batches.py` | 自动分批收割 | 内存监控、断点续传、失败重试 | **生产环境**（推荐） |
| `run_v26_full_harvest.py` | 全量收割 | 4进程并行、特征剪枝、幂等性 | 大规模数据处理 |
| `run_v26_full_pipeline.py` | 完整流水线 | L1+L2+训练一体化 | 端到端测试 |

## V26.1 数据流架构

```
┌─────────────────────────────────────────────────────────────┐
│                    V26.1 数据流架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  L1: FotMob API 数据采集                              │  │
│  │  - v50_autonomous_season_discoverer.py (赛季发现)     │  │
│  │  - v50_rich_l1_scanner.py (Rich L1 扫描)              │  │
│  │  - 输出: matches 表 (match_id, home_score, status)   │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  L2: Schema-Agnostic 递归解析                          │  │
│  │  - v25_production_extractor.py (自适应提取)           │  │
│  │  - 输出: raw_match_data 表 (JSON 原始数据)           │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  L3: 特征提取 + 数据收割                               │  │
│  │  - auto_harvest_batches.py (自动分批)                │  │
│  │  - run_v26_full_harvest.py (全量收割)                │  │
│  │  - 输出: 特征文件 (parquet/csv)                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  L4: 模型训练 + 预测                                   │  │
│  │  - pipeline_v19_4.py (V19.4 流水线)                  │  │
│  │  - XGBoost 2.0+ 训练                                   │  │
│  │  - 输出: 模型文件 (.pkl)                               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 常见工作流

### 新赛季数据采集
```bash
# 1. L1 数据收割
python main_production.py l1-harvest --season 2425 --target 500

# 2. L2 特征解析
python main_production.py l2-parse --batch --limit 500

# 3. 自动分批收割
python scripts/auto_harvest_batches.py --batch-size 200

# 4. 检查健康状态
cat data/monitoring/pipeline_health.json | jq '.health_status'
```

### 断点续传
```bash
# 从上次中断处继续
python scripts/auto_harvest_batches.py --resume

# 查看当前进度
cat data/monitoring/pipeline_health.json | jq '.progress'
```

## 故障排查

### 内存不足
```bash
# 减小批次大小
python scripts/auto_harvest_batches.py --batch-size 100

# 降低内存限制
python scripts/auto_harvest_batches.py --memory-limit 6
```

### 特征维度过高
```bash
# 启用特征剪枝
python scripts/run_v26_full_harvest.py --max-features 6000
```

### 处理速度慢
```bash
# 增加并行进程数
python scripts/run_v26_full_harvest.py --workers 8
```

## 相关技能
- `data-collection`: FotMob API 数据采集
- `data-engineering`: ETL 数据管道
- `feature-engineering`: 特征工程专项
- `machine-learning-engineering`: ML 模型优化

## 最佳实践

1. **生产环境**: 优先使用 `auto_harvest_batches.py`
2. **大规模数据**: 使用 `run_v26_full_harvest.py`
3. **监控**: 定期检查 `pipeline_health.json`
4. **内存**: 批次大小不超过 200 场
5. **容错**: 启用断点续传和失败重试

---
*Last updated: 2025-12-28*
*Version: V26.1*
*Target: 生产级"零缺陷"收割流水线*
