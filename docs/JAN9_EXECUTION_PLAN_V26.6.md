# 1月9日全球数据收割第一波预案 - V26.6

**版本**: V26.6
**日期**: 2026-01-06
**目标**: 在 OddsPortal 冷却期结束后，分阶段执行 FotMob 全球数据扩充
**作者**: Data Engineering Expert

---

## 📋 执行摘要

本预案基于 V26.6 FotMob 全球数据扩充系统，规划了 **3 个阶段** 的执行清单，确保高价值数据优先入库，同时保护 IP 资源避免封禁。

### 核心原则

1. **数据价值优先**: Tier 1 Premium 联赛 > Tier 2 Standard > Tier 3 Basic
2. **安全第一**: 严格遵守 V26.5 哨兵系统规则，成功率 < 70% 自动停机
3. **渐进式验证**: 每个阶段完成后验证数据质量，再进入下一阶段
4. **IP 资源保护**: 批次间隔 10 秒 + Jittering 2-5 秒，避免触发限流

---

## 🚨 执行前检查清单

### 环境健康检查

```bash
# 1. 检查数据库连接
docker-compose exec db pg_isready -U football_user -d football_db

# 2. 检查当前 FAILED 记录数量
psql -h localhost -U football_user -d football_db -c "
SELECT COUNT(*) as failed_count
FROM matches
WHERE status = 'FAILED';
"

# 3. 运行 V26.5 复工自检脚本
python scripts/ops/v26_5_resume_check.py

# 4. 验证 FotMob API 可用性
python -c "
from src.api.collectors.fotmob_core import FotMobCoreCollector
collector = FotMobCoreCollector()
# 仅测试连接，不采集数据
import requests
try:
    response = requests.get('https://www.fotmob.com/api/leagues', timeout=5)
    print(f'✅ FotMob API 可用: HTTP {response.status_code}')
except Exception as e:
    print(f'❌ FotMob API 不可用: {e}')
"
```

### 代理资源检查

```bash
# 检查可用代理数量
python scripts/ops/v26_5_quality_dashboard.py

# 预期输出: 可用代理 >= 2 个
# 如果 < 2 个，先补充代理资源再执行
```

### 哨兵系统检查

```bash
# 检查是否有冷却期锁
echo $COLLECTION_PAUSE_UNTIL

# 如果有值，等待冷却期结束后再执行
# 或手动清除（仅用于测试）: unset COLLECTION_PAUSE_UNTIL
```

---

## 📊 Phase 1: 抢救 801 条核心失败数据

**目标**: 优先抢救 V26.5 系统遗留的 801 条 FAILED 记录
**预计时间**: 30-60 分钟（取决于失败原因）
**优先级**: 🔴 最高（Tier 1 联赛优先）

### 执行命令

```bash
# 使用 V26.5 抢救脚本，按联赛等级优先级排序
python scripts/maintenance/reprocess_failed_matches.py \
    --limit 100 \
    --enable-sentry
```

### 验收标准

- [ ] 801 条 FAILED 记录处理完成（成功或确认无法恢复）
- [ ] 哨兵系统未触发停机
- [ ] 成功率 >= 70%（Tier 1 联赛）
- [ ] 数据质量检查通过：`python main.py --mode check`

### 监控指标

```bash
# 实时查看抢救进度
tail -f logs/v26_5_reprocess.log

# 查看当前失败记录数量
psql -h localhost -U football_user -d football_db -c "
SELECT league_name, COUNT(*) as failed_count
FROM matches
WHERE status = 'FAILED'
GROUP BY league_name
ORDER BY COUNT(*) DESC;
"
```

### 异常处理

| 异常情况 | 处理方案 |
|---------|---------|
| 哨兵触发停机（成功率 < 70%） | 停止抢救，等待 12 小时冷却期后重试 |
| IP 封禁（HTTP 429/403） | 停止抢救，检查代理配置，等待 6-24 小时 |
| 数据库连接失败 | 检查 PostgreSQL 服务状态，重启 `make restart db` |
| 内存不足 | 减小 `--limit` 参数，分批次处理 |

---

## 🏆 Phase 2: Tier 1 联赛历史回填

**目标**: 回填 5 大联赛（英超、西甲、德甲、意甲、法甲）23/24 和 24/25 赛季数据
**预计时间**: 约 2 小时（3,652 场比赛）
**优先级**: 🟡 高（Premium 数据）

### 执行命令

```bash
# 干跑模式（推荐先测试）
python scripts/maintenance/fotmob_historical_backfill.py \
    --league-id 47 \
    --season "2324" \
    --dry-run

# 正式回填英超 23/24 赛季
python scripts/maintenance/fotmob_historical_backfill.py \
    --league-id 47 \
    --years 2 \
    --enable-sentry

# 回填所有 Tier 1 联赛（5 大联赛）
python scripts/maintenance/fotmob_historical_backfill.py \
    --years 2 \
    --enable-sentry
```

