# 断言质量提升指南

## 概述

本指南提供测试断言质量改进的最佳实践，确保测试具有更高的可读性、可维护性和调试能力。

## 基本原则

### 1. 描述性断言
**❌ 差的实践:**
```python
assert result == True
assert len(data) > 0
```

**✅ 好的实践:**
```python
assert result is True, f"Expected prediction to be successful, got {result}"
assert len(data) > 0, f"Expected non-empty data list, got {len(data)} items"
```

### 2. 使用专门的断言方法
**❌ 差的实践:**
```python
assert a == b
assert a in b
assert isinstance(a, type)
```

**✅ 好的实践:**
```python
# 使用pytest提供的专门断言
assert a == b  # 对于简单相等比较仍然可以
assert a in b  # 对于成员检查仍然可以
assert isinstance(a, type)  # 对于类型检查仍然可以

# 更复杂的断言使用自定义消息
assert actual_value == expected_value, f"Expected {expected_value}, got {actual_value}"
```

### 3. 浮点数比较
**❌ 差的实践:**
```python
assert result == 0.3333333333
```

**✅ 好的实践:**
```python
import math
assert math.isclose(result, 1/3, rel_tol=1e-9)
assert abs(result - expected) < tolerance, f"Value {result} not close to {expected}"
```

### 4. 集合比较
**❌ 差的实践:**
```python
assert set(a) == set(b)
```

**✅ 好的实践:**
```python
assert set(a) == set(b), f"Sets differ. Missing: {set(b) - set(a)}, Extra: {set(a) - set(b)}"
```

## 数据验证断言

### API响应验证
```python
def test_api_response_validation(response):
    # 基础响应检查
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"

    # 响应数据存在性检查
    assert "data" in response.json(), "Response missing 'data' field"

    data = response.json()["data"]

    # 数据结构验证
    required_fields = ["match_id", "predicted_outcome", "confidence"]
    for field in required_fields:
        assert field in data, f"Response missing required field: {field}"

    # 数据类型验证
    assert isinstance(data["match_id"], int), f"match_id should be int, got {type(data['match_id'])}"
    assert isinstance(data["confidence"], float), f"confidence should be float, got {type(data['confidence'])}"
    assert 0 <= data["confidence"] <= 1, f"confidence should be between 0 and 1, got {data['confidence']}"
```

### 数据库记录验证
```python
def test_database_record_validation(record):
    # 记录存在性
    assert record is not None, "Database record should not be None"

    # 必需字段检查
    required_fields = ["id", "created_at", "updated_at"]
    for field in required_fields:
        assert hasattr(record, field), f"Record missing field: {field}"

    # 时间戳验证
    assert record.created_at <= record.updated_at, "created_at should be <= updated_at"

    # 关联数据验证
    if hasattr(record, "related_records"):
        assert len(record.related_records) >= 0, "Related records should not be negative"
```

## 错误处理断言

### 异常验证
```python
def test_error_handling():
    # 预期异常
    with pytest.raises(ValueError, match="Invalid input data"):
        process_invalid_data()

    # 异常属性验证
    with pytest.raises(ValidationError) as exc_info:
        validate_data(invalid_data)

    assert exc_info.value.errors == ["Missing required field: name"]
    assert exc_info.value.status_code == 400
```

### 超时验证
```python
def test_timeout_handling():
    start_time = time.time()

    # 执行可能超时的操作
    result = perform_operation_with_timeout()

    elapsed_time = time.time() - start_time
    assert elapsed_time < max_timeout, f"Operation timed out after {elapsed_time:.2f}s"
```

## 性能断言

### 响应时间验证
```python
def test_response_time_performance():
    start_time = time.time()
    result = perform_operation()
    response_time = (time.time() - start_time) * 1000  # 转换为毫秒

    # 性能断言
    assert response_time < 100, f"Response time {response_time:.2f}ms exceeds 100ms limit"

    # 多次测试的平均性能
    times = []
    for _ in range(10):
        start = time.time()
        perform_operation()
        times.append((time.time() - start) * 1000)

    avg_time = sum(times) / len(times)
    max_time = max(times)

    assert avg_time < 50, f"Average response time {avg_time:.2f}ms too high"
    assert max_time < 150, f"Max response time {max_time:.2f}ms too high"
```

### 内存使用验证
```python
def test_memory_usage():
    import psutil
    process = psutil.Process()

    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # 执行内存密集型操作
    result = perform_memory_intensive_operation()

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    assert memory_increase < max_memory_increase, \
        f"Memory increased by {memory_increase:.1f}MB, limit is {max_memory_increase}MB"
```

## 数据一致性断言

### 概率分布验证
```python
def test_probability_distribution(probabilities):
    # 概率总和检查
    total_prob = sum(probabilities.values())
    assert abs(total_prob - 1.0) < 1e-6, \
        f"Probabilities sum to {total_prob}, expected 1.0"

    # 概率范围检查
    for outcome, prob in probabilities.items():
        assert 0 <= prob <= 1, f"Probability for {outcome} is {prob}, outside [0,1] range"

    # 概率分布合理性检查（可选）
    assert all(prob > 0 for prob in probabilities.values()), \
        "All probabilities should be positive"
```

