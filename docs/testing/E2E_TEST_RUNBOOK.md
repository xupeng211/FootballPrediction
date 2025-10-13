# 🚀 端到端测试运行手册（E2E Test Runbook）

**目标：**
验证从前端接口请求 → 后端服务处理 → 数据落库 → 返回响应的全流程可用性。

## 📋 测试范围

### 测试目录结构
```
tests/e2e/
├── api/                     # API端到端测试
│   ├── test_health_check.py
│   ├── test_prediction_workflow.py
│   └── test_user_management.py
├── workflows/               # 业务流程测试
│   ├── test_match_prediction_flow.py
│   ├── test_batch_processing.py
│   └── test_real_time_updates.py
├── performance/            # 性能测试
│   ├── test_load_simulation.py
│   └── test_stress_testing.py
└── fixtures/              # 测试数据
    ├── match_data.json
    ├── user_data.json
    └── prediction_data.json
```

### 典型测试用例
1. **test_health_check.py** - 系统健康检查
2. **test_prediction_workflow.py** - 预测完整流程
3. **test_audit_event_chain.py** - 审计事件链
4. **test_batch_processing.py** - 批量处理
5. **test_real_time_updates.py** - 实时更新

## 🌍 运行环境

### 1. 环境选择
```bash
# 推荐在以下环境运行：
# 1. Staging环境（推荐日常使用）
# 2. Nightly Job（自动化执行）
# 3. 本地Docker环境（开发调试）

# 环境变量
export TEST_ENV=e2e
export E2E_MODE=full  # full | smoke | regression
```

### 2. Staging环境配置
```yaml
# docker-compose.staging.yml
version: '3.8'
services:
  app:
    image: football-prediction:staging
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/football_staging
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BROKER=kafka:9092
      - ENVIRONMENT=staging
    depends_on:
      - db
      - redis
      - kafka
```

### 3. 测试数据库配置
```sql
-- 使用独立的测试schema
CREATE SCHEMA IF NOT EXISTS e2e_test;
SET search_path TO e2e_test, public;

-- 创建测试用户
CREATE USER e2e_user WITH PASSWORD 'e2e_pass_2024';
GRANT ALL ON SCHEMA e2e_test TO e2e_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA e2e_test TO e2e_user;
```

## 🚀 执行测试

### 1. 完整E2E测试套件
```bash
# 运行所有E2E测试
pytest tests/e2e/ \
  -v \
  --maxfail=1 \
  --disable-warnings \
  --timeout=300 \
  --junit-xml=reports/e2e-results.xml \
  --html=reports/e2e-report.html \
  --self-contained-html

# 生成详细报告
pytest tests/e2e/ --json-report --json-report-file=reports/e2e.json
python scripts/generate_e2e_report.py reports/e2e.json
```

### 2. 快速冒烟测试
```bash
# 只运行关键路径测试（5分钟内完成）
pytest tests/e2e/api/test_health_check.py \
  tests/e2e/workflows/test_match_prediction_flow.py \
  -v \
  --tb=short \
  --timeout=60 \
  --maxfail=1
```

### 3. 回归测试
```bash
# 运行历史用例，确保新更新没有破坏功能
pytest tests/e2e/ -m "regression" \
  -v \
  --maxfail=0 \
  --disable-warnings
```

### 4. 性能测试
```bash
# 负载测试
pytest tests/e2e/performance/test_load_simulation.py \
  -v \
  --benchmark-only \
  --benchmark-json=reports/e2e-performance.json

# 压力测试
pytest tests/e2e/performance/test_stress_testing.py \
  -v \
  --maxfail=1 \
  --timeout=600
```

## 🧪 测试用例示例

