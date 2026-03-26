# TITAN V5.2 技术规格说明书

> **版本**: V5.2.0-HOME-FORTRESS  
> **发布日期**: 2026-03-14  
> **文档状态**: 生产级稳定版  
> **适用模型**: TITAN_CORE_V5_PROD

---

## 1. 38维特征大图谱

### 1.1 特征架构演进

| 版本 | 特征维度 | 核心升级点 |
|------|----------|------------|
| V4.0 | 11维 | 基础战斗特征 (Elo+身价+H2H) |
| V5.0 | 30维 | 滚动统计 + 效率特征 + 平局体质 |
| **V5.2** | **38维** | **主客场分离感知 + 堡垒指数** |

### 1.2 特征分层详解

#### 第一层：基础战斗特征 (11维)

| 字段 | 类型 | 定义 | 默认值 |
|------|------|------|--------|
| `home_elo_pre` | float | 主队赛前Elo评分 | 1500 |
| `away_elo_pre` | float | 客队赛前Elo评分 | 1500 |
| `elo_diff` | float | Elo差值 (主-客) | 0 |
| `expected_home_win` | float | 主队预期胜率 | 0.45 |
| `expected_away_win` | float | 客队预期胜率 | 0.30 |
| `log_home_squad_value` | float | 主队身价对数值 | 18.0 |
| `log_away_squad_value` | float | 客队身价对数值 | 18.0 |
| `home_mv_share` | float | 主队身价占比 | 0.5 |
| `h2h_home_win_ratio` | float | 历史交锋主胜率 | 0.4 |
| `h2h_draw_ratio` | float | 历史交锋平局率 | 0.25 |
| `h2h_avg_goal_diff` | float | 历史交锋平均净胜球 | 0.0 |

#### 第二层：滚动统计特征 (7维)

| 字段 | 类型 | 定义 | 计算窗口 |
|------|------|------|----------|
| `home_last5_xg_avg` | float | 主队近5场平均xG | 5场 |
| `away_last5_xg_avg` | float | 客队近5场平均xG | 5场 |
| `home_last5_win_rate` | float | 主队近5场胜率 | 5场 |
| `away_last5_win_rate` | float | 客队近5场胜率 | 5场 |
| `home_last5_draw_rate` | float | 主队近5场平局率 | 5场 |
| `away_last5_draw_rate` | float | 客队近5场平局率 | 5场 |
| `rest_days_diff` | float | 休息天数差 (主-客) | - |

#### 第三层：效率特征 (5维)

| 字段 | 类型 | 定义 | 公式 |
|------|------|------|------|
| `home_shot_conversion` | float | 主队射门转化率 | goals/shots |
| `away_shot_conversion` | float | 客队射门转化率 | goals/shots |
| `home_finishing_efficiency` | float | 主队终结效率 | goals/xG |
| `away_finishing_efficiency` | float | 客队终结效率 | goals/xG |
| `finishing_efficiency_diff` | float | 终结效率差 | 主-客 |

#### 第四层：平局体质特征 (7维)

| 字段 | 类型 | 定义 | 阈值 |
|------|------|------|------|
| `home_draw_rate` | float | 主队赛季平局率 | - |
| `away_draw_rate` | float | 客队赛季平局率 | - |
| `home_draw_tendency` | float | 主队平局倾向指数 | >0.6偏高 |
| `away_draw_tendency` | float | 客队平局倾向指数 | >0.6偏高 |
| `combined_draw_probability` | float | 综合平局概率 | 0-1 |
| `match_stalemate_index` | float | 比赛僵局指数 | >0.7僵局 |
| `tactical_stalemate_index` | float | 战术僵局指数 | >0.7僵局 |

#### 第五层：V5.2 主场堡垒特征 (8维) ⭐