### 联赛清单（Tier 1 Premium）

| 联赛 | ID | 赛季 | 预估场数 | 预估时间 |
|------|----|----|----------|----------|
| 英超 | 47 | 23/24, 24/25 | 760 场 | ~25 分钟 |
| 西甲 | 87 | 23/24, 24/25 | 760 场 | ~25 分钟 |
| 德甲 | 78 | 23/24, 24/25 | 612 场 | ~20 分钟 |
| 意甲 | 126 | 23/24, 24/25 | 760 场 | ~25 分钟 |
| 法甲 | 53 | 23/24, 24/25 | 760 场 | ~25 分钟 |

**小计**: 3,652 场比赛，约 2 小时

### 验收标准

- [ ] 5 大联赛 2 个赛季数据全部回填完成
- [ ] 哨兵系统未触发停机
- [ ] 成功率 >= 80%（Tier 1 联赛质量要求更高）
- [ ] 数据质量检查通过：xG, Stats 覆盖率 >= 90%

### 监控指标

```bash
# 实时查看回填进度
tail -f logs/v26_6_backfill.log

# 查看已采集的比赛数量（按联赛）
psql -h localhost -U football_user -d football_db -c "
SELECT
    league_name,
    COUNT(*) as total_matches,
    COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END) as has_l2_data,
    COUNT(CASE WHEN l2_extracted_features IS NOT NULL THEN 1 END) as has_features
FROM matches
WHERE league_name IN ('Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1')
  AND season >= '2023-2024'
GROUP BY league_name
ORDER BY total_matches DESC;
"
```

### 异常处理

| 异常情况 | 处理方案 |
|---------|---------|
| 哨兵触发停机 | 检查失败原因，修复后继续 |
| 某个联赛全部失败 | 检查联赛 ID 是否正确，验证 FotMob API 可用性 |
| 数据质量差（xG 缺失） | 检查 `has_xg` 标记，某些联赛可能不支持 xG |
| 内存占用过高 | 减小批次大小（修改 `config/global_harvest_list.yaml` 中的 `batch_size`） |

---

## 🌍 Phase 3: Tier 2/3 联赛扩展

**目标**: 回填 Tier 2 Standard 和 Tier 3 Basic 联赛数据
**预计时间**: 约 3.5 小时（约 5,430 场比赛）
**优先级**: 🟢 中（扩展数据覆盖）

### 执行命令

```bash
# 回填所有启用的联赛（包括 Tier 2 和 Tier 3）
python scripts/maintenance/fotmob_historical_backfill.py \
    --years 3 \
    --enable-sentry

# 或指定某个联赛
python scripts/maintenance/fotmob_historical_backfill.py \
    --league-id 48 \
    --years 3 \
    --enable-sentry
```

### 联赛清单（Tier 2 Standard - 次级联赛）

| 联赛 | ID | 赛季 | 预估场数 |
|------|----|----|----------|
| 英冠 | 48 | 23/24, 24/25 | 552 场 |
| 葡超 | 155 | 23/24, 24/25 | 306 场 |
| 荷甲 | 129 | 23/24, 24/25 | 306 场 |
| 美职联 | 203 | 2024, 2025 | 580 场 |
| 日职联 | 345 | 2024, 2025 | 380 场 |
| 沙特超 | 410 | 2024, 2025 | 306 场 |

**小计**: 2,430 场比赛，约 1.5 小时

### 联赛清单（Tier 2/3 Basic - 其他联赛）

剩余 20 个联赛，约 3,000 场比赛，约 2 小时

### 验收标准

- [ ] 所有启用的联赛数据回填完成
- [ ] 哨兵系统未触发停机
- [ ] 成功率 >= 70%（Tier 2/3 联赛标准要求）
- [ ] 数据质量检查通过：基础数据覆盖率 >= 80%

### 监控指标

```bash
# 查看所有联赛的采集进度
psql -h localhost -U football_user -d football_db -c "
SELECT
    league_name,
    season,
    COUNT(*) as total_matches,
    COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END) as has_l2_data
FROM matches
WHERE season >= '2023-2024'
GROUP BY league_name, season
ORDER BY total_matches DESC;
"
```

### 异常处理

| 异常情况 | 处理方案 |
|---------|---------|
| 某些联赛全部失败 | 检查 `config/global_harvest_list.yaml` 中的联赛 ID，或禁用该联赛 |
| 内存不足 | 分批执行，每次处理 5-10 个联赛 |
| 网络超时 | 增加 `config/global_harvest_list.yaml` 中的 `batch_delay` |