### 1. API端到端测试
```python
# tests/e2e/api/test_prediction_workflow.py
import pytest
from httpx import AsyncClient
import asyncio

class TestPredictionWorkflow:
    """预测工作流程端到端测试"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_prediction_flow(self):
        """测试完整的预测流程"""
        async with AsyncClient() as client:
            # 1. 用户认证
            auth_response = await client.post("/api/v1/auth/login", json={
                "username": "test_user",
                "password": "test_pass"
            })
            assert auth_response.status_code == 200
            token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. 获取比赛列表
            matches_response = await client.get(
                "/api/v1/matches?status=UPCOMING",
                headers=headers
            )
            assert matches_response.status_code == 200
            matches = matches_response.json()["data"]
            assert len(matches) > 0

            # 3. 创建预测
            match_id = matches[0]["id"]
            prediction_response = await client.post(
                "/api/v1/predictions",
                json={
                    "match_id": match_id,
                    "prediction": "HOME_WIN",
                    "confidence": 0.85
                },
                headers=headers
            )
            assert prediction_response.status_code == 201
            prediction_id = prediction_response.json()["id"]

            # 4. 验证预测保存
            get_response = await client.get(
                f"/api/v1/predictions/{prediction_id}",
                headers=headers
            )
            assert get_response.status_code == 200
            prediction = get_response.json()
            assert prediction["match_id"] == match_id
            assert prediction["status"] == "PENDING"

            # 5. 模拟比赛结果更新
            # 这里可能需要内部API或直接数据库更新
            update_response = await client.post(
                "/api/v1/admin/matches/update-result",
                json={
                    "match_id": match_id,
                    "home_score": 2,
                    "away_score": 1,
                    "status": "FINISHED"
                },
                headers=headers
            )
            assert update_response.status_code == 200

            # 6. 验证预测结果
            await asyncio.sleep(5)  # 等待异步处理
            final_response = await client.get(
                f"/api/v1/predictions/{prediction_id}",
                headers=headers
            )
            assert final_response.status_code == 200
            final_prediction = final_response.json()
            assert final_prediction["status"] == "COMPLETED"
            assert final_prediction["is_correct"] == True

            # 7. 验证审计日志
            audit_response = await client.get(
                f"/api/v1/audit/predictions/{prediction_id}",
                headers=headers
            )
            assert audit_response.status_code == 200
            audit_logs = audit_response.json()
            assert len(audit_logs) >= 3  # 创建、更新、完成
```

### 2. 批量处理测试
```python
# tests/e2e/workflows/test_batch_processing.py
class TestBatchProcessing:
    """批量处理端到端测试"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_batch_prediction_import(self):
        """测试批量导入预测"""
        async with AsyncClient() as client:
            # 1. 认证
            token = await self._get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}"}

            # 2. 上传CSV文件
            with open("tests/fixtures/batch_predictions.csv", "rb") as f:
                upload_response = await client.post(
                    "/api/v1/batch/predictions/upload",
                    files={"file": ("predictions.csv", f, "text/csv")},
                    headers=headers
                )
            assert upload_response.status_code == 202
            batch_id = upload_response.json()["batch_id"]

            # 3. 监控批处理进度
            for _ in range(30):  # 最多等待5分钟
                status_response = await client.get(
                    f"/api/v1/batch/predictions/{batch_id}/status",
                    headers=headers
                )
                status = status_response.json()

                if status["status"] == "COMPLETED":
                    break
                elif status["status"] == "FAILED":
                    pytest.fail(f"Batch processing failed: {status['error']}")

                await asyncio.sleep(10)

            # 4. 验证结果
            result_response = await client.get(
                f"/api/v1/batch/predictions/{batch_id}/results",
                headers=headers
            )
            assert result_response.status_code == 200
            results = result_response.json()
            assert results["total"] == 1000
            assert results["successful"] >= 990
            assert results["failed"] <= 10
```

### 3. 实时更新测试
```python
# tests/e2e/workflows/test_real_time_updates.py
class TestRealTimeUpdates:
    """实时更新端到端测试"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_match_updates(self):
        """测试WebSocket实时更新"""
        import websockets
        import json

        async with websockets.connect("ws://localhost:8000/ws/matches") as websocket:
            # 1. 订阅比赛更新
            await websocket.send(json.dumps({
                "action": "subscribe",
                "match_id": "12345"
            }))

            # 2. 触发比赛状态更新
            async with AsyncClient() as client:
                token = await self._get_auth_token(client)
                headers = {"Authorization": f"Bearer {token}"}

                await client.post(
                    "/api/v1/admin/matches/12345/update",
                    json={
                        "minute": 45,
                        "score": {"home": 1, "away": 0},
                        "events": ["GOAL", "YELLOW_CARD"]
                    },
                    headers=headers
                )

            # 3. 接收WebSocket更新
            message = await websocket.recv()
            update = json.loads(message)
            assert update["match_id"] == "12345"
            assert update["minute"] == 45
            assert "GOAL" in update["events"]
```

## 📊 性能测试