| 字段 | 类型 | 定义 | 数学逻辑 |
|------|------|------|----------|
| `home_last5_home_only_xg` | float | 主队主场近5场xG | Σ(xG_home) / 5 |
| `away_last5_away_only_xg` | float | 客队客场近5场xG | Σ(xG_away) / 5 |
| `home_fortress_index` | float | 主场堡垒指数 | 见下文公式 |
| `away_away_form_ratio` | float | 客战适应率 | away_points / total_points |
| `home_rest_advantage` | float | 主场休息优势 | rest_home - rest_away |
| `elo_rest_synergy` | float | 战力体能协同 | 见下文公式 |
| `home_pressure_score` | float | 主场压力分 | crowd * form_weight |
| `away_travel_fatigue` | float | 客场旅途疲劳 | distance_factor * rest_penalty |

### 1.3 核心数学公式

#### 主场堡垒指数 (Fortress Index)

```
fortress_index = (
    0.35 * (home_win_rate - away_win_rate) +
    0.25 * (home_xg_avg / (home_xg_avg + away_xg_avg)) +
    0.20 * rest_advantage_score +
    0.20 * home_pressure_score
) * normalization_factor

其中:
- normalization_factor = 1 / (1 + exp(-raw_score))  // Sigmoid归一化
- 取值范围: [0, 1]
- >0.65 视为"堡垒级主场优势"
```

#### 战力体能协同 (Elo-Rest Synergy)

```
elo_rest_synergy = (
    elo_diff * 0.6 +                    // 基础实力差 (60%)
    rest_advantage_score * 0.3 +         // 体能优势 (30%)
    home_field_advantage * 0.1          // 主场加成 (10%)
) * synergy_multiplier

其中:
- synergy_multiplier = 1 + (|elo_diff| / 400) * 0.1  // 实力差距放大器
- 正值: 主队综合优势
- 负值: 客队综合优势
```

---

## 2. 9900X 动力参数

### 2.1 硬件架构

```
处理器: AMD Ryzen 9 9900X (12核24线程)
架构:   Zen 5
主频:   4.4GHz (Boost 5.6GHz)
内存:   64GB DDR5-6000
存储:   NVMe SSD 2TB
```

### 2.2 Worker Pool 架构

```yaml
Pool配置:
  worker_count: 12          # 与物理核心数对齐
  max_concurrent: 10        # 预留2核给系统
  queue_size: 1000          # 待处理队列深度
  
Worker类型:
  harvester_workers: 8      # 数据收割Worker
  smelter_workers: 3        # 特征熔炼Worker
  prediction_workers: 1     # 预测服务Worker
```

### 2.3 性能基准

| 指标 | 数值 | 测试环境 |
|------|------|----------|
| 11,907场重炼耗时 | **71.9秒** | 全量数据集 |
| 单场平均处理 | 6.0ms | L2→L3完整流程 |
| 吞吐量 | 165场/秒 | 峰值并发 |
| 内存占用 | 4.2GB | Worker Pool满载 |
| CPU利用率 | 85-92% | 12核全负载 |

### 2.4 数据库连接池

```yaml
PostgreSQL连接池:
  max_connections: 50
  min_connections: 10
  connection_timeout: 30s
  idle_timeout: 10min
  max_lifetime: 30min
  
压测结论:
  - 50连接可支撑200并发查询
  - 特征熔炼批次: 500条/批次
  - 长查询隔离: 读写分离
```

---

## 3. 实战操盘指南

### 3.1 精英阈值策略

| 置信度阈值 | 覆盖率 | 预期胜率 | 建议仓位 |
|------------|--------|----------|----------|
| ≥0.70 | 8% | 78.5% | 5% (满仓) |
| ≥0.65 | 18% | 72.95% | 3.5% (标准) |
| ≥0.60 | 35% | 68.2% | 2% (轻仓) |
| <0.60 | - | - | **弃投** |

**核心结论**: 0.65精英阈值下，预期胜率**72.95%**

### 3.2 凯利仓位管理

#### 分数凯利公式