---

## 🛡️ 安全措施和应急方案

### 哨兵系统规则（V26.5）

```yaml
触发条件:
  - 成功率 < 70%
  - AND 连续失败 >= 6 次

自动操作:
  - 设置环境变量 COLLECTION_PAUSE_UNTIL（12 小时冷却期）
  - 抛出 SecurityInterrupt 异常终止程序
  - 记录详细日志到 logs/v26_6_backfill.log
```

### IP 资源保护

- **批次间隔**: 10 秒（`batch_delay: 10`）
- **随机 Jittering**: 2-5 秒（防止模式识别）
- **批次大小**: 50 场/批（`batch_size: 50`）
- **代理轮换**: 自动切换代理（如果配置了多个代理）

### 应急停止

```bash
# 如果需要立即停止采集（按 Ctrl+C）
# 程序会执行优雅关闭，保存当前进度

# 如果哨兵触发停机，需要等待冷却期结束
# 或手动清除（不推荐）: unset COLLECTION_PAUSE_UNTIL
```

### 数据回滚

```bash
# 如果回填数据质量不达标，可以删除指定联赛的数据
psql -h localhost -U football_user -d football_db -c "
DELETE FROM matches
WHERE league_name = 'Premier League'
  AND season >= '2023-2024';
"
```

---

## 📊 执行后数据质量验证

### 验证脚本

```bash
# 1. 运行数据质量检查
python main.py --mode check

# 2. 查看各联赛数据覆盖情况
psql -h localhost -U football_user -d football_db -c "
SELECT
    league_name,
    COUNT(*) as total_matches,
    ROUND(100.0 * COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END) / COUNT(*), 2) as l2_coverage_pct,
    ROUND(100.0 * COUNT(CASE WHEN l2_extracted_features IS NOT NULL THEN 1 END) / COUNT(*), 2) as feature_coverage_pct
FROM matches
WHERE season >= '2023-2024'
GROUP BY league_name
ORDER BY l2_coverage_pct DESC;
"

# 3. 检查空心场次（被拒绝的比赛）
psql -h localhost -U football_user -d football_db -c "
SELECT
    league_name,
    COUNT(*) as hollow_matches
FROM matches
WHERE l2_raw_json IS NULL
  AND season >= '2023-2024'
GROUP BY league_name
ORDER BY hollow_matches DESC;
"
```

### 验收标准总结

| 指标 | Tier 1 Premium | Tier 2 Standard | Tier 3 Basic |
|------|---------------|-----------------|--------------|
| **成功率** | >= 80% | >= 70% | >= 60% |
| **L2 数据覆盖率** | >= 90% | >= 80% | >= 70% |
| **特征覆盖率** | >= 85% | >= 75% | >= 65% |
| **xG 数据覆盖** | >= 90% | >= 70% | N/A |
| **空心场次比例** | < 10% | < 20% | < 30% |

---

## 🎯 最终目标

### 预期成果

**Phase 1 完成**:
- ✅ 801 条 FAILED 记录抢救完成
- ✅ 核心数据质量提升至生产标准

**Phase 2 完成**:
- ✅ 5 大联赛 2 个赛季数据完整（3,652 场）
- ✅ Premium 数据库建立，支持高价值预测

**Phase 3 完成**:
- ✅ 全球 31 个联赛数据覆盖（约 9,082 场）
- ✅ 多元化数据生态，提升模型泛化能力

### 下一步计划

1. **特征工程重建**: 使用新的全球数据重新计算 V26.7 特征
2. **模型重新训练**: 使用扩充后的数据集训练 V26.9 模型
3. **预测准确率验证**: 验证全球联赛预测准确率
4. **OddsPortal 复工**: 冷却期结束后恢复 OddsPortal 数据采集

---

## 📞 联系方式

**技术负责人**: Data Engineering Expert
**文档版本**: V26.6 Final
**最后更新**: 2026-01-06 23:59

---

**附录: 常用命令速查**

```bash
# 查看当前失败记录数量
psql -h localhost -U football_user -d football_db -c "SELECT COUNT(*) FROM matches WHERE status = 'FAILED';"

# 查看某个联赛的比赛数量
psql -h localhost -U football_user -d football_db -c "SELECT COUNT(*) FROM matches WHERE league_id = 47;"

# 查看回填日志
tail -f logs/v26_6_backfill.log

# 停止采集（按 Ctrl+C）
# 程序会执行优雅关闭

# 查看哨兵状态
echo $COLLECTION_PAUSE_UNTIL
```

---

**🚀 点火日口号**: "收割机已入库，等待 9 号点火！"