### 1. 负载测试配置
```python
# tests/e2e/performance/test_load_simulation.py
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
import statistics

class TestLoadSimulation:
    """负载模拟测试"""

    @pytest.mark.performance
    @pytest.mark.e2e
    async def test_concurrent_prediction_requests(self):
        """测试并发预测请求"""
        async with AsyncClient() as client:
            # 获取认证token
            token = await self._get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}"}

            # 并发参数
            concurrent_users = 50
            requests_per_user = 10
            total_requests = concurrent_users * requests_per_user

            # 收集响应时间
            response_times = []

            async def make_request(session_id):
                """单个用户请求"""
                user_times = []
                for i in range(requests_per_user):
                    start_time = time.time()

                    response = await client.post(
                        "/api/v1/predictions",
                        json={
                            "match_id": f"match_{session_id}_{i}",
                            "prediction": "HOME_WIN"
                        },
                        headers=headers
                    )

                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    user_times.append(response_time)

                    assert response.status_code in [200, 201]

                return user_times

            # 执行并发测试
            tasks = [
                make_request(user_id)
                for user_id in range(concurrent_users)
            ]

            all_times = await asyncio.gather(*tasks)
            response_times = [time for user_times in all_times for time in user_times]

            # 性能断言
            assert len(response_times) == total_requests
            assert statistics.mean(response_times) < 500  # 平均响应时间 < 500ms
            assert statistics.stdev(response_times) < 200  # 标准差 < 200ms
            assert max(response_times) < 2000  # 最大响应时间 < 2s

            # 生成性能报告
            self._generate_performance_report(response_times, {
                "concurrent_users": concurrent_users,
                "requests_per_user": requests_per_user,
                "total_requests": total_requests
            })
```

### 2. 压力测试
```python
# tests/e2e/performance/test_stress_testing.py
class TestStressTesting:
    """压力测试"""

    @pytest.mark.slow
    @pytest.mark.e2e
    async def test_sustained_load(self):
        """测试持续负载"""
        duration_seconds = 300  # 5分钟
        target_rps = 100  # 每秒100个请求

        async with AsyncClient() as client:
            token = await self._get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}"}

            start_time = time.time()
            request_count = 0
            error_count = 0
            response_times = []

            async def continuous_requests():
                nonlocal request_count, error_count
                while time.time() - start_time < duration_seconds:
                    try:
                        req_start = time.time()
                        response = await client.post(
                            "/api/v1/predictions",
                            json={
                                "match_id": f"stress_{request_count}",
                                "prediction": "DRAW"
                            },
                            headers=headers,
                            timeout=5
                        )
                        req_end = time.time()

                        if response.status_code in [200, 201]:
                            response_times.append((req_end - req_start) * 1000)
                        else:
                            error_count += 1

                        request_count += 1

                        # 控制请求速率
                        await asyncio.sleep(1.0 / target_rps)

                    except Exception as e:
                        error_count += 1
                        await asyncio.sleep(0.1)

            # 启动多个并发请求流
            tasks = [continuous_requests() for _ in range(10)]
            await asyncio.gather(*tasks)

            # 压力测试断言
            total_time = time.time() - start_time
            actual_rps = request_count / total_time
            error_rate = error_count / request_count

            assert actual_rps >= target_rps * 0.9  # 至少达到90%的目标RPS
            assert error_rate < 0.01  # 错误率低于1%
            assert statistics.mean(response_times) < 1000  # 平均响应时间 < 1s
```

## 📈 报告生成

### 1. E2E测试报告模板
```markdown
# E2E测试报告 - 2025-01-13

## 📊 测试概览
- 环境：Staging
- 执行时间：2025-01-13 22:00 - 22:45
- 总测试数：85
- 通过：82 (96.5%)
- 失败：3 (3.5%)
- 跳过：0

## 🔍 测试类别
### API端到端测试
- 通过：45/48
- 失败：3
- 平均响应时间：234ms
- 失败详情：
  - test_prediction_timeout - 超时(>5s)
  - test_concurrent_users - 503错误
  - test_websocket_disconnect - 连接断开

### 业务流程测试
- 通过：25/25
- 成功率：100%
- 平均耗时：1.2s

### 性能测试
- 负载测试：通过
  - 100并发用户，10请求/用户
  - 平均响应时间：456ms
  - 99.9分位：1.2s
- 压力测试：通过
  - 5分钟持续负载
  - 目标RPS：100，实际：98.5
  - 错误率：0.12%

## 📊 性能指标
| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 平均响应时间 | < 500ms | 234ms | ✅ |
| 99分位响应时间 | < 2s | 1.2s | ✅ |
| 错误率 | < 1% | 0.5% | ✅ |
| 并发用户数 | > 100 | 150 | ✅ |
| 吞吐量 | > 500 RPS | 520 RPS | ✅ |

## 🚨 失败分析
### 1. test_prediction_timeout
- **原因**：数据库查询优化问题
- **影响**：3/45 API测试失败
- **建议**：添加查询索引，优化慢查询

### 2. test_concurrent_users
- **原因**：连接池耗尽
- **影响**：高并发场景不稳定
- **建议**：增加连接池大小

## 🎯 改进建议
1. 优化数据库查询性能
2. 调整连接池配置
3. 添加WebSocket重连机制
4. 实施更细粒度的监控

## 📅 历史趋势
[图表展示：测试通过率趋势]
```