### 时间序列数据验证
```python
def test_time_series_data(time_series):
    # 数据排序验证
    timestamps = [point["timestamp"] for point in time_series]
    assert timestamps == sorted(timestamps), "Time series data should be chronologically ordered"

    # 时间间隔验证
    for i in range(1, len(time_series)):
        interval = time_series[i]["timestamp"] - time_series[i-1]["timestamp"]
        assert interval > 0, f"Time interval should be positive, got {interval}"

    # 数据连续性验证
    expected_intervals = [point["expected_interval"] for point in time_series[1:]]
    actual_intervals = [time_series[i]["timestamp"] - time_series[i-1]["timestamp"]
                       for i in range(1, len(time_series))]

    for expected, actual in zip(expected_intervals, actual_intervals):
        assert abs(expected - actual) < tolerance, \
            f"Expected interval {expected}, got {actual}"
```

## Mock对象验证

### Mock调用验证
```python
def test_mock_interaction(mock_service):
    # 操作执行
    result = perform_operation_with_mock(mock_service)

    # Mock调用验证
    mock_service.method.assert_called_once()
    mock_service.method.assert_called_with(expected_args)

    # 调用次数验证
    assert mock_service.method.call_count == expected_count, \
        f"Expected {expected_count} calls, got {mock_service.method.call_count}"

    # 调用参数验证
    call_args = mock_service.method.call_args[0] if mock_service.method.call_args else []
    assert call_args == expected_args, f"Called with {call_args}, expected {expected_args}"
```

## 边界条件断言

### 数值边界验证
```python
def test_boundary_conditions():
    # 测试边界值
    boundary_values = [0, 1, -1, max_value, min_value]

    for value in boundary_values:
        result = process_boundary_value(value)
        assert validate_boundary_result(result, value), \
            f"Boundary test failed for value {value}, result {result}"

    # 测试溢出条件
    with pytest.raises(OverflowError):
        process_extremely_large_value(large_value)
```

### 空值和None处理
```python
def test_none_handling():
    # None输入处理
    result = process_none_input(None)
    assert result is not None, "Result should not be None for None input"
    assert result == expected_default_value, f"Expected default value {expected_default_value}"

    # 空集合处理
    empty_results = process_empty_collection([])
    assert isinstance(empty_results, list), "Empty collection should return list"
    assert len(empty_results) == 0, "Empty collection should return empty list"
```

## 自定义断言函数

### 创建可重用的断言函数
```python
def assert_valid_prediction_response(response_data):
    """验证预测响应数据的有效性"""
    # 基础结构检查
    assert isinstance(response_data, dict), "Response data should be a dictionary"

    # 必需字段
    required_fields = ["match_id", "predicted_outcome", "probabilities", "confidence"]
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"

    # 数据类型和范围
    assert isinstance(response_data["match_id"], int), "match_id should be integer"
    assert response_data["predicted_outcome"] in ["home_win", "draw", "away_win"], \
        f"Invalid outcome: {response_data['predicted_outcome']}"

    # 概率验证
    probabilities = response_data["probabilities"]
    assert_probabilities_valid(probabilities)

    # 置信度验证
    confidence = response_data["confidence"]
    assert 0 <= confidence <= 1, f"Confidence {confidence} outside valid range"

def assert_probabilities_valid(probabilities):
    """验证概率分布的有效性"""
    assert isinstance(probabilities, dict), "Probabilities should be a dictionary"

    # 检查必需的结果类型
    required_outcomes = ["home_win", "draw", "away_win"]
    for outcome in required_outcomes:
        assert outcome in probabilities, f"Missing probability for {outcome}"

    # 验证概率总和
    total_prob = sum(probabilities.values())
    assert abs(total_prob - 1.0) < 1e-6, f"Probabilities sum to {total_prob}, expected 1.0"

    # 验证单个概率
    for outcome, prob in probabilities.items():
        assert 0 <= prob <= 1, f"Probability for {outcome} is {prob}, outside [0,1] range"
```

## 调试友好的断言

### 提供详细的错误信息
```python
def test_with_detailed_assertions():
    # 提供上下文信息的断言
    expected = {"status": "success", "data": {"value": 42}}
    actual = get_api_response()

    # 使用详细的错误消息
    assert actual == expected, \
        f"API response mismatch.\nExpected: {expected}\nActual: {actual}\nDifference: {set(expected.items()) ^ set(actual.items())}"

    # 对于复杂对象，提供字段级别的比较
    for key in expected:
        assert key in actual, f"Missing key in response: {key}"
        assert actual[key] == expected[key], \
            f"Value mismatch for key '{key}'. Expected: {expected[key]}, Got: {actual[key]}"
```

## 使用示例

### 完整的测试示例
```python
def test_prediction_api_endpoint(client, valid_match_data):
    """测试预测API端点的完整功能"""
    # 发送请求
    response = client.post("/api/predict", json=valid_match_data)

    # 响应状态验证
    assert response.status_code == 200, \
        f"Expected status 200, got {response.status_code}. Response: {response.text}"

    # 响应数据解析
    try:
        data = response.json()
    except ValueError as e:
        assert False, f"Invalid JSON response: {e}"

    # 完整响应验证
    assert_valid_prediction_response(data)

    # 额外的业务逻辑验证
    assert data["match_id"] == valid_match_data["match_id"], \
        f"Match ID mismatch. Expected: {valid_match_data['match_id']}, Got: {data['match_id']}"

    # 性能验证（如果需要）
    assert "processing_time" in data["metadata"], "Missing processing time in metadata"
    assert data["metadata"]["processing_time"] < 1000, \
        f"Processing time {data['metadata']['processing_time']}ms too high"
```

这些断言质量改进原则将帮助我们创建更可靠、更易维护的测试套件。