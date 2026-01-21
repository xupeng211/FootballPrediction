# FootballPrediction Engine

> **"以年化 25% 的真实收益率为北极星指标，构建一个可验证、可复制、可持续的体育预测系统。"**
>
> **📌 Production-Ready**: V41.370 Consolidated Engine | Golden Shield Audit | One-Click Deployment
>
> **📘 开发指南**: 详见 [CLAUDE.md](CLAUDE.md)

---

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![V41.370](https://img.shields.io/badge/version-V41.370%20Production%20Ready-brightgreen.svg)](https://github.com/xupeng211/FootballPrediction)
[![Tests](https://img.shields.io/badge/tests-60%2B%20passed-success.svg)](tests/)

**V41.370 Grand Deployment | Consolidated Engine | 1770 Perfect Samples | 48% Accuracy Baseline**

---

## 📋 目录

- [项目简介](#项目简介)
- [系统架构](#系统架构)
- [数据资产](#数据资产)
- [快速开始](#快速开始)
- [生产运维](#生产运维)
- [技术栈](#技术栈)
- [版本演进](#版本演进)

---

## 🎯 项目简介

**FootballPrediction Engine** 是一个基于 XGBoost 3.0+ 的专业足球比赛预测系统，采用工业级数据采集流水线和机器学习引擎，提供可验证的预测能力。

### 核心特性

- **🛡️ Ghost Protocol V141.0**: 30+ 浏览器指纹池 + 人类行为模拟
- **🏆 Consolidated Engine V41.350**: 浏览器单例 + 金盾校验
- **📊 多源数据采集**: FotMob API + OddsPortal RPA
- **🔮 XGBoost 预测引擎**: 6000+ 维深度特征
- **🚀 一键部署**: `python main.py --task harvest --limit 2000`

### 数据资产统计

| 指标 | 数值 | 说明 |
|------|------|------|
| **Perfect Samples** | 1,770 | 三位一体样本 (Odds + Lineups + Features) |
| **Accuracy Baseline** | 48% | 真赛前基线准确率 |
| **Feature Dimensions** | 6,000+ | V26.8 深度特征向量 |
| **Leagues Covered** | 15+ | 顶级联赛覆盖 |
| **Inference Latency** | <100ms | 单次预测响应时间 |

---

## 🏗️ 系统架构

### V41.350 Consolidated Engine

```
╔══════════════════════════════════════════════════════════════════════╗
║                  V41.350 CONSOLIDATED ENGINE                           ║
║  ┌─────────────────────────────────────────────────────────────────┐  ║
║  │  BrowserManager (V41.291) - Memory-Optimized Singleton        │  ║
║  │  • Single Browser Instance (1.2GB → 300MB)                      │  ║
║  │  • Isolated BrowserContext per Worker                          │  ║
║  │  • Anti-modal Script Injection                                 │  ║
║  └─────────────────────────────────────────────────────────────────┘  ║
║  ┌─────────────────────────────────────────────────────────────────┐  ║
║  │  IntegrityGuard (V41.287) - Golden Shield Validation          │  ║
║  │  • Feature Richness Calculation (Recursive)                    │  ║
║  │  • Core Metrics Check (xG, Shots, Possession)                 │  ║
║  │  • Quality Rating (EXCELLENT/GOOD/FAIR/POOR)                  │  ║
║  └─────────────────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════╝
                              ↓
╔══════════════════════════════════════════════════════════════════════╗
║                    MULTI-SOURCE DATA COLLECTION                        ║
║  ┌──────────────────────┐  ┌──────────────────────┐                  ║
║  │  FotMob V144.5       │  │  OddsPortal V144.2   │                  ║
║  │  • Unified Schema    │  │  • Enhanced Stealth  │                  ║
║  │  • L2 API Harvest    │  │  • RPA Extraction    │                  ║
║  │  • Real-time Stats   │  │  • Pinnacle Odds     │                  ║
║  └──────────────────────┘  └──────────────────────┘                  ║
╚══════════════════════════════════════════════════════════════════════╝
                              ↓
╔══════════════════════════════════════════════════════════════════════╗
║                         PERSISTENCE LAYER                              ║
║  PostgreSQL 15 + Redis 7 + Unified Schema (V36.0)                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 数据流水线

```
┌─────────────────────────────────────────────────────────────────┐
│  L1: FotMob API - 基础数据层                                    │
│  • 比赛基础信息: league, season, teams, match_time               │
│  • V36.0 Schema: season_id, season_name, match_time_utc         │
│  • 实时统计数据: xG, shots, possession                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  L2: URL Harvest - 链接收割层                                    │
│  • 自动导航联赛页面                                              │
│  • 智能提取比赛详情链接                                          │
│  • 仅提取新格式 URL: /football/.../.../...                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  L3: RPA Extraction - 赔率提取层                                 │
│  • 智能轮询: wait_for_selector(60s)                             │
│  • 悬停自愈: scroll_into_view_if_needed()                       │
│  • 提取目标: Pinnacle 开盘赔率 + 时间戳                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PostgreSQL 持久层                                               │
│  matches 表 + metrics_multi_source_data 表                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 数据资产

### Perfect Samples (三位一体)

```sql
-- 查询三位一体样本数量
SELECT COUNT(*) as perfect_samples
FROM matches m
INNER JOIN match_odds_intelligence modi ON m.match_id = modi.match_id
INNER JOIN match_lineups ml ON m.match_id = ml.match_id
WHERE m.technical_features IS NOT NULL;
-- Result: 1,770 samples
```

### 质量评级分布 (Golden Shield)

| 评级 | 标准 | 样本数 | 占比 |
|------|------|--------|------|
| **EXCELLENT** | ≥100维 + 4项核心指标 | 856 | 48.4% |
| **GOOD** | ≥80维 + 3项核心指标 | 423 | 23.9% |
| **FAIR** | ≥50维 + 2项核心指标 | 287 | 16.2% |
| **POOR** | <50维 或 <2项核心指标 | 204 | 11.5% |

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: 7+ (可选)
- **内存**: 8GB+ (推荐 24GB)
- **操作系统**: Linux/WSL2/macOS

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填写数据库连接信息

# 5. 启动数据库服务
docker-compose up -d db redis

# 6. 运行一键收割
python main.py --task harvest --limit 2000
```

### 一键命令入口

```bash
# V41.360: 一键收割 (Consolidated Engine)
python main.py --task harvest --limit 2000

# V41.360: Golden Shield 审计
python main.py --task audit

# 传统模式 (向后兼容)
python main.py --source fotmob --mode single --limit 10
python main.py --source oddsportal --mode cruise
```

### Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

---

## 🔧 生产运维

### 代码质量检查

```bash
# 格式化代码
ruff format src/ tests/

# Lint 检查
ruff check src/ tests/

# 类型检查
mypy src/

# 安全扫描
bandit -r src/

# 运行测试
make verify
```

### 数据库维护

```bash
# 进入 PostgreSQL Shell
make db-shell

# 查看数据采集统计
SELECT source_name, COUNT(*) as total_records
FROM metrics_multi_source_data
GROUP BY source_name;

# 检查数据完整性
SELECT
    CASE
        WHEN integrity_score < 1.02 THEN 'Too Low'
        WHEN integrity_score > 1.08 THEN 'Too High'
        ELSE 'Valid'
    END as score_category,
    COUNT(*) as count
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P'
GROUP BY score_category;
```

### 故障排除

**症状**: HTTP 429/403 错误频繁出现
```bash
# 1. 测试代理连通性
python main.py --test-proxy

# 2. 等待冷却期 (6-24小时)
```

**症状**: WSL2 无法连接 Docker 容器
```bash
# 1. 验证网桥 IP
ping 172.25.16.1

# 2. 重启网络
wsl --shutdown
```

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.11+ | 核心开发语言 |
| **数据库** | PostgreSQL | 15 | 生产数据存储 |
| **缓存** | Redis | 7 | 分布式缓存 |
| **浏览器** | Playwright | 1.57+ | 智能网页自动化 |
| **ML 框架** | XGBoost | 3.1+ | 预测模型 |
| **Web** | FastAPI | 0.124+ | REST API |
| **测试** | Pytest | 9.0+ | 单元测试 |
| **代码质量** | Ruff | 0.14+ | 格式化 + Lint |

---

## 🏭 自动化特征工厂 (V41.500+)

### V41.500 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    V41.500 Automated Pipeline                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Schema Map   │───▶│Path Resolver │───▶│Feature       │      │
│  │ (YAML 配置)   │    │(安全路径访问)  │    │Factory       │      │
│  └──────────────┘    └──────────────┘    │(特征工厂)    │      │
│                                          └──────────────┘      │
│                                                  │              │
│                                                  ▼              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              PipelineIntegrator                          │   │
│  │  数据采集完成后自动生成 V41.500 特征并写入 golden_features │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Database (matches 表)                       │   │
│  │  golden_features = V41.500 + 原有特征                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 文件路径 | 功能 |
|------|----------|------|
| **Schema Map** | `config/schema_map.yaml` | JSON 路径配置，支持数据源变动 |
| **Path Resolver** | `src/processors/path_resolver.py` | 安全路径访问，带默认值容错 |
| **Feature Factory** | `src/processors/feature_factory.py` | 特征生成引擎（疲劳度/缺阵/赔率） |
| **Pipeline Integrator** | `src/api/collectors/v41_500_pipeline_integration.py` | 流水线自动集成器 |

### 如何更新 `schema_map.yaml`

当数据源结构变化时，只需更新 `config/schema_map.yaml`，无需修改代码：

```yaml
# 示例：添加新的数据源路径
new_source:
  match_data:
    path: "data.match"
    home_team: "teams.home.name"
    unavailable: "teams.home.unavailable_list"
```

### V41.500 新增特征定义

| 特征类别 | 特征名称 | 说明 |
|----------|----------|------|
| **疲劳度** | `home_rest_days` | 主队休息天数 |
| | `away_is_busy_week` | 客队是否为忙碌周（休息<4天） |
| | `diff_rest_days` | 休息天数差值 |
| **缺阵** | `home_unavailable_total_count` | 主队缺阵人数 |
| | `home_unavailable_total_market_value` | 主队缺阵总身价（欧元） |
| | `home_unavailable_star_count` | 主队缺阵球星数（身价>30M） |
| **首发战力** | `home_starter_avg_rating` | 主队首发平均评分 |
| | `home_missing_stars_count` | 主队缺阵大腿数（评分>=7.5） |
| **赔率动向** | `home_drop_ratio` | 主胜赔率下降比率 |
| | `total_movement` | 赔率总变化幅度 |
| **联赛等级** | `is_top_5_league` | 是否为五大联赛 |

### 使用方式

```bash
# 1. 数据采集完成后自动处理
python -c "
from src.api.collectors.v41_500_pipeline_integration import process_match_after_collection
process_match_after_collection('match_id')
"

# 2. 批量处理最近 100 场比赛
python src/api/collectors/v41_500_pipeline_integration.py

# 3. 在代码中调用
from src.processors.feature_factory import get_feature_factory
factory = get_feature_factory()
features = factory.process_match(match_data)
```

### 测试覆盖

```bash
# 运行 V41.500 端到端测试
pytest tests/ai/test_v41_500_pipeline.py -v

# 包含 29 个测试用例：
# - Schema Map 配置测试
# - Path Resolver 路径解析测试
# - Feature Factory 特征生成测试
# - V41.510 鲁棒性测试（空值/损坏 JSON）
```

---

## 📈 版本演进

### 核心组件版本系列

| 组件 | 版本系列 | 说明 |
|------|----------|------|
| **Consolidated Engine** | V41.350 | 浏览器单例 + 金盾校验 |
| **Command Center** | V41.360 | 一键入口 + 生产就绪 |
| **Data Collection** | V41.x | 运维工具和采集器 |
| **Harvester Service** | V142.0 | 统一收割服务架构 |
| **Ghost Protocol** | V141.0 | 反爬检测基础能力 |

### 关键里程碑

- **V41.370** (2026-01): Grand Deployment - 远程仓库发布
- **V41.360** (2026-01): Production Lockdown - 代码合规与脱敏
- **V41.350** (2026-01): The Great Consolidation - 核心组件固化为生产标准
- **V144.7** (2026-01): Multi-Source Command Center - 统一命令入口
- **V26.8** (2024-11): 6000+ 维深度特征引擎

---

## 📄 许可证

[MIT License](LICENSE)

---

## 🙏 致谢

本项目由 FootballPrediction Engine 团队开发和维护。

**联系方式**: https://github.com/xupeng211/FootballPrediction

---

**最后更新**: 2026-01-21 | **版本**: V41.370 "The Grand Deployment"
