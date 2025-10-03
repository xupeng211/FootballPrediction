# 📊 行长修复报告 (LINE_LENGTH_REPORT)

**修复时间**: 2025-09-30 12:34:41
**修复工具**: scripts/line_length_fix.py
**修复范围**: tests/unit
**行长限制**: 120 字符

## 📈 修复统计

### 总体统计
- **处理文件总数**: 286 个
- **已修复文件数**: 0 个
- **修复成功率**: 0.0%

### 详细统计
- **发现长行**: 29 行
- **拆分行数**: 0 行
- **自动修复**: 0 处
- **需要手动审查**: 29 处
- **处理错误**: 0 个

## 📋 已修复文件列表

### 自动修复的文件 (0 个)
无文件需要自动修复

## ⚠️ 需要手动审查的长行

以下长行需要手动处理:


### `tests/unit/test_analyze_coverage_precise.py`:342
- **长度**: 148 字符 (限制: 120)
- **内容**: `                <class name="test_module" ": "file...`

```python
    340:         <package name="src" ": "line-rate="0.75" branch-rate="0.65">\n    341:             <classes>\n>>> 342:                 <class name="test_module" ": "filename="src/test_module.py" line-rate="0.8" branch-rate="0.7" lines-covered="4" ": "lines-valid="5">\n    343:                     <methods>\n    344:                         <method name="test_function" ": "line-rate="1.0" branch-rate="1.0">
```


### `tests/unit/test_analyze_coverage_precise.py`:43
- **长度**: 135 字符 (限制: 120)
- **内容**: `        )  # shebang + module docstring + def + fu...`

```python
     41:         assert (\n     42:             result ==10\n>>>  43:         )  # shebang + module docstring + def + func docstring + x=1 + return + class + class docstring + def + method docstring + pass\n     44:     def test_count_lines_of_code_complex_file(self, tmp_path):\n     45:         """测试复杂文件结构"""
```


### `tests/unit/test_extract_coverage.py`:333
- **长度**: 122 字符 (限制: 120)
- **内容**: `                mock_path.side_effect = lambda p: ...`

```python
    331:             os.chdir(tmp_path)\n    332:             with patch('extract_coverage.Path') as mock_path:\n>>> 333:                 mock_path.side_effect = lambda p: src_dir if p =='/home/user/projects/FootballPrediction/src' else Path(p)\n    334:                 # KLp\n    335:                 loc1 = count_lines_of_code(str(test_file1))
```


### `tests/unit/test_data_lake_storage_batch_delta_001.py`:99
- **长度**: 141 字符 (限制: 120)
- **内容**: `        assert "bronze" in str(data_lake.tables[ta...`

```python
     97:         for table in expected_tables:\n     98:         assert table in data_lake.tables\n>>>  99:         assert "bronze" in str(data_lake.tables[table]) or "silver" in str(data_lake.tables[table]) or "gold" in str(data_lake.tables[table])\n    100:         @pytest.mark.asyncio\n    101:     async def test_save_historical_data_with_dataframe(self, data_lake, sample_dataframe):
```


### `tests/unit/test_anomaly_detector_batch_delta_004.py`:187
- **长度**: 151 字符 (限制: 120)
- **内容**: `    def test_statistical_detector_detect_distribut...`

```python
    185:         assert result.statistics["p_value"] ==0.8\n    186:         @patch('src.data.quality.anomaly_detector.stats.ks_2samp')\n>>> 187:     def test_statistical_detector_detect_distribution_shift_with_shift(self, mock_ks_2samp, statistical_detector, baseline_data, current_data_shifted):\n    188:         """测试分布偏移检测有偏移情况"""\n    189:         # Mock ks_2samp返回显著差异的结果
```


### `tests/unit/test_anomaly_detector_batch_delta_004.py`:173
- **长度**: 127 字符 (限制: 120)
- **内容**: `    def test_statistical_detector_detect_distribut...`

