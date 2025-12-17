# FootballPrediction v2.0 系统集成验收工具

## 概述

这是一套完整的系统集成验收与审计工具，用于验证 FootballPrediction v2.0 系统的所有核心功能是否正常工作。

## 验收范围

该工具验证以下核心链路：

### 1. 核心预测链路
- ✅ API → Redis (Cache Miss) → Celery (Async) → ML Model → Response
- ✅ 单次预测功能及缓存机制
- ✅ 异步批量预测功能

### 2. MLOps 链路
- ✅ Admin API (Trigger Retrain) → Worker (Train) → Model Registry (Update) → Hot Swap
- ✅ 模型状态查询
- ✅ 重训练任务触发
- ✅ 模型版本切换

### 3. 高并发链路
- ✅ 批量预测接口排队机制
- ✅ 并发任务处理
- ✅ 任务状态轮询

### 4. 监控链路
- ✅ Prometheus 指标暴露
- ✅ 指标数据收集
- ✅ Grafana 面板数据验证

### 5. 容错链路
- ✅ Redis 故障降级
- ✅ 数据库连接失败处理
- ✅ 模型加载失败 fallback

## 快速开始

### 方法一：使用便捷脚本（推荐）

```bash
# 1. 安装依赖
./scripts/audit/run_audit.sh --install

# 2. 运行验收测试
./scripts/audit/run_audit.sh --verbose --output audit_report.json
```

### 方法二：直接运行Python脚本

```bash
# 1. 安装依赖
pip install -r scripts/audit/requirements.txt

# 2. 运行验收测试
python scripts/audit/system_health_check.py --verbose --output-json --output-file audit_report.json
```

## 命令行选项

### system_health_check.py 选项

```bash
python scripts/audit/system_health_check.py [选项]

选项:
  --verbose, -v          详细输出模式，显示每个检查的详细信息
  --output-json, -j      输出JSON格式的详细报告
  --output-file FILE     将报告保存到指定文件
  --help, -h            显示帮助信息
```

### 使用示例

```bash
# 基础验收
python scripts/audit/system_health_check.py

# 详细模式验收
python scripts/audit/system_health_check.py --verbose

# 输出JSON报告
python scripts/audit/system_health_check.py --output-json

# 保存报告到文件
python scripts/audit/system_health_check.py --verbose --output-json --output-file audit_20251217.json
```

## 前置条件

### 系统要求

- Python 3.8+
- pip
- 运行中的系统服务：
  - API 服务 (localhost:8000)
  - Redis (localhost:6379)
  - PostgreSQL (localhost:5432)
  - Prometheus (localhost:9090)

### 依赖项

主要依赖项包括：
- `requests` - HTTP客户端
- `redis` - Redis客户端
- `colorama` - 彩色终端输出
- `psutil` - 系统监控

## 验收流程

验收脚本按以下顺序执行检查：

1. **基础健康检查** - 验证API服务、数据库、Redis状态
2. **Redis连接检查** - 验证Redis缓存服务连接
3. **同步预测检查** - 测试单次预测功能和缓存机制
4. **异步批量预测检查** - 测试批量预测功能
5. **MLOps功能检查** - 测试模型管理和重训练功能
6. **Prometheus指标检查** - 验证监控指标暴露

每个检查都会：
- 显示检查状态（✓ PASS, ✗ FAIL, - SKIP）
- 提供详细的成功/失败信息
- 记录检查耗时

## 输出结果

### 终端输出

```
FootballPrediction v2.0 系统集成验收与审计
============================================================

✓ [PASS] 基础健康检查
    所有组件正常运行 (响应时间: 45ms)
    耗时: 120ms

✓ [PASS] Redis连接检查
    Redis连接正常
    耗时: 15ms

✓ [PASS] 同步预测检查
    同步预测功能正常，缓存行为: 正常 (第一次Miss，第二次Hit)
    耗时: 850ms

...

============================================================
验收结果汇总
============================================================
总检查项: 6
通过: 6
失败: 0
跳过: 0
总耗时: 15.23秒

✓ 整体验收状态: PASS
```

### JSON报告格式

```json
{
  "audit_info": {
    "timestamp": "2025-12-17T10:30:00.000Z",
    "total_duration_seconds": 15.23,
    "overall_status": "PASS"
  },
  "summary": {
    "total_checks": 6,
    "passed": 6,
    "failed": 0,
    "skipped": 0
  },
  "checks": [
    {
      "name": "基础健康检查",
      "description": "验证API服务、数据库、Redis等基础组件是否正常运行",
      "status": "PASS",
      "message": "所有组件正常运行 (响应时间: 45ms)",
      "details": {
        "components": ["database", "redis", "filesystem"]
      },
      "duration_ms": 120.0
    }
    // ... 更多检查结果
  ]
}
```

## 故障排除

### 常见问题

1. **连接被拒绝**
   ```
   ✗ [FAIL] 基础健康检查
       健康检查失败，状态码: 503
   ```
   **解决方案**：确保API服务正在运行：
   ```bash
   docker-compose ps
   docker-compose up -d
   ```

2. **Redis连接失败**
   ```
   ✗ [FAIL] Redis连接检查
       无法连接到Redis服务
   ```
   **解决方案**：检查Redis服务状态：
   ```bash
   redis-cli ping
   docker-compose logs redis
   ```

3. **权限认证失败**
   ```
   ✗ [FAIL] MLOps功能检查
       获取模型状态失败，状态码: 401
   ```
   **解决方案**：设置管理员token或跳过需要认证的检查。

4. **依赖项缺失**
   ```
   ModuleNotFoundError: No module named 'colorama'
   ```
   **解决方案**：安装依赖项：
   ```bash
   ./scripts/audit/run_audit.sh --install
   ```

### 调试模式

使用 `--verbose` 选项获取详细的调试信息：

```bash
python scripts/audit/system_health_check.py --verbose
```

这会显示：
- 详细的HTTP请求信息
- Redis连接详情
- 错误堆栈信息
- 响应数据详情

## 验收报告

验收完成后，可以：

1. **查看详细报告**：使用 `docs/AUDIT_REPORT.md` 模板填写手动验收结果
2. **生成JSON报告**：使用 `--output-json` 选项生成机器可读的报告
3. **保存报告**：使用 `--output-file` 选项保存报告到文件

## 集成到CI/CD

### GitHub Actions 示例

```yaml
name: System Audit

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点运行
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r scripts/audit/requirements.txt

      - name: Run system audit
        run: |
          python scripts/audit/system_health_check.py \
            --output-json \
            --output-file audit_report.json

      - name: Upload audit report
        uses: actions/upload-artifact@v3
        with:
          name: audit-report
          path: audit_report.json
```

## 更新日志

### v1.0.0 (2025-12-17)
- 初始版本发布
- 支持6个核心验收检查
- 提供彩色终端输出和JSON报告
- 包含便捷的bash脚本

## 贡献指南

如果您发现bug或有改进建议，请：

1. 查看现有issues
2. 创建新的issue描述问题
3. 提交pull request

## 许可证

本工具遵循项目的整体许可证。

## 联系方式

- **技术负责人**: [填写负责人信息]
- **项目仓库**: [项目Git仓库地址]
- **文档**: [项目文档地址]