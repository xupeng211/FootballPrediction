# 测试体系运行指南

**版本**: V4.46.6
**更新日期**: 2026-03-11
**维护团队**: TITAN QA Engineering

---

## 📋 快速开始

### 运行所有单元测试
```bash
# 容器内执行（推荐）
docker-compose -f docker-compose.dev.yml exec dev node --test tests/unit/*.test.js

# 或使用 npm 脚本
npm run test:unit
```

### 运行带覆盖率的测试
```bash
# Node.js 内置覆盖率
docker-compose -f docker-compose.dev.yml exec dev node --test --experimental-test-coverage tests/unit/*.test.js

# 或使用 npm 脚本
npm run test:coverage
```

### 运行单个测试文件
```bash
# AbstractHarvester 测试
docker-compose -f docker-compose.dev.yml exec dev node --test tests/unit/AbstractHarvester.test.js

# ProductionHarvester 测试
docker-compose -f docker-compose.dev.yml exec dev node --test tests/unit/ProductionHarvester.test.js
```

### 运行 Python 测试
```bash
# 所有 Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ -v

# 带覆盖率
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ --cov=src/ml --cov-report=term-missing

# 按标记运行
docker-compose -f docker-compose.dev.yml exec dev pytest -m unit
docker-compose -f docker-compose.dev.yml exec dev pytest -m integration
```

---

## 🧪 测试套件清单

### Node.js 单元测试 (tests/unit/)

| 测试文件 | 测试模块 | 测试用例数 | 覆盖率 | 状态 |
|---------|---------|-----------|--------|------|
| `AbstractHarvester.test.js` | 延时、重试、熔断、质量门禁、退避 | 22 | 31.11% | 🟡 需要补充 |
| `ProductionHarvester.test.js` | L2 引擎核心逻辑 | 5 | 26.05% | 🟡 需要补充 |
| `FixtureSeeder.test.js` | L1 赛程种子 | 15 | 95.18% | ✅ 优秀 |
| `SessionManager.test.js` | 会话管理 | 10 | 100% | ✅ 优秀 |
| `FeatureSmelter.test.js` | L3 特征熔炼 | 12 | 31.87% | 🟡 需要补充 |
| `MatchDetailEngine.test.js` | 比赛详情引擎 | 15 | 98.26% | ✅ 优秀 |
| `XGExtractor.test.js` | xG 提取器 | 10 | 7.87% | 🔴 严重不足 |
| `TacticalMomentumExtractor.test.js` | 战术动量 | 10 | 96.03% | ✅ 良好 |
| `StressAndSecurity.test.js` | 压力与安全测试 | 10 | 96.14% | ✅ 良好 |
| `SafeAccess.test.js` | 安全访问工具 | 5 | 100% | ✅ 优秀 |

### Python 单元测试 (tests/)

| 测试文件 | 测试模块 | 测试用例数 | 状态 |
|---------|---------|-----------|------|
| `test_ev_calculator.py` | EV 计算器 | 7 | ✅ 优秀 |
| `test_core_logic.py` | 核心逻辑 | 12 | ✅ 优秀 |
| `test_edge_cases.py` | 边缘情况 | 20 | ✅ 优秀 |

---

## 🎭 Mock 数据标本库 (tests/fixtures/)

### 1. match_success.json - 完整比赛数据
**用途**: 模拟成功的 L2 详情响应
**包含数据**:
- ✅ 完整阵容信息（首发 + 替补）
- ✅ 球员身价（Market Value）
- ✅ 射门图（Shotmap）
- ✅ 比赛事件（Goals, Cards）
- ✅ 统计数据（xG, Possession）
- ✅ 比分信息

**使用场景**:
- ProductionHarvester 成功收割测试
- FotMobStrategy 数据提取测试
- NextDataParser 解析测试

### 2. error_403_blocked.json - Cloudflare 拦截
**用途**: 模拟 403 错误场景
**触发条件**:
- Cloudflare Turnstile 验证
- IP 被封禁
- 请求频率过高

**测试验证点**:
- ✅ 重试机制是否触发
- ✅ 代理切换是否执行
- ✅ 熔断器是否激活

### 3. error_404_notfound.json - 比赛不存在
**用途**: 模拟无效比赛 ID
**测试验证点**:
- ✅ 错误分类（不可重试）
- ✅ 不触发重试
- ✅ 记录失败原因

### 4. malformed_data.json - 数据损坏
**用途**: 模拟数据源异常
**包含问题**:
- ❌ 缺失统计数据
- ❌ 空阵容列表
- ❌ 缺少身价信息

**测试验证点**:
- ✅ QUALITY_GATE 验证失败
- ✅ 记录数据质量问题
- ✅ 不写入数据库

### 5. timeout_scenario.json - 网络超时
**用途**: 模拟网络超时场景
**配置**:
- 连接超时: 30s
- 请求超时: 60s
- 模拟延时: 65s

**测试验证点**:
- ✅ 触发重试
- ✅ 指数退避
- ✅ 最终超时失败

---

## 🔧 网络模拟器配置 (nock)

### 全局配置
```javascript
// 在测试文件的 beforeEach 中配置
beforeEach(() => {
    // 禁用所有真实网络连接（严格模式）
    nock.disableNetConnect();

    // 清理之前的拦截器
    nock.cleanAll();
});

afterEach(() => {
    // 清理 nock
    nock.cleanAll();
    nock.enableNetConnect();
});
```

