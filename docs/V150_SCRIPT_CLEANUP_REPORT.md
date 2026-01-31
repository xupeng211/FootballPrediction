# V150 Scripts Cleanup Report
## scripts/ops/ 临时脚本清理审计报告

**生成时间**: 2026-01-11
**审计范围**: scripts/ops/ 目录下的所有 Python 脚本
**审计目的**: 识别临时/调试脚本，保留长期运维脚本

---

## 📊 统计概览

| 类别 | 数量 | 说明 |
|------|------|------|
| **总脚本数** | 146 | 所有 .py 文件 |
| **保留** | 8 | 长期运维脚本 |
| **归档** | 135 | V150 系列探索性脚本 |
| **删除** | 3 | 备份/重复文件 |

---

## ✅ 保留脚本 (长期运维)

以下脚本应保留在 `scripts/ops/` 目录中，用于日常运维：

| 脚本名称 | 用途 | 版本 |
|----------|------|------|
| `check_db_consistency.py` | V26.7 数据库一致性检查 | V26.7 |
| `drop_dev_database.py` | 开发数据库清理工具 | - |
| `final_production_smoke_test.py` | 生产冒烟测试 | - |
| `lock_feature_manifest.py` | V26.7 特征清单锁定 | V26.7 |
| `v150_35_incremental_harvest.py` | V150.53 生产收割机（当前版本） | V150.53 |
| `v150_52_matches_mapping_check.py` | URL 健康检查（准入红线验证） | V150.52 |
| `v26_7_ultimate_harvester.py` | V26.7 终极收割机 | V26.7 |
| `v26_5_quality_dashboard.py` | V26.5 质量仪表盘 | V26.5 |

---

## 📦 归档脚本 (V150 系列探索性脚本)

以下脚本应移至 `scripts/archive/v150_experiments/` 目录：

### V150.0-V150.9 早期探索
- v150_1_run_refinement.py
- v150_2_*.py (5个脚本 - pilot 测试和验证)
- v150_3_*.py (2个脚本 - 稳定性测试)
- v150_4_*.py (6个脚本 - TDD 验证和深度分析)
- v150_5_*.py (2个脚本 - 分页相关)
- v150_6_*.py (2个脚本 - 数据同步和分页)
- v150_7_*.py (4个脚本 - L3 提取器演进)
- v150_8_*.py (2个脚本 - URL 导航)
- v150_9_hash_scout.py

### V150.10-V150.19 批量收割阶段
- v150_10_*.py (4个脚本 - campaign 和 L3 验证)
- v150_12_*.py (3个脚本 - browser search 和 hash rescue)
- v150_13_*.py (9个脚本 - archive 导航和调试)
- v150_14_mapping_audit.py
- v150_15_*.py (5个脚本 - 页面分析和调试)
- v150_16_phantom_penetrator.py
- v150_17_deep_session.py
- v150_18_*.py (3个脚本 - 资产定价和代理测试)
- v150_19_mapping_calibration.py

### V150.20-V150.29 优化阶段
- v150_20_*.py (5个脚本 - bypass 和 TDD 验证)
- v150_21_precision_loader.py
- v150_22_hardcore_loader.py
- v150_23_proxy_pool_loader.py
- v150_25_dryrun_test.py
- v150_26_ip_scanner.py
- v150_27_*.py (9个脚本 - 提取和代理测试)
- v150_28_id_harvester.py
- v150_29_stealth_harvest.py

### V150.30-V150.39 最终优化
- v150_30_*.py (4个脚本 - debug 和简化版本)
- v150_31_*.py (3个脚本 - 滚动和调试)
- v150_32_based_on_29.py
- v150_33_usage_example.py
- v150_34_*.py (2个脚本 - 团队名修复和冒烟测试)
- v150_36_final_report.py
- v150_37_old_id_recovery.py
- v150_38_url_extractor.py
- v150_3_stability_test_50.py

### V150.40-V150.49 别名引擎阶段
- v150_40_master_id_harvester.py
- v150_41_fuzzy_aligner.py ⭐ 已提取到 `src/utils/team_alias.py`
- v150_42_approve_medium.py
- v150_43_*.py (3个脚本 - debug 和 multi-season)
- v150_44_*.py (3个脚本 - debug 和 final mapper) ⭐ 已提取到 `src/utils/team_alias.py`
- v150_45_final_mapper_pro.py
- v150_46_*.py (6个脚本 - debug 和 parser)
- v150_47_detail_mapper.py
- v150_48_*.py (2个脚本 - diagnostic)
- v150_49_final_crusher.py

### V150.50+ 收割阶段
- v150_50_url_health_check.py ⭐ 已完成准入红线验证
- v150_51_*.py (2个脚本 - URL patcher 和验证)
- v150_5_pagination_breaker.py
- v150_5_pagination_detector.py

### 综合脚本
- v150_alignment_pipeline.py
- v150_five_season_harvest.py
- v150_historical_indexer.py
- v150_historical_url_finder.py
- v150_mock_indexer.py
- v150_real_fire_drill.py
- v150_second_fire_drill.py
- v150_survival_drill*.py (2个脚本)
- v150_url_pattern_finder.py

---

## 🗑️ 删除脚本 (备份/重复)

以下脚本应直接删除（备份文件或重复文件）：

| 脚本名称 | 原因 |
|----------|------|
| `v150_13_archive_navigator.py.backup_20260108_182721` | 备份文件 |
| 其他 `.backup_*` 文件 | 备份文件 |

---

## 📋 执行计划

### 步骤 1: 创建归档目录
```bash
mkdir -p scripts/archive/v150_experiments
```

### 步骤 2: 移动归档脚本
```bash
# 移动所有 V150 系列脚本（除保留的）
mv scripts/ops/v150_1_run_refinement.py scripts/archive/v150_experiments/
mv scripts/ops/v150_2_*.py scripts/archive/v150_experiments/
# ... (继续处理其他 V150 脚本)
```

### 步骤 3: 删除备份文件
```bash
rm scripts/ops/*.backup_*
```

### 步骤 4: 生成清理后的目录清单
```bash
ls scripts/ops/*.py > scripts/ops/CLEANUP_MANIFEST.txt
```

---

## 🎯 清理后的 scripts/ops/ 结构

```
scripts/ops/
├── check_db_consistency.py          # V26.7 数据库一致性检查
├── drop_dev_database.py              # 开发数据库清理
├── final_production_smoke_test.py   # 生产冒烟测试
├── lock_feature_manifest.py          # V26.7 特征清单锁定
├── v150_35_incremental_harvest.py    # V150.53 生产收割机
├── v150_52_matches_mapping_check.py  # URL 健康检查
├── v26_5_quality_dashboard.py        # V26.5 质量仪表盘
├── v26_7_ultimate_harvester.py       # V26.7 终极收割机
└── __pycache__/                      # Python 缓存目录

scripts/archive/v150_experiments/     # V150 系列归档（135个脚本）
└── ...
```

---

## ✅ 验收标准

1. **保留脚本数量**: 8 个
2. **归档脚本数量**: 135 个
3. **删除脚本数量**: 3 个
4. **scripts/ops/ 目录整洁度**: ✅ 仅保留长期运维脚本
5. **Git 提交准备**: ✅ 可提交清理后的变更

---

## 📝 附录: 脚本分类代码

- **PRESERVE**: 保留在 scripts/ops/
- **ARCHIVE**: 移至 scripts/archive/v150_experiments/
- **DELETE**: 直接删除
- **REVIEW**: 需要进一步审查

---

**审计人员**: Claude Code (V150.49 Principal Architect)
**批准日期**: 2026-01-11
