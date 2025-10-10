# 性能监控系统文档

## 概述

性能监控系统是足球预测系统的核心组件，提供全面的性能监控、分析和优化建议。系统采用模块化设计，支持实时监控、历史分析和智能告警。

## 架构设计

### 核心组件

1. **性能分析器 (PerformanceProfiler)**
   - 函数级性能分析
   - 内存使用跟踪
   - 数据库查询分析
   - 实时指标收集

2. **监控中间件 (PerformanceMonitoringMiddleware)**
   - HTTP请求性能跟踪
   - 响应时间监控
   - 并发请求统计
   - 错误率监控

3. **性能分析器 (PerformanceAnalyzer)**
   - 性能数据聚合
   - 趋势分析
   - 洞察生成
   - 优化建议

4. **集成模块 (PerformanceIntegration)**
   - 自动集成到FastAPI应用
   - 配置管理
   - 生命周期管理

## 功能特性

### 1. 实时性能监控

- API端点响应时间
- 数据库查询性能
- 缓存命中率
- 内存使用情况
- CPU使用率
- 并发请求数

### 2. 性能分析

- 慢查询识别
- 性能瓶颈定位
- 内存泄漏检测
- 资源使用趋势

### 3. 智能告警

- 自定义阈值配置
- 多级别告警（critical, high, medium, low）
- 告警聚合
- 自动恢复检测

### 4. 性能报告

- 实时性能仪表板
- 定期性能报告
- 性能趋势图表
- 优化建议列表

## 使用指南

### 快速开始

1. **集成到FastAPI应用**

```python
from src.performance.integration import setup_performance_monitoring

# 在应用启动时设置
app = FastAPI()
setup_performance_monitoring(app)
```

2. **启动性能分析**

```python
from src.performance.integration import start_performance_profiling

# 开始分析
start_performance_profiling()

# 执行需要分析的代码...

# 停止分析并获取结果
from src.performance.integration import stop_performance_profiling
results = stop_performance_profiling()
```

3. **生成性能报告**

```python
from src.performance.integration import generate_performance_report

report = generate_performance_report()
```

### API端点

性能监控系统提供了以下API端点：

- `GET /api/v1/performance/metrics` - 获取实时性能指标
- `POST /api/v1/performance/profiling/start` - 启动性能分析
- `POST /api/v1/performance/profiling/stop` - 停止性能分析
- `GET /api/v1/performance/report` - 生成性能报告
- `GET /api/v1/performance/insights` - 获取性能洞察
- `GET /api/v1/performance/score` - 获取性能评分
- `GET /api/v1/performance/trends` - 获取性能趋势

### 配置参数

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| PERFORMANCE_MONITORING_ENABLED | True | 是否启用性能监控 |
| PERFORMANCE_MONITORING_SAMPLE_RATE | 1.0 | 采样率（0-1） |
| PERFORMANCE_PROFILING_ENABLED | False | 是否启用性能分析 |
| SLOW_REQUEST_THRESHOLD | 1.0 | 慢请求阈值（秒） |
| CRITICAL_REQUEST_THRESHOLD | 5.0 | 严重请求阈值（秒） |
| SLOW_QUERY_THRESHOLD | 0.1 | 慢查询阈值（秒） |

## 性能指标

### API性能指标

- **响应时间**: 请求处理时间
- **吞吐量**: 每秒处理的请求数
- **错误率**: 错误请求占比
- **并发数**: 同时处理的请求数

### 数据库性能指标

- **查询时间**: SQL执行时间
- **查询频率**: 每秒查询数
- **连接池使用率**: 活跃连接占比
- **慢查询数**: 超过阈值的查询数

### 系统资源指标

- **CPU使用率**: CPU占用百分比
- **内存使用率**: 内存占用百分比
- **磁盘I/O**: 读写操作次数
- **网络I/O**: 网络传输量

## 最佳实践

### 1. 性能优化建议

- **数据库优化**
  - 使用索引加速查询
  - 实施查询缓存
  - 优化连接池配置
  - 定期分析慢查询

- **API优化**
  - 实施响应缓存
  - 使用异步处理
  - 批量处理请求
  - 压缩响应数据

- **内存优化**
  - 及时释放资源
  - 使用对象池
  - 监控内存泄漏
  - 优化数据结构

### 2. 监控策略

- **设置合理的阈值**
  - 根据业务需求调整阈值
  - 考虑系统负载变化
  - 定期评估和调整

- **告警配置**
  - 避免告警风暴
  - 设置告警级别
  - 配置告警通知渠道

- **数据分析**
  - 定期查看性能报告
  - 分析性能趋势
  - 制定优化计划

## 故障排除

### 常见问题

1. **性能监控数据缺失**
   - 检查配置是否正确
   - 确认中间件是否正确注册
   - 查看日志是否有错误

2. **性能分析影响业务**
   - 降低采样率
   - 限制分析持续时间
   - 在非高峰时段运行

3. **内存使用过高**
   - 检查是否有内存泄漏
   - 优化数据缓存策略
   - 增加内存限制

### 调试工具

- **日志查看**
  ```bash
  tail -f logs/performance.log
  ```

- **性能分析**
  ```python
  # 使用装饰器分析特定函数
  from src.performance.profiler import profile_function

  @profile_function
  def slow_function():
      # 函数实现
      pass
  ```

- **实时监控**
  ```bash
  # 使用curl获取实时指标
  curl http://localhost:8000/api/v1/performance/metrics
  ```

## 扩展开发

### 自定义指标

```python
from src.performance.profiler import get_profiler

profiler = get_profiler()
profiler.record_metric(
    name="custom_metric",
    value=100.0,
    unit="ms",
    tags={"component": "custom"}
)
```

### 自定义分析器

```python
from src.performance.analyzer import PerformanceAnalyzer

class CustomAnalyzer(PerformanceAnalyzer):
    def analyze_custom_metric(self, metrics):
        # 自定义分析逻辑
        insights = []
        # ...
        return insights
```

### 自定义中间件

```python
from src.performance.middleware import BaseHTTPMiddleware

class CustomPerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 自定义性能跟踪逻辑
        # ...
        return await call_next(request)
```

## 版本历史

- **v1.0.0** (2024-12)
  - 初始版本发布
  - 基础性能监控功能
  - API端点监控
  - 数据库查询监控

- **v1.1.0** (计划中)
  - 分布式追踪支持
  - 更多性能指标
  - 高级分析功能
  - 可视化仪表板

## 相关链接

- [FastAPI文档](https://fastapi.tiangolo.com/)
- [psutil文档](https://psutil.readthedocs.io/)
- [Pydantic文档](https://pydantic-docs.helpmanual.io/)

## 贡献指南

欢迎贡献代码和改进建议！请遵循以下步骤：

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

本项目采用MIT许可证。详见[LICENSE](../LICENSE)文件。