```
Kelly_Fraction = (p * b - q) / b

其中:
- p: 模型预测胜率 (如0.7295)
- q: 失败概率 (1 - p)
- b: 赔率净收益 (decimal_odds - 1)

实际仓位 = Kelly_Fraction * 0.25  // 保守系数
```

#### 3.5%标准仓位逻辑

```
假设:
- 模型置信度: 0.65
- 平均赔率: 1.85
- 凯利分数: 0.14

计算:
实际仓位 = 0.14 * 0.25 = 0.035 = 3.5%

意义:
- 单注风险控制在总资金的3.5%
- 连续30次失利后仍有65%本金
- 符合"生存优先"的职业操盘原则
```

### 3.3 入场信号矩阵

| 信号组合 | 权重 | 操作 |
|----------|------|------|
| 模型置信度≥0.65 + EV>0.05 | 40% | **标准入场** |
| fortress_index>0.65 + 主胜信号 | 25% | **堡垒加成** |
| elo_rest_synergy>0.3 + 置信度≥0.60 | 20% | **体能优势** |
| 赔率背离>15% + 凯利>0.03 | 15% | **价值投注** |

### 3.4 风险控制红线

```yaml
单日止损线: 总资金的15%
连续失利阈值: 5次后强制冷却24小时
单联赛仓位上限: 30% (避免集中风险)
周末高波动期: 仓位减半 (1.75%)
```

---

## 4. 模型规格

### 4.1 TITAN_CORE_V5_PROD

```yaml
算法: XGBoost Classifier
特征维度: 38维
训练样本: 11,907场 (2019-2025)
准确率: 65.31% (测试集) / 67.94% (交叉验证)
F1 Score: 0.6371
Log Loss: 0.9834
推理延迟: <100ms (单场比赛)
模型大小: 1.3MB
```

### 4.2 特征重要性TOP5

| 排名 | 特征 | 重要性 | 说明 |
|------|------|--------|------|
| 1 | elo_diff | 64.66% | 核心实力指标 |
| 2 | fortress_index | 12.34% | 主场优势(V5.2新增) |
| 3 | combined_draw_probability | 8.21% | 平局体质 |
| 4 | finishing_efficiency_diff | 5.87% | 终结效率差 |
| 5 | home_last5_home_only_xg | 4.32% | 主场xG(V5.2新增) |

---

## 5. 快速上手指南

### 5.1 环境启动

```bash
# 1. 启动Docker环境
docker-compose -f docker-compose.dev.yml up -d

# 2. 进入开发容器
docker-compose -f docker-compose.dev.yml exec dev bash

# 3. 验证模型
python scripts/ops/train_model_production.py --verify-only

# 4. 运行测试
npm test
```

### 5.2 生产收割流程

```bash
# L1: 赛程发现
npm run seed

# L2: 数据收割 (9900X Worker Pool)
npm run harvest:swarm

# L3: 特征熔炼 (38维)
npm run smelt

# PREDICT: 生成预测
npm run predict
```

### 5.3 关键命令速查

| 命令 | 用途 |
|------|------|
| `npm run titan:start` | 完整TITAN工作流 |
| `npm run titan:watch` | 哨兵监控模式 |
| `npm run predict:dry` | 试运行预测 |
| `npm run train` | 重训练模型 |

---

## 6. 附录

### 6.1 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|----------|
| V4.0 | 2026-02 | Smelter模块化重构 |
| V5.0 | 2026-03 | 30维特征上线 |
| **V5.2** | **2026-03-14** | **38维HOME-FORTRESS** |

### 6.2 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构
- [OPERATIONS_MANUAL.md](./OPERATIONS_MANUAL.md) - 运维手册
- [MODEL_V4_ANATOMY.md](./MODEL_V4_ANATOMY.md) - 模型解剖

### 6.3 联系方式

**维护团队**: V174 Engineering Team  
**最后更新**: 2026-03-14  
**状态**: 生产级稳定版

---

> ⚠️ **免责声明**: 本系统仅供技术研究与学习，不构成投资建议。使用本系统产生的任何决策，风险由使用者自行承担。
