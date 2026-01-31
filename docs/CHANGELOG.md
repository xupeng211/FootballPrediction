# 版本历史 (CHANGELOG)

本文档记录 FootballPrediction 项目的所有重要版本变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [V1.0] - 2026-01-14

### 文档重构 - 精简版 CLAUDE.md

#### 变更
- 将 CLAUDE.md 从 2328 行精简到 428 行（减少 82%）
- 新增 `docs/module_reference.md` - 核心模块详细说明
- 新增 `docs/deployment.md` - Docker 部署完整指南
- 保留 MCP 和 Skills 配置说明
- 优化文档导航结构

#### 改进
- 更清晰的快速参考章节
- 更简洁的架构概览
- 更易读的开发指南

---

## [V32.1] - 2026-01-11

### Production Guard & Log Lifecycle Management

#### 新增
- 生产守护系统 (Production Guard)
- 日志生命周期管理
- 多进程 8W 并发处理
- 列表狩猎 (List Hunting) 功能
- 就地重试机制

#### 改进
- 系统稳定性增强
- 日志轮转和清理机制
- 错误恢复能力提升

---

## [V151.1] - 2026-01-11

### Retry + Hash Hunting Edition

#### 新增
- **Hash Hunting Engine**: 通过队名搜索自动发现 OddsPortal URL
- **重试机制**: retry_count 字段记录重试次数（最多 3 次）
- **自动放弃**: 超过 3 次失败后标记为 `abandoned` 状态
- **并发采集**: V151.3 多进程并发收割器
- **哈希缓存保护**: V151.3 防止数据库连接中断导致数据丢失

#### 数据库迁移
- `v151_3_add_retry_count.sql`: 添加重试计数和放弃状态字段

---

## [V150.0] - 2026-01-10

#### 新增
- 新增运维脚本目录 `scripts/ops/`
- 端到端链接测试
- URL 健康检查
- 生产环境冒烟测试
- 数据质量仪表盘

---

## [V149.0] - 2026-01-06

#### 修复
- SchemaManager API 修复
- Circuit Breaker 硬编码问题修复

#### 变更
- 160 模块稳定版本发布
- 旧脚本归档至 `scripts/archive/`

---

## [V148.5] - 2026-01-05

### Final Master Sweep

#### 变更
- 总攻最终生产基线
- 需重新训练模型

---

## [V148.0] - 2026-01-04

#### 变更
- 模型架构调整
- 需重新训练模型

---

## [V144.7] - 2026-01-06

### Multi-Source Command Center

#### 新增
- `--source` 参数支持数据源切换 (oddsportal/fotmob)
- Ghost Protocol 统一验证日志
- 环境预检功能 (WSL2 检测、代理自动发现、IP 检测)
- FotMob 批量采集支持

#### 路由实现
- `run_oddsportal_mode()`: OddsPortal RPA 采集
- `run_fotmob_mode()`: FotMob API 采集

---

## [V144.5] - 2026-01-05

### FotMob API 升级

#### 新增
- V36.0 统一 Schema
- season_id, season_name, match_time_utc 字段

---

## [V144.2] - 2026-01-04

### Ghost Protocol 增强

#### 新增
- WSL2 自动代理发现
- 30+ 主流浏览器指纹池
- 5 种常见屏幕分辨率随机化
- 人类行为模拟 (滚动 + 点击噪声)
- 深度拦截检测 (Cloudflare, IP 封禁)
- 自动错误截图

---

## [V142.0] - 2025-12-30

### HarvesterService 重构

#### 新增
- 统一收割服务
- 队列驱动架构
- Ghost Protocol 集成
- 全路径试错匹配
- 信号处理 (SIGINT/SIGTERM)
- 优雅关闭机制
- 流量弹性 (V142.5)

#### 废弃
- 旧版 `production_harvester.py` 移至 `scripts/archive/`

---

## [V141.0] - 2025-12-28

### Ghost Protocol 集成

#### 新增
- BaseExtractor 反爬检测基础能力
- 浏览器指纹混淆
- WSL2 自动代理发现

---

## [V140.0] - 2025-12-25

### TeamNameNormalizer

#### 新增
- 全路径试错匹配
- Fuzzy matching 算法
- 多连字符队名处理
- 去重保护

#### 队名匹配逻辑变更
- 所有采集器使用新的队名匹配逻辑

---

## [V139.0] - 2025-12-24

### Auto Cruise Controller

#### 新增
- L2: URL Harvest 链接收割层
- 自动导航联赛页面
- 智能提取比赛详情链接
- **仅支持新格式 URL**: `/football/.../.../...`

#### 废弃
- 旧格式 URL `/match/{XXXXX}/` 已永久废弃

---

## [V138.0] - 2025-12-23

#### 新增
- URL 搜索并发支持
- URL 格式验证配置
- V138 系列探索性版本

---

## [V126.7] - 2025-12-18

### 数据库一致性工具

#### 新增
- `check_db_consistency.py`: 特征维度一致性检查
- `lock_feature_manifest.py`: 特征清单锁定
- `reprocess_from_local.py`: 离线特征重解析
- League ID 字段 (双重识别: ID + Name)

#### 数据库迁移
- `v26_7_add_league_id.sql`
- `v26_7_data_label_cleanup.sql`
- `v26_7_history_alignment.sql`

