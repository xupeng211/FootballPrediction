# Quick Start Guide - [Genesis.ProductionFreeze]
# =============================================

本文档提供如何使用 `production_fire.py` 启动数据采集任务的快速指南。

## 📋 前置要求

### 环境检查

```bash
# 检查 Python 版本 (需要 3.11+)
python --version

# 检查 Docker 是否运行
docker ps

# 启动核心数据库服务
make up
```

### 数据库验证

```bash
# 确保数据库已启动并包含必要表
docker exec football_prediction_db psql -U football_user -d football_db -c "\dt"
```

预期输出应包含:
- `matches` (L1 基础数据表)
- `metrics_multi_source_data` (L2/L3 数据表)

---

## 🚀 快速开始

### 单场比赛数据采集 (推荐)

```bash
# 基本用法 - 采集 L1 + L2 数据
python production_fire.py --match-id 404148650 \
    --league "Premier League" \
    --season "2024-2025" \
    --home-team "Arsenal" \
    --away-team "Chelsea" \
    --skip-l3
```

**说明**:
- `--match-id`: FotMob 比赛 ID
- `--league`: 联赛名称
- `--season`: 赛季格式 (如 2024-2025)
- `--home-team` / `--away-team`: 球队名称
- `--skip-l3`: 暂时跳过 L3 (OddsPortal) 采集

### 完整数据采集 (L1 + L2 + L3)

```bash
python production_fire.py --match-id 404148650 \
    --league "Premier League" \
    --season "2024-2025" \
    --home-team "Arsenal" \
    --away-team "Chelsea"
```

### 批量采集模式

```bash
# 创建比赛 ID 列表文件
cat > matches.txt << EOF
404148650
404148651
404148652
EOF

# 批量采集
python production_fire.py --batch matches.txt --concurrency 3
```

### 采集最近 N 场比赛

```bash
# 从数据库获取最近 10 场比赛并采集
python production_fire.py --recent 10
```

---

## 📊 执行流程说明

### 数据流

```
[NetworkShield 初始化]
    ↓
[分配 IP 端口] → 22/22 节点可用
    ↓
[L1: 基础数据] → 插入 matches 表
    ↓
[L2: FotMob API] → 采集评分/射门数据
    ↓
[L3: OddsPortal] → 采集赔率数据 (可选)
    ↓
[Golden Merger 融合] → 统一数据格式
```

### 日志输出示例

```
2026-02-03 19:20:09 | INFO | [NetworkShield] Initialized: 22/22 nodes available
2026-02-03 19:20:09 | INFO | [L1] Starting basic match data collection: 404148650
2026-02-03 19:20:09 | INFO | [L1] Complete: 404148650 (1 rows)
2026-02-03 19:20:09 | INFO | [L2] Starting FotMob data collection: 404148650
2026-02-03 19:20:12 | INFO | [NetworkShield] Assigned Clean IP (Port 7910)
2026-02-03 19:20:15 | INFO | [L2] Complete: 404148650
2026-02-03 19:20:15 | INFO | [SUCCESS] Golden Match secured in database
```

---

## 🔧 高级选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--match-id` | 单场比赛 ID | 必需 |
| `--league` | 联赛名称 | Auto-detect |
| `--season` | 赛季 | 2024-2025 |
| `--home-team` | 主队名称 | Unknown |
| `--away-team` | 客队名称 | Unknown |
| `--force` | 强制重新采集 | False |
| `--skip-l2` | 跳过 L2 采集 | False |
| `--skip-l3` | 跳过 L3 采集 | False |
| `--concurrency` | 批量并发数 | 3 |
| `--dry-run` | 预览模式 | False |

### 强制重新采集

```bash
python production_fire.py --match-id 404148650 --force
```

### 跳过 L2/L3 层

```bash
# 只采集 L1 基础数据
python production_fire.py --match-id 404148650 --skip-l2 --skip-l3

# 只采集 L1 + L2 (不采集 L3 赔率)
python production_fire.py --match-id 404148650 --skip-l3
```

---

## 🐛 故障排除

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `database "football_db" does not exist` | 数据库未初始化 | `make up` |
| `No available proxies from NetworkShield` | 所有代理失效 | 检查 `config/active_proxies.json` |
| `404 Client Error: Not Found` | 无效的 match_id | 使用真实的 FotMob match_id |
| `relation "metrics_multi_source_data" does not exist` | 表未创建 | 运行 SQL 迁移脚本 |

### 验证数据

```bash
# 检查 L1 数据
docker exec football_prediction_db psql -U football_user -d football_db -c \
    "SELECT match_id, home_team, away_team, league_name FROM matches ORDER BY match_date DESC LIMIT 5;"

# 检查 L2 数据
docker exec football_prediction_db psql -U football_user -d football_db -c \
    "SELECT match_id, source_name, final_h FROM metrics_multi_source_data ORDER BY updated_at DESC LIMIT 5;"
```

---

## 📈 性能基准

| 指标 | 基准值 |
|------|--------|
| **L1 采集延迟** | ~50ms |
| **L2 采集延迟** | ~2-3s (含代理分配) |
| **L3 采集延迟** | ~15-20s (含浏览器启动) |
| **网络可用性** | 22/22 节点 |
| **成功率** | >95% |

---

## 🔗 相关文档

- **完整架构**: [CLAUDE.md](../CLAUDE.md)
- **技术债务**: [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)
- **清理审计**: [docs/AUDIT_GENESIS_CLEAN_SWEEP.md](AUDIT_GENESIS_CLEAN_SWEEP.md)

---

**最后更新**: 2026-02-03
**版本**: V1.0.0
**状态**: Production Ready ✅