```python
    171:         assert result.statistics["outlier_rate"] ==0.0\n    172:         @patch('src.data.quality.anomaly_detector.stats.ks_2samp')\n>>> 173:     def test_statistical_detector_detect_distribution_shift_no_shift(self, mock_ks_2samp, statistical_detector, baseline_data):\n    174:         """测试分布偏移检测无偏移情况"""\n    175:         # Mock ks_2samp返回无显著差异的结果
```


### `tests/unit/api/test_features_comprehensive.py`:268
- **长度**: 129 字符 (限制: 120)
- **内容**: `    async def test_get_team_features_with_raw_data...`

```python
    266:             assert result["data"]["calculation_date"] ==custom_date.isoformat()\n    267:     @pytest.mark.asyncio\n>>> 268:     async def test_get_team_features_with_raw_data(self, mock_session, sample_team, mock_feature_store, mock_feature_calculator):\n    269:         """测试获取球队特征包含原始数据"""\n    270:         async def mock_execute(query):
```


### `tests/unit/api/test_features_comprehensive.py`:156
- **长度**: 131 字符 (限制: 120)
- **内容**: `    async def test_get_match_features_with_raw_dat...`

```python
    154:             assert result["data"]["features"]["home_goals_scored"] ==12\n    155:     @pytest.mark.asyncio\n>>> 156:     async def test_get_match_features_with_raw_data(self, mock_session, sample_match, mock_feature_store, mock_feature_calculator):\n    157:         """测试获取比赛特征包含原始数据"""\n    158:         async def mock_execute(query):
```


### `tests/unit/api/test_models_comprehensive.py`:371
- **长度**: 138 字符 (限制: 120)
- **内容**: `        async def test_get_model_performance_produ...`

```python
    369:                 assert performance["overall_accuracy"] ==0.8\n    370:         @pytest.mark.asyncio\n>>> 371:         async def test_get_model_performance_production_version(self, mock_session, mock_mlflow_client, sample_model_version, sample_run):\n    372:             """测试获取生产版本性能"""\n    373:             with patch("src.api.models.mlflow_client", mock_mlflow_client):
```


### `tests/unit/api/test_models_comprehensive.py`:324
- **长度**: 132 字符 (限制: 120)
- **内容**: `        async def test_get_model_performance_with_...`

```python
    322:         """测试获取模型详细性能接口"""\n    323:         @pytest.mark.asyncio\n>>> 324:         async def test_get_model_performance_with_version(self, mock_session, mock_mlflow_client, sample_model_version, sample_run):\n    325:             """测试指定版本获取模型性能"""\n    326:             with patch("src.api.models.mlflow_client", mock_mlflow_client):
```


### `tests/unit/api/test_models_comprehensive.py`:91
- **长度**: 134 字符 (限制: 120)
- **内容**: `        async def test_get_active_models_success(s...`

```python
     89:         """测试获取活跃模型接口"""\n     90:         @pytest.mark.asyncio\n>>>  91:         async def test_get_active_models_success(self, mock_mlflow_client, sample_registered_model, sample_model_version, sample_run):\n     92:             """测试成功获取活跃模型"""\n     93:             with patch("src.api.models.mlflow_client", mock_mlflow_client):
```


### `tests/unit/models/test_prediction_service_caching.py`:30
- **长度**: 122 字符 (限制: 120)
- **内容**: `    pytest tests/unit/models/test_prediction_servi...`

