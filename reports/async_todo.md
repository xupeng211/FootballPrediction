# FootballPrediction 异步化改造清单

**项目**: Football Prediction System
**目标**: 全面异步标准化改造
**生成时间**: 2025-12-06
**负责人**: Async架构负责人

---

## 🎯 改造目标

- [x] 扫描同步调用模式 (`reports/async_scan.txt`)
- [ ] 创建Async Base Class全局基类
- [ ] 开发自动迁移工具
- [ ] Collectors批次迁移 (P0)
- [ ] Service Layer异步化 (P1)
- [ ] FastAPI层完善 (P1)
- [ ] Database Layer优化 (P2)
- [ ] CI测试与回归验证

---

## 📊 模块改造优先级

### 🔴 P0 - 立即改造 (关键路径)

#### 1. Data Collectors 异步化
**影响**: 数据采集效率，核心业务功能
**工作量**: 2-3天
**风险**: 高 (需保证数据完整性)

| 文件路径 | 当前状态 | 改造内容 | 优先级 | 依赖 |
|---------|---------|---------|--------|------|
| `src/collectors/html_fotmob_collector.py` | ❌ requests同步 | requests → httpx.AsyncClient | P0-Critical | Async Base Class |
| `src/data/collectors/fbref_collector.py` | ❌ curl_cffi同步 | curl_cffi → httpx.AsyncClient | P0-Critical | Async Base Class |
| `src/data/collectors/fbref_details_collector.py` | ❌ curl_cffi同步 | curl_cffi → httpx.AsyncClient | P0-Critical | Async Base Class |
| `src/data/collectors/fbref_team_collector.py` | ❌ curl_cffi同步 | curl_cffi → httpx.AsyncClient | P0-Critical | Async Base Class |
| `src/data/collectors/fbref_collector_pure.py` | ❌ curl_cffi同步 | curl_cffi → httpx.AsyncClient | P0-Critical | Async Base Class |

**验证方法**:
- 每个collector迁移后运行3条记录采集测试
- 对比同步/异步采集结果一致性
- 性能测试: 异步版本吞吐量应提升2-3倍

#### 2. 工具函数异步化
**影响**: 消除阻塞调用，提升并发能力
**工作量**: 1天
**风险**: 中等 (需要保证重试逻辑正确)

| 文件路径 | 当前状态 | 改造内容 | 优先级 | 测试 |
|---------|---------|---------|--------|------|
| `src/utils/_retry.py` | ❌ time.sleep | time.sleep → asyncio.sleep | P0-High | 单元测试 |
| `src/utils/_retry/__init__.py` | ❌ time.sleep | time.sleep → asyncio.sleep | P0-High | 单元测试 |
| `src/patterns/decorator.py` | ❌ time.sleep | time.sleep → asyncio.sleep | P0-High | 单元测试 |
| `src/cache/ttl_cache_enhanced/ttl_cache.py` | ❌ time.sleep | time.sleep → asyncio.sleep | P0-Medium | 集成测试 |

### 🟡 P1 - 后续改造 (优化性能)

#### 3. Inference Layer 异步化
**影响**: 推理性能，模型加载速度
**工作量**: 1-2天
**风险**: 中等 (需保证模型加载稳定性)

| 文件路径 | 当前状态 | 改造内容 | 优先级 | 测试 |
|---------|---------|---------|--------|------|
| `src/inference/predictor.py` | ⚠️ 混合状态 | predict_sync → async predict | P1-High | 推理测试 |
| `src/inference/loader.py` | ⚠️ 混合状态 | _load_model_sync → async | P1-High | 模型加载测试 |
| `src/inference/hot_reload.py` | ✅ 大部分异步 | 完善异步逻辑 | P1-Medium | 热重载测试 |

#### 4. Job Scripts 异步化
**影响**: 批处理性能，数据回填效率
**工作量**: 1天
**风险**: 低 (不影响实时业务)

| 文件路径 | 当前状态 | 改造内容 | 优先级 | 测试 |
|---------|---------|---------|--------|------|
| `src/jobs/run_season_backfill.py` | ❌ requests同步 | requests → httpx.AsyncClient | P1-Medium | 批处理测试 |
| `src/jobs/run_season_fixtures.py` | ❌ requests同步 | requests → httpx.AsyncClient | P1-Medium | 批处理测试 |