### 2. 自动报告生成脚本
```python
# scripts/generate_e2e_report.py
import json
import datetime
from pathlib import Path

def generate_report(result_file):
    with open(result_file) as f:
        data = json.load(f)

    report = f"""
# E2E测试报告 - {datetime.date.today()}

## 📊 测试概览
- 总测试数：{data['total']}
- 通过：{data['passed']} ({data['passed']/data['total']*100:.1f}%)
- 失败：{data['failed']} ({data['failed']/data['total']*100:.1f}%)
- 耗时：{data['duration']}s

## 🔍 详细结果
"""

    # 添加更多报告内容...

    report_file = Path(f"docs/_reports/E2E_RESULT_{datetime.date.today()}.md")
    report_file.write_text(report)
```

## 🌙 Nightly Job 配置

### GitHub Actions配置
```yaml
# .github/workflows/e2e-test.yml
name: E2E Test

on:
  schedule:
    - cron: "0 22 * * *"  # 每晚22:00执行
  workflow_dispatch:  # 手动触发

jobs:
  e2e:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [staging, production]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-html

      - name: Setup test environment
        run: |
          cp .env.example .env.test
          echo "E2E_MODE=full" >> .env.test

      - name: Run E2E tests
        run: |
          pytest tests/e2e/ \
            -v \
            --maxfail=1 \
            --disable-warnings \
            --junit-xml=e2e-results.xml \
            --html=e2e-report.html \
            --self-contained-html
        env:
          E2E_ENV: ${{ matrix.environment }}

      - name: Generate report
        run: |
          python scripts/generate_e2e_report.py e2e-results.json
          mv e2e-report.md docs/_reports/E2E_RESULT_$(date +%F).md

      - name: Upload results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-test-results-${{ matrix.environment }}
          path: |
            e2e-results.xml
            e2e-report.html

      - name: Notify on failure
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: failure
          channel: '#alerts'
          text: 'E2E测试失败，请检查报告！'
```

### 本地Cron配置
```bash
# 添加到crontab
# 每晚22:00执行E2E测试
0 22 * * * cd /path/to/project && source .venv/bin/activate && python scripts/run_e2e_nightly.py
```

## 🔧 故障排查

### 1. 测试超时
```bash
# 增加超时时间
pytest tests/e2e/ --timeout=600

# 使用异步超时
pytest tests/e2e/ --asyncio-mode=auto
```

### 2. 服务不可用
```bash
# 检查所有服务状态
docker compose -f docker-compose.staging.yml ps

# 查看服务日志
docker compose -f docker-compose.staging.yml logs -f app

# 重启服务
docker compose -f docker-compose.staging.yml restart
```

### 3. 测试数据问题
```bash
# 重新加载测试数据
python scripts/load_e2e_test_data.py --reset

# 检查数据库状态
docker exec -it football-staging-db psql -U postgres -d football -c "SELECT COUNT(*) FROM e2e_test.predictions;"
```

## 📋 测试清单

### 执行前
- [ ] 环境变量已配置
- [ ] 测试数据库已初始化
- [ ] 所有服务正常运行
- [ ] 测试数据已加载

### 执行中
- [ ] 监控测试执行进度
- [ ] 注意观察错误率
- [ ] 记录异常情况

### 执行后
- [ ] 生成测试报告
- [ ] 分析失败原因
- [ ] 创建修复任务
- [ ] 更新看板状态

## 🔄 清理操作

```bash
# 清理测试数据
python scripts/cleanup_e2e_data.py

# 清理日志
rm -f logs/e2e-*.log

# 清理报告
rm -f reports/e2e-*.xml reports/e2e-*.html

# 重置测试环境
docker compose -f docker-compose.staging.yml down -v
```

## 📝 最佳实践

1. **测试独立性**
   - 每个测试用例应该是独立的
   - 不依赖其他测试的状态
   - 使用独立的测试数据

2. **数据管理**
   - 使用事务隔离测试数据
   - 测试后清理数据
   - 使用确定性数据

3. **错误处理**
   - 明确的错误断言
   - 详细的错误日志
   - 优雅的失败处理

4. **性能考虑**
   - 设置合理的超时时间
   - 避免不必要的等待
   - 使用并发测试提高效率

---

**注意事项：**
- E2E测试运行时间较长，建议在非工作时间执行
- 确保测试环境稳定，避免外部因素影响
- 定期更新测试数据和预期结果
- 保持测试用例与实际业务场景一致