```python
     28: \n     29:     # 运行特定测试\n>>>  30:     pytest tests/unit/models/test_prediction_service_caching.py:TestPredictionServiceCaching:test_predict_match_caching -v\n     31:     ```\n     32: """
```


### `tests/unit/services/test_audit_service.py`:229
- **长度**: 126 字符 (限制: 120)
- **内容**: `        assert self.audit_service._determine_compl...`

```python
    227:         """测试金融数据合规分类"""\n    228:         assert self.audit_service._determine_compliance_category(AuditAction.CREATE, "financial_data", False) =="FINANCIAL"\n>>> 229:         assert self.audit_service._determine_compliance_category(AuditAction.UPDATE, "financial_records", False) =="FINANCIAL"\n    230:     def test_determine_compliance_category_general(self):\n    231:         """测试通用合规分类"""
```


### `tests/unit/services/test_audit_service.py`:228
- **长度**: 123 字符 (限制: 120)
- **内容**: `        assert self.audit_service._determine_compl...`

```python
    226:     def test_determine_compliance_category_financial(self):\n    227:         """测试金融数据合规分类"""\n>>> 228:         assert self.audit_service._determine_compliance_category(AuditAction.CREATE, "financial_data", False) =="FINANCIAL"\n    229:         assert self.audit_service._determine_compliance_category(AuditAction.UPDATE, "financial_records", False) =="FINANCIAL"\n    230:     def test_determine_compliance_category_general(self):
```


### `tests/unit/services/test_audit_service.py`:225
- **长度**: 127 字符 (限制: 120)
- **内容**: `        assert self.audit_service._determine_compl...`

```python
    223:         """测试数据保护合规分类"""\n    224:         assert self.audit_service._determine_compliance_category(AuditAction.BACKUP, "matches", False) =="DATA_PROTECTION"\n>>> 225:         assert self.audit_service._determine_compliance_category(AuditAction.RESTORE, "predictions", False) =="DATA_PROTECTION"\n    226:     def test_determine_compliance_category_financial(self):\n    227:         """测试金融数据合规分类"""
```


### `tests/unit/services/test_audit_service.py`:224
- **长度**: 122 字符 (限制: 120)
- **内容**: `        assert self.audit_service._determine_compl...`

```python
    222:     def test_determine_compliance_category_data_protection(self):\n    223:         """测试数据保护合规分类"""\n>>> 224:         assert self.audit_service._determine_compliance_category(AuditAction.BACKUP, "matches", False) =="DATA_PROTECTION"\n    225:         assert self.audit_service._determine_compliance_category(AuditAction.RESTORE, "predictions", False) =="DATA_PROTECTION"\n    226:     def test_determine_compliance_category_financial(self):
```


### `tests/unit/services/test_audit_service.py`:221
- **长度**: 125 字符 (限制: 120)
- **内容**: `        assert self.audit_service._determine_compl...`

```python
    219:         """测试访问控制合规分类"""\n    220:         assert self.audit_service._determine_compliance_category(AuditAction.GRANT, "permissions", False) =="ACCESS_CONTROL"\n>>> 221:         assert self.audit_service._determine_compliance_category(AuditAction.REVOKE, "permissions", False) =="ACCESS_CONTROL"\n    222:     def test_determine_compliance_category_data_protection(self):\n    223:         """测试数据保护合规分类"""
```


### `tests/unit/services/test_audit_service.py`:220
- **长度**: 124 字符 (限制: 120)
- **内容**: `        assert self.audit_service._determine_compl...`

```python
    218:     def test_determine_compliance_category_access_control(self):\n    219:         """测试访问控制合规分类"""\n>>> 220:         assert self.audit_service._determine_compliance_category(AuditAction.GRANT, "permissions", False) =="ACCESS_CONTROL"\n    221:         assert self.audit_service._determine_compliance_category(AuditAction.REVOKE, "permissions", False) =="ACCESS_CONTROL"\n    222:     def test_determine_compliance_category_data_protection(self):
```


### `tests/unit/services/test_data_processing_phase5321.py`:86
- **长度**: 169 字符 (限制: 120)
- **内容**: `sys.modules['feast.infra.offline_stores.contrib.po...`

```python
     84: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store'] = mock_feast.infra.offline_stores.contrib.postgres_offline_store\n     85: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres'] = mock_feast.infra.offline_stores.contrib.postgres_offline_store.postgres\n>>>  86: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source'] = mock_feast.infra.offline.stores.contrib.postgres_offline_store.postgres_source\n     87: sys.modules['feast.infra.online_stores'] = mock_feast.infra.online_stores\n     88: sys.modules['feast.infra.online_stores.redis'] = mock_feast.infra.online_stores.redis
```


### `tests/unit/services/test_data_processing_phase5321.py`:85
- **长度**: 155 字符 (限制: 120)
- **内容**: `sys.modules['feast.infra.offline_stores.contrib.po...`

```python
     83: sys.modules['feast.infra.offline_stores.contrib'] = mock_feast.infra.offline_stores.contrib\n     84: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store'] = mock_feast.infra.offline_stores.contrib.postgres_offline_store\n>>>  85: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres'] = mock_feast.infra.offline_stores.contrib.postgres_offline_store.postgres\n     86: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source'] = mock_feast.infra.offline.stores.contrib.postgres_offline_store.postgres_source\n     87: sys.modules['feast.infra.online_stores'] = mock_feast.infra.online_stores
```


### `tests/unit/services/test_data_processing_phase5321.py`:84
- **长度**: 137 字符 (限制: 120)
- **内容**: `sys.modules['feast.infra.offline_stores.contrib.po...`

```python
     82: sys.modules['feast.infra.offline_stores'] = mock_feast.infra.offline_stores\n     83: sys.modules['feast.infra.offline_stores.contrib'] = mock_feast.infra.offline_stores.contrib\n>>>  84: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store'] = mock_feast.infra.offline_stores.contrib.postgres_offline_store\n     85: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres'] = mock_feast.infra.offline_stores.contrib.postgres_offline_store.postgres\n     86: sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source'] = mock_feast.infra.offline.stores.contrib.postgres_offline_store.postgres_source
```


### `tests/unit/features/test_feature_calculator_phase53.py`:253
- **长度**: 121 字符 (限制: 120)
- **内容**: `        feature_types = ['strength_features', 'for...`

```python
    251:     assert len(all_features) > 0\n    252:         # 验证特征类型\n>>> 253:         feature_types = ['strength_features', 'form_features', 'h2h_features', 'position_features', 'advantage_features']\n    254:         for feature_type in feature_types:\n    255:     assert feature_type in all_features
```


### `tests/unit/features/test_feature_calculator_phase53.py`:246
- **长度**: 126 字符 (限制: 120)
- **内容**: `            patch.object(calculator, 'calculate_le...`

```python
    244:             patch.object(calculator, 'calculate_form_features', return_value = {'home_form_rating': 0.7, 'away_form_rating': 0.5}), \\n    245:             patch.object(calculator, 'calculate_head_to_head_features', return_value = {'h2h_advantage': 0.6}), \\n>>> 246:             patch.object(calculator, 'calculate_league_position_features', return_value = {'home_position_advantage': 0.8}), \\n    247:             patch.object(calculator, 'calculate_home_advantage_features', return_value = {'home_advantage': 0.7})\n    248:             all_features = await calculator.calculate_all_features(match_data)
```


### `tests/unit/features/test_feature_calculator_phase53.py`:244
- **长度**: 133 字符 (限制: 120)
- **内容**: `            patch.object(calculator, 'calculate_fo...`

```python
    242:         # Mock所有数据源\n    243:         with patch.object(calculator, 'calculate_team_strength_features', return_value = {'home_team_strength': 0.8, 'away_team_strength': 0.6}), \\n>>> 244:             patch.object(calculator, 'calculate_form_features', return_value = {'home_form_rating': 0.7, 'away_form_rating': 0.5}), \\n    245:             patch.object(calculator, 'calculate_head_to_head_features', return_value = {'h2h_advantage': 0.6}), \\n    246:             patch.object(calculator, 'calculate_league_position_features', return_value = {'home_position_advantage': 0.8}), \
```


### `tests/unit/features/test_feature_calculator_phase53.py`:243
- **长度**: 147 字符 (限制: 120)
- **内容**: `        with patch.object(calculator, 'calculate_t...`

```python
    241:         }\n    242:         # Mock所有数据源\n>>> 243:         with patch.object(calculator, 'calculate_team_strength_features', return_value = {'home_team_strength': 0.8, 'away_team_strength': 0.6}), \\n    244:             patch.object(calculator, 'calculate_form_features', return_value = {'home_form_rating': 0.7, 'away_form_rating': 0.5}), \\n    245:             patch.object(calculator, 'calculate_head_to_head_features', return_value = {'h2h_advantage': 0.6}), \
```


### `tests/unit/tasks/test_backup_tasks.py`:225
- **长度**: 128 字符 (限制: 120)
- **内容**: `        mock_result.stdout = "1048576 1631234567.0...`

```python
    223:         mock_result = Mock()\n    224:         mock_result.returncode = 0\n>>> 225:         mock_result.stdout = "1048576 1631234567.0 _backup/full/backup.sql.gz\n2097152 1631234568.0 /backup/full/backup2.sql.gz"\n    226:         mock_subprocess.return_value = mock_result\n    227:         result = get_backup_status.apply().get()
```


### `tests/unit/tasks/test_task_scheduler.py`:756
- **长度**: 123 字符 (限制: 120)
- **内容**: `        mock_db_manager.get_async_session.return_v...`

```python
    754:         """测试数据质量检查任务"""\n    755:         # 模拟数据库查询结果\n>>> 756:         mock_db_manager.get_async_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = (\n    757:         5\n    758:         )
```


### `tests/unit/data/test_odds_collector.py`:169
- **长度**: 134 字符 (限制: 120)
- **内容**: `            patch.object(collector, '_clean_odds_d...`

```python
    167:             patch.object(collector, '_save_to_bronze_layer') as mock_save, \\n    168:             patch.object(collector, '_has_odds_changed', side_effect=[True, True, True]), \\n>>> 169:             patch.object(collector, '_clean_odds_data', side_effect = [mock_odds_data_1[0], mock_odds_data_2[0], mock_odds_data_3[0]])\n    170:             # 模拟部分成功\n    171:             mock_collect.side_effect = [
```


### `tests/unit/scheduler/test_recovery_handler_batch_omega_004.py`:237
- **长度**: 134 字符 (限制: 120)
- **内容**: `        mock_retry.assert_called_once_with(mock_ta...`

```python
    235:             result = recovery_handler._execute_recovery_strategy(mock_task, sample_failure)\n    236:     assert result is True\n>>> 237:         mock_retry.assert_called_once_with(mock_task, sample_failure, recovery_handler.recovery_configs[FailureType.CONNECTION_ERROR])\n    238:     def test_execute_recovery_strategy_unknown_strategy(self, recovery_handler, mock_task, sample_failure):\n    239:         """测试执行未知恢复策略"""
```



## 🎯 修复效果

- **行长合规**: 自动修复的长行现在符合 120 字符限制
- **代码可读性**: 合理的换行提高了代码可读性
- **维护性**: 遵循 PEP 8 行长规范

## 🔧 使用方法

```bash
# 修复整个项目 (默认 120 字符限制)
python scripts/line_length_fix.py

# 修复特定目录
python scripts/line_length_fix.py src/services

# 自定义行长限制
python scripts/line_length_fix.py --max-length 100

# 查看帮助
python scripts/line_length_fix.py --help
```

## ⚡ 修复策略

1. **字符串拼接**: 在 + 号处拆分长字符串拼接
2. **函数调用**: 将多参数函数调用换行排列
3. **集合字面量**: 数组、字典按元素换行
4. **逻辑表达式**: 在 and/or 处分行复杂条件
5. **Import 语句**: 多模块 import 按行分开
6. **通用拆分**: 对其他情况在合适位置换行

---

**报告生成时间**: 2025-09-30 12:34:41
**工具版本**: 1.0