---

## [V26.6] - 2025-12-17

### 全球数据支持

#### 新增
- **31 个全球联赛** 覆盖欧洲、美洲、亚洲、非洲
- Tier 质量分级系统 (Premium/Standard/Basic)
- YAML 配置驱动 (`config/global_harvest_list.yaml`)
- 历史回填引擎 (3-5 年数据)
- V26.5 哨兵配置集成

#### 全球联赛清单

**Tier 1 Premium (5 大联赛)**:
- 英超 (47), 西甲 (87), 德甲 (78), 意甲 (126), 法甲 (53)

**Tier 2 Standard (17 个次级联赛)**:
- 英冠、西乙、德乙、意乙、葡超、荷甲、比甲、苏超、土超、希超、俄超、乌超、美职联、巴甲、日职联、沙特超、澳超

**Tier 3 Basic (9 个基础联赛)**:
- 阿甲、墨超、中超、K联赛、阿联酋职业联赛、印超、南非超、埃及超、尼日利亚职业足球联赛

---

## [V26.5] - 2025-12-16

### 自动巡航哨兵 & IP 消耗预警

#### 新增
- **CollectionSentry**: 自动巡航哨兵系统
  - 滑动窗口统计 (成功率 < 70% 触发停机)
  - 连续失败监控 (超过 6 次触发停机)
  - 自动设置 12 小时冷却期
- **IP 消耗预警**: 可用代理 < 2 时红色警示
- **抢救优先级过滤**: 5 大联赛数据优先

---

## [V82.6] - 2025-12-15

### 智能轮询与悬停自愈

#### 新增
- **智能轮询**: `wait_for_selector(60s)` 替代硬等待
- **悬停自愈**: 鼠标抖动自愈 (±5px) 重新触发 tooltip
- **IP 健康监控**: 连续 3 次错误 → 5 分钟冷却
- **数据完整性审计**: `Score = 1/P1 + 1/P2 + 1/P3`

#### 性能提升
- 平均响应时间: 20s → 3s (85% 提升)
- 悬停成功率: 75% → 92% (23% 提升)
- 数据完整性: 89% → 96% (8% 提升)

---

## [V56.4] - 2025-12-14

### 三层生产级架构

#### 新增
- Master 调度层: 跨赛季/跨联赛编排
- Production 提取层: 智能轮询 + 悬停自愈
- Database 持久层: Unified Schema

#### 核心特性
- 智能跳过检测: 自动跳过已有 opening_time 的比赛
- 反封禁机制: 每 30 场休息 60 秒
- IP 健康监控: 连续 3 次连接错误 → 5 分钟冷却

---

## [V26.8] - 2025-12-20

### 联赛专项模型分发器

#### 新增
- **ModelDispatcher**: 联赛专项模型自动分发
- 支持的联赛专项模型:
  - `v26.8_epl_production.pkl` - 英超
  - `v26.8_la_liga_production.pkl` - 西甲
  - `v26.8_ligue1_production.pkl` - 法甲
  - `v26.8_bund_production.pkl` - 德甲

---

## [V26.7] - 2025-12-18

### 19 维完全对齐特征

#### 新增
- 19 维赛前特征 (滚动特征 + 积分榜特征 + 高级特征)
- 特征清单管理器 (6346 维锁定)
- 离线解析能力 (零网络请求)
- 数据库一致性检查

#### 特征列表
- 滚动特征 (8个): rolling_xg, shots_on_target, possession, team_rating
- 积分榜特征 (7个): table_position, points, form_points
- 高级特征 (4个): elo_gap, fatigue_index

---

## [V25.1] - 2025-12-10

### 万能自适应特征提取

#### 新增
- 自适应特征提取引擎
- 48 → 12061 维特征扩展

---

## [V17.0] - 2025-11-20

### 滚动特征训练引擎

#### 新增
- V17MLEngine: 16 维特征滚动训练
- V17Predictor: 统一推理接口

---

## 版本兼容性矩阵

| 组件版本 | Python | PostgreSQL | Docker | 备注 |
|---------|--------|------------|--------|------|
| V32.x | 3.11+ | 15 | 24+ | 当前生产版本 |
| V151.x | 3.11+ | 15 | 24+ | Retry + Hash Hunting |
| V149.x | 3.11+ | 15 | 24+ | 稳定版本 |
| V148.x | 3.11+ | 15 | 24+ | 生产推荐 |
| V144.x | 3.11+ | 15 | 24+ | 多数据源支持 |
| V142.x | 3.11+ | 15 | 24+ | HarvesterService |
| V140.x | 3.10+ | 14 | 20+ | 旧版本，建议升级 |

---

## 升级前检查清单

- [ ] 备份数据库 (`make db-backup`)
- [ ] 备份模型文件 (`model_zoo/`)
- [ ] 运行完整测试 (`./scripts/run_checks.sh`)
- [ ] 检查 git diff 确认变更范围
- [ ] 准备回滚方案
- [ ] 阅读版本发布说明

---

## 升级流程

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 检查版本变更
git log --oneline -10

# 3. 备份数据
make db-backup

# 4. 运行测试
make verify

# 5. 应用数据库迁移（如有）
alembic upgrade head

# 6. 重启服务
make restart

# 7. 验证服务健康
make health
```