### 🟢 P2 - 可选改造 (完善体验)

#### 5. API 层完善
**影响**: 代码质量，维护性
**工作量**: 0.5天
**风险**: 低

| 文件路径 | 当前状态 | 改造内容 | 优先级 | 测试 |
|---------|---------|---------|--------|------|
| `src/api/predictions.py` | ⚠️ 测试代码 | 清理同步示例 | P2-Low | API测试 |
| `src/api/README.md` | ⚠️ 文档示例 | 更新为异步示例 | P2-Low | 文档验证 |

---

## 🛠️ 技术方案

### 1. Async Base Class 设计

```python
# src/core/async_base.py
class AsyncBaseCollector:
    """异步采集器基类"""

    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            headers=await self._get_headers(),
            timeout=self._get_timeout()
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
```

### 2. 迁移模式

#### HTTP客户端迁移
```python
# ❌ 同步版本
def fetch_data(url):
    response = requests.get(url)
    return response.json()

# ✅ 异步版本
async def fetch_data(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

#### 数据库操作迁移
```python
# ✅ 已正确实现 (无需改动)
async def get_match(match_id: str):
    async with get_db_session() as session:
        result = await session.execute(
            select(Match).where(Match.id == match_id)
        )
        return result.scalar_one_or_none()
```

---

## 📋 执行计划

### Phase 1: 基础设施 (第3-4步)
- [x] 步骤1: 扫描同步调用模式
- [ ] 步骤2: 生成异步化清单
- [ ] 步骤3: 创建Async Base Class全局基类
- [ ] 步骤4: 开发自动迁移工具

**交付物**:
- `src/core/async_base.py` - 异步基类
- `scripts/async_migrate.py` - 自动迁移工具
- `patches/async_unification/*.patch` - 迁移补丁

### Phase 2: 核心改造 (第5-8步)
- [ ] 步骤5: 批次迁移collectors (P0)
- [ ] 步骤6: 迁移Database Layer (P2)
- [ ] 步骤7: 迁移Service Layer (P1)
- [ ] 步骤8: 迁移FastAPI层 (P1)

**验收标准**:
- 所有HTTP请求使用异步客户端
- 所有阻塞操作使用async/await
- 单元测试通过率 > 95%
- 性能提升: 采集吞吐量 +200%

### Phase 3: 验证与优化 (第9步)
- [ ] 步骤9: CI测试与回归验证

**验证指标**:
```bash
make test.smart      # 核心功能测试
make coverage        # 覆盖率验证
# 采集器性能测试
python scripts/async_performance_test.py
# API延迟测试
curl -w "@curl-format.txt" http://localhost:8000/api/v1/predictions
```

---

## 🚨 风险控制

### 技术风险
1. **数据一致性**: 异步采集必须保证数据完整性
2. **性能回退**: 避免过度await导致性能下降
3. **依赖冲突**: httpx与现有依赖可能冲突

### 缓解措施
1. **渐进式迁移**: 按模块逐步改造，避免大爆炸
2. **双版本并行**: 同步/异步版本并存，便于回滚
3. **完整测试**: 每个模块迁移后必须验证功能正确性
4. **性能基准**: 建立性能基线，对比改造效果

### 回滚计划
```bash
# 如果异步版本出现问题，快速回滚
git checkout pre-async-migration
make dev  # 重启同步版本
```

---

## 📊 成功指标

### 性能指标
- **数据采集QPS**: 提升200% (当前 10 QPS → 目标 30 QPS)
- **API响应时间**: P95 < 200ms
- **并发处理能力**: 支持1000并发连接

### 质量指标
- **测试覆盖率**: 维持29%以上
- **代码质量**: ruff评分保持A+
- **异步化完成度**: 95%以上

### 可维护性指标
- **代码复杂度**: 不增加超过10%
- **技术债务**: 显著减少同步阻塞调用
- **文档完整性**: 100%API异步文档

---

## 📝 后续规划

异步化完成后，可考虑以下优化:

1. **P1-5: 性能/缓存体系** - Redis缓存层异步优化
2. **P1-6: 数据链路压测** - 全链路性能基准测试
3. **监控增强** - 异步指标监控和告警
4. **部署优化** - 异步友好的容器编排

---

**当前状态**: 准备开始第3步 - 创建Async Base Class
**下一步**: 等待确认后开始实施基础设施改造