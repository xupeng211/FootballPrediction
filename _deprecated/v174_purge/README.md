# V174 目录规范化清场归档

> **归档日期**: 2026-03-01  
> **归档原因**: V174 模块化重构，清理旧版脚本和断链引用

---

## 归档清单

### legacy_scripts/ (旧版脚本)

| 文件 | 原版本 | 说明 |
|------|--------|------|
| `check_v51_data_health.py` | V51.0 | V51 旧版数据健康检查 |
| `import_v26_gold.py` | V150.5 | V26 一次性 TSV 导入 (已完成使命) |
| `v26_acceptance_audit.py` | V26.1 | V26 验收审计 (已被 V26.7 替代) |
| `prod_start_v172.sh` | V172 | V172 生产启动脚本 (已被 V174 替代) |

### orphan_scripts/ (孤儿脚本)

| 文件 | 说明 |
|------|------|
| `activate_historical_vault.py` | 用途不明，无引用 |
| `import_ucl_history.py` | UCL 历史导入，一次性脚本 |

### experimental/ (实验性脚本)

| 文件 | 原版本 | 说明 |
|------|--------|------|
| `harvest_all_l2.js` | V172 | 旧版全量收割控制器 |
| `incremental_factory.js` | V173 | 增量数据工厂 (已重构到 V174) |
| `time_alignment.test.js` | V122 | 时间对齐测试 |
| `v171_real_backfill_live.js` | V171 | 历史数据回填 |
| `v171_stealth_harvest.js` | V171 | Stealth 模式收割 |
| `v171_xg_harvest.js` | V171 | xG 数据收割 |

---

## 恢复方法

如需恢复某个脚本，请从本目录复制回原位置：

```bash
# 示例：恢复 v26_acceptance_audit.py
cp _deprecated/v174_purge/legacy_scripts/v26_acceptance_audit.py scripts/maintenance/
```

---

*归档执行者: Claude AI | V174 Engineering Team*

### src_scripts_legacy/ (src/scripts 旧版脚本)

| 文件 | 原版本 | 说明 |
|------|--------|------|
| `comprehensive_data_expansion.py` | V9.3 | 综合数据扩容器 |
| `comprehensive_data_expansion_fixed.py` | V9.3 | 综合数据扩容器修正版 |
| `data_migration_to_docker.py` | - | Docker 数据迁移 |
| `download_real_odds.py` | V11.0 | 真实赔率下载器 |
| `merge_multi_season_odds.py` | V9.2 | 多赛季赔率合并器 |
| `merge_real_odds.py` | V9.0 | 真实赔率合并器 |
| `multi_season_harvest.py` | V8.5 | 多赛季收割脚本 |
| `season_reharvest.py` | V7.0 | 赛季全量收割脚本 |

