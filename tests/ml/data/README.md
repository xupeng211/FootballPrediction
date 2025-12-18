# TDD DataLoader Tests - 数据加载模块测试驱动开发

## 🎯 TDD阶段状态

### ✅ **红阶段 (Red Phase) - 已完成**
- 测试用例已定义
- DataLoader接口规范已明确
- 预期的导入错误已验证 (`No module named 'src.ml.data'`)

### 📋 **下一步 (绿阶段 - Green Phase)**
创建 `src/ml/data/loader.py` 并实现DataLoader类以满足测试用例。

## 🧪 **测试覆盖范围**

### **核心功能测试 (`TestDataLoader`)**
1. **接口定义验证** - `test_load_raw_data_interface_definition`
   - 验证DataLoader类存在
   - 验证load_raw_data方法存在
   - 验证方法签名

2. **DataFrame返回验证** - `test_load_raw_data_returns_dataframe`
   - 返回pd.DataFrame对象
   - DataFrame非空验证
   - 行数匹配验证

3. **核心字段验证** - `test_dataframe_contains_core_fields`
   - 必需字段存在性检查
   - 字段命名规范验证
   - 数据类型基础验证

4. **日期处理验证** - `test_match_date_datetime_conversion`
   - match_date datetime类型转换
   - 时区信息保留
   - 字符串类型排除

5. **数据完整性验证** - `test_data_integrity_validation`
   - 得分字段非负验证
   - 期望进球有效性
   - 控球率范围检查

6. **数据过滤功能** - `test_load_filtered_data`
   - 日期范围过滤
   - 比赛状态过滤
   - 队伍过滤支持

7. **错误处理验证** - `test_error_handling`
   - 数据库连接错误
   - 查询超时处理
   - 数据格式异常

8. **配置支持验证** - `test_configuration_support`
   - 批量大小配置
   - 列选择配置
   - 记录数限制

### **性能测试 (`TestDataLoaderPerformance`)**
- **大数据集加载** - `test_large_dataset_loading`
  - 10万+记录处理
  - 加载时间优化
  - 内存使用控制

### **集成测试 (`TestDataLoaderIntegration`)**
- **真实数据库连接** - `test_real_database_connection`
  - 实际数据库环境测试
  - 标记为 `@pytest.mark.integration` 和 `@pytest.mark.slow`

## 🎯 **测试标记体系**

```python
@pytest.mark.ml           # ML特定测试
@pytest.mark.data         # 数据处理测试
@pytest.mark.unit         # 单元测试
@pytest.mark.integration  # 集成测试
@pytest.mark.slow         # 慢速测试
@pytest.mark.asyncio      # 异步测试
```

## 📊 **测试执行命令**

### 运行所有数据加载器测试
```bash
pytest tests/ml/data/test_loader.py -v
```

### 运行特定测试类
```bash
pytest tests/ml/data/test_loader.py::TestDataLoader -v
```

### 运行性能测试
```bash
pytest tests/ml/data/test_loader.py::TestDataLoaderPerformance -v -m slow
```

### 运行集成测试
```bash
pytest tests/ml/data/test_loader.py::TestDataLoaderIntegration -v -m integration
```

### 生成覆盖率报告
```bash
pytest tests/ml/data/ --cov=src/ml/data --cov-report=html --cov-report=term-missing
```

## 🔧 **测试配置**

### Fixtures
- `mock_db_session` - 模拟数据库会话
- `sample_match_data` - 示例比赛数据
- `sample_dataframe` - 示例DataFrame
- `mock_database_session` - 数据库会话mock
- `mock_sql_result` - SQL查询结果mock

### 异步支持
- 使用 `@pytest.mark.asyncio` 标记异步测试
- 配置 `asyncio_mode = "auto"`

## 📈 **预期结果**

### 红阶段 (当前)
- ✅ 所有测试因 `ImportError` 失败
- ✅ DataLoader类不存在
- ✅ TDD原则得到遵循

### 绿阶段 (下一步)
- 🎯 实现DataLoader类
- 🎯 所有测试通过
- 🎯 接口行为符合规范

### 重构阶段
- 🔧 代码优化
- 🔧 性能提升
- 🔧 可维护性改进

## 🚀 **开发指南**

1. **先运行测试**: `pytest tests/ml/data/test_loader.py -v`
2. **观察失败**: 确认红阶段状态
3. **实现代码**: 创建 `src/ml/data/loader.py`
4. **验证通过**: 所有测试变绿
5. **重构优化**: 改进代码质量

这就是TDD的核心循环：**红 -> 绿 -> 重构** 🎯