### Mock FotMob API 示例
```javascript
// Mock 成功响应
nock('https://www.fotmob.com')
    .get('/api/matchDetails')
    .query({ matchId: '4803413' })
    .reply(200, fixtures.matchSuccess);

// Mock 403 错误
nock('https://www.fotmob.com')
    .get('/match/4803413')
    .reply(403, fixtures.error403);

// Mock 超时
nock('https://www.fotmob.com')
    .get('/match/4803413')
    .delayConnection(65000) // 65s 延时
    .reply(200, {});
```

### 验证 Mock 调用
```javascript
// 检查所有 Mock 是否被调用
assert.ok(nock.isDone(), '所有 Mock 请求应该被调用');

// 检查未调用的 Mock
const pendingMocks = nock.pendingMocks();
assert.strictEqual(pendingMocks.length, 0, '不应该有未调用的 Mock');
```

---

## 📊 覆盖率目标与现状

### 当前整体覆盖率
```
Line Coverage:    54.51%  ❌ (目标: 80%)
Branch Coverage:  84.10%  ✅ (目标: 80%)
Function Coverage: 48.44%  ❌ (目标: 80%)
```

### 核心模块覆盖率

| 模块 | Line | Branch | Function | 状态 | 优先级 |
|------|------|--------|----------|------|--------|
| **AbstractHarvester** | 31.11% | 80.00% | 20.69% | 🟡 | P0 |
| **ProductionHarvester** | 26.05% | 60.00% | 16.67% | 🔴 | P0 |
| **FotMobStrategy** | 28.50% | 100% | 10.00% | 🔴 | P0 |
| **NextDataParser** | 27.07% | 100% | 0.00% | 🔴 | P0 |
| **PostgresClient** | 54.86% | 66.67% | 4.76% | 🟡 | P1 |
| **WorkerPool** | 47.57% | 100% | 0.00% | 🟡 | P1 |

### 提升到 80% 的路线图

#### 阶段 1: 核心收割引擎 (2 周)
- [ ] AbstractHarvester 补充测试 (目标: 80%)
- [ ] ProductionHarvester 补充测试 (目标: 80%)
- [ ] FotMobStrategy 补充测试 (目标: 80%)
- [ ] NextDataParser 补充测试 (目标: 80%)

#### 阶段 2: 数据与并发层 (1 周)
- [ ] PostgresClient 补充测试 (目标: 80%)
- [ ] WorkerPool 补充测试 (目标: 80%)
- [ ] NetworkManager 补充测试 (目标: 80%)
- [ ] NetworkShield 补充测试 (目标: 80%)

#### 阶段 3: 辅助模块 (1 周)
- [ ] MetricsClient 补充测试 (目标: 80%)
- [ ] SessionManager 补充测试 (目标: 80%)
- [ ] SwarmHarvester 补充测试 (目标: 80%)

---

## 🚨 故障排查

### 问题 1: 测试失败 - "Cannot find module 'nock'"
**解决方案**:
```bash
docker-compose -f docker-compose.dev.yml exec dev npm install --save-dev nock@13.5.0
```

### 问题 2: 覆盖率报告不显示
**解决方案**:
```bash
# 确保使用 --experimental-test-coverage 标志
node --test --experimental-test-coverage tests/unit/*.test.js
```

### 问题 3: Mock 数据格式错误
**检查步骤**:
1. 验证 JSON 格式: `cat tests/fixtures/match_success.json | jq .`
2. 检查 QUALITY_GATE 要求: `config/factory_config.js`
3. 查看最小体积要求: `minSizeBytes: 5000`

### 问题 4: 网络请求未被拦截
**调试方法**:
```javascript
// 在测试中添加日志
nock.emitter.on('no match', (req) => {
    console.error('❌ 未匹配的请求:', req.path);
});
```

---

## 📚 测试编写规范

### 命名约定
```javascript
// 测试套件: 模块名 + 功能描述
describe('AbstractHarvester 容错机制测试套件', () => {

    // 子套件: 具体功能模块
    describe('模块 1: _delay() 延时函数测试', () => {

        // 测试用例: 编号 + 描述
        it('测试 1.1: 应该产生指定毫秒的延时', async () => {
            // 测试代码
        });
    });
});
```

### 断言规范
```javascript
// ✅ 推荐：详细的断言消息
assert.ok(
    elapsed >= testDelay - 10 && elapsed <= testDelay + 10,
    `延时 ${elapsed}ms 不在预期范围 [${testDelay - 10}, ${testDelay + 10}] 内`
);

// ❌ 不推荐：简单的断言
assert.ok(elapsed >= 50);
```

### Mock 使用规范
```javascript
// ✅ 推荐：清晰的 Mock 配置
nock('https://www.fotmob.com')
    .get('/match/4803413')
    .reply(200, fixtures.matchSuccess);

// ❌ 不推荐：硬编码响应
nock('https://www.fotmob.com')
    .get('/match/4803413')
    .reply(200, { id: 123 });
```

---

## 🎯 质量门禁

### 提交前必须通过
- ✅ 所有单元测试通过 (`npm run test:unit`)
- ✅ Lint 检查通过 (`npm run lint`)
- ✅ 格式化检查通过 (`npm run format:check`)

### 合并到主分支前必须达到
- ✅ 整体覆盖率 >= 50%
- ✅ 核心模块覆盖率 >= 70%
- ✅ 新增代码覆盖率 >= 80%
- ✅ 所有测试通过（无 skip）

---

## 📞 联系方式

**测试基础设施团队**: titan-qa@example.com
**文档维护**: docs@example.com
**紧急问题**: @titan-oncall

---

**最后更新**: 2026-03-11
**文档版本**: V1.0.0
