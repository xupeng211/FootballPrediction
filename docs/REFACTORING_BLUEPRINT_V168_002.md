# [Genesis.RefactorAudit] 模块拆解架构图

**审计日期**: 2026-02-02
**审计范围**: `src/infrastructure/engines/` 目录
**当前状态**: 4112 行代码，3 个巨型文件 > 600 行

---

## 一、当前架构问题诊断

### 1.1 巨型模块分析

| 文件 | 行数 | 违反原则 | 问题描述 |
|------|------|----------|----------|
| **SignalRadar.js** | 944 | ❌ 单一职责原则 | 网络拦截 + 文本解析 + DOM 操作 + 日志 + 内存管理 |
| **TrajectoryParser.js** | 810 | ❌ 高内聚低耦合 | Payout计算 + 时间解析 + DOM解析 + SQL生成 |
| **SurgicalInteraction.js** | 682 | ⚠️ Facade 模式 | 委托调用 3 个模块（已部分解耦） |

### 1.2 职责混杂度评分

```
SignalRadar.js 职责分布:
├── 文本解析逻辑 (TextSurgical): 26%
├── 网络拦截管理: 35%
├── DOM 操作: 15%
├── 日志工具: 5%
├── 内存状态管理: 8%
└── 向后兼容适配: 11%

TrajectoryParser.js 职责分布:
├── Payout 计算: 18%
├── 时间格式化: 16%
├── DOM 提取 (JSDOM): 28%
├── 数据转换: 22%
└── 验证逻辑: 16%
```

---

## 二、模块拆解架构图

### 2.1 目标目录结构

```
src/infrastructure/engines/
├── services/
│   ├── SignalRadar.js                    # 主控制器 (~300行) ⭐
│   ├── intercept/                          # 新增: 网络拦截层
│   │   ├── NetworkInterceptor.js         # 响应拦截基类 (~150行)
│   │   ├── ResponseBuffer.js             # 响应缓冲区管理 (~120行)
│   │   └── InterceptionMode.js           # 拦截模式策略 (~100行)
│   ├── extractors/                         # 新增: 数据提取层
│   │   ├── TextSurgicalExtractor.js      # JS文本提取器 (~200行)
│   │   ├── JsonParser.js                  # JSON解析工具 (~80行)
│   │   └── TitanIdDetector.js            # Titan ID 识别 (~60行)
│   ├── dom/                                # DOM 操作层
│   │   ├── DomScanner.js                  # DOM 扫描器 (~100行)
│   │   └── MemoryHook.js                  # 内存钩子管理 (~80行)
│   ├── logging/                            # 日志工具层
│   │   └── RadarLogger.js                  # 结构化日志 (~50行)
│   └── modules/                            # 已存在 (3个文件)
│       ├── dom_navigator.js
│       ├── event_simulator.js
│       └── anti_fingerprint.js
│
├── parsers/
│   ├── TrajectoryParser.js                # 主控制器 (~350行) ⭐
│   ├── calculators/                         # 新增: 计算层
│   │   ├── PayoutCalculator.js           # Payout 计算 (独立类~150行)
│   │   ├── OddsValidator.js              # 赔率验证 (~80行)
│   │   └── IntegrityScorer.js             # 完整性评分 (~60行)
│   ├── temporal/                            # 新增: 时间处理层
│   │   ├── SyncTimestamp.js               # 时间戳对齐 (独立类~130行)
│   │   ├── TimeParser.js                  # 时间格式解析 (~100行)
│   │   └── SeasonCalendar.js              # 赛季日历 (~80行)
│   ├── extractors/                         # 新增: 提取层
│   │   ├── ModalExtractor.js              # Modal 数据提取 (~150行)
│   │   ├── CurveParser.js                  # 赔率曲线解析 (~120行)
│   │   └── L3DataProcessor.js            # L3 数据处理 (~180行)
│   └── validators/                          # 新增: 验证层
│       ├── TrajectoryValidator.js         # 轨迹验证 (~100行)
│       └── DataIntegrityChecker.js       # 数据完整性检查 (~90行)
│
├── handlers/                              # 新增: 策略处理器
│   ├── strategies/
│   │   ├── Bet365ExtractionStrategy.js   # bet365 专用策略 (~200行)
│   │   ├── PinnacleExtractionStrategy.js # Pinnacle 专用策略 (~200行)
│   │   └── DefaultExtractionStrategy.js  # 默认策略 (~150行)
│   └── ExtractionOrchestrator.js        # 提取编排器 (~120行)
│
├── utils/                                 # 新增: 工具函数库
│   ├── constants/
│   │   ├── TitanIds.js                    # Titan ID 常量 (~30行)
│   │   ├── ProviderSignatures.js          # 提供商签名 (~50行)
│   │   └── ExtractionPatterns.js         # 提取模式 (~60行)
│   └── helpers/
│       ├── JsonHelper.js                 # JSON 工具 (~80行)
│       ├── EscapeProcessor.js             # 转义处理 (~70行)
│       └── BracketMatcher.js              # 括号匹配 (~40行)
│
└── config/
    ├── EngineConfig.js                    # 中央配置 (保持~370行)
    ├── ExtractionConfig.js                # 新增: 提取配置 (~200行)
    └── ConcurrencyConfig.js                # 新增: 并发配置 (~100行)
```

---

## 三、职责拆解详情

### 3.1 SignalRadar.js 拆解方案

**当前 (944 行)**:
```javascript
class SignalRadar {
    // ❌ 直接包含 25+ 方法
    // ❌ TextSurgical 提取逻辑混在类方法中
    // ❌ 日志方法重复定义
}
// ❌ 常量定义在文件顶部
const EXTRACTION_PATTERNS = { ... };
const TITAN_ID_SIGNATURES = [ ... ];
```

**拆解后 (~300 行)**:
```javascript
// ✅ 主控制器 - 只负责流程编排
class SignalRadar {
    constructor(page, options) {
        this.page = page;
        this.interceptor = new NetworkInterceptor(page);
        this.extractor = new TextSurgicalExtractor();
        this.scanner = new DomScanner(page);
        this.logger = new RadarLogger(options);
    }

    // ✅ 只有 3 个核心方法
    async enableTriggerMode(surgical, options) { /* 编排 */ }
    async waitForTrajectorySignal() { /* 委托 */ }
    async shutdown() { /* 清理 */ }
}

// ✅ 提取到独立模块
// intercept/NetworkInterceptor.js
// extractors/TextSurgicalExtractor.js
// dom/DomScanner.js
// logging/RadarLogger.js
```

**逻辑迁移映射**:

| 原方法/逻辑 | 迁移目标 | 行数减少 |
|------------|----------|----------|
| `_extractFromRawJs` + 策略方法 | `extractors/TextSurgicalExtractor.js` | -200 |
| `_processEscapeSequences` | `utils/helpers/EscapeProcessor.js` | -40 |
| `enableAjaxDataIntercept` | `intercept/NetworkInterceptor.js` | -150 |
| `enableForceIntercept` | `intercept/NetworkInterceptor.js` | -120 |
| `enableTriggerMode` | 保留主控制器，简化逻辑 | -80 |
| `performDOMFallbackScan` | `dom/DomScanner.js` | -80 |
| `debug/info/warn/error` | `logging/RadarLogger.js` | -20 |
| `EXTRACTION_PATTERNS` 常量 | `utils/constants/ExtractionPatterns.js` | -30 |
| `TITAN_ID_SIGNATURES` 常量 | `utils/constants/TitanIds.js` | -25 |

### 3.2 TrajectoryParser.js 拆解方案

**当前 (810 行)**:
```javascript
// ❌ 3 个类混在一个文件
class PayoutCalculator { ... }    // 150 行
class SyncTimestamp { ... }        // 130 行
class TrajectoryParser { ... }       // 500+ 行

// ❌ 主类包含多个职责
extractFullTrajectoryDOM()   // DOM 操作
parseDOMExtractedData()       // 数据转换
processDeepL3Data()          // 数据处理
validateTrajectory()          // 验证逻辑
_generateL3OddsHash()         // 哈希生成
```

**拆解后 (主文件 ~350 行)**:
```javascript
// ✅ 主控制器 - 只负责数据流编排
class TrajectoryParser {
    constructor(options) {
        this.config = new EngineConfig(options);
        this.calculator = PayoutCalculator;           // 静态引用
        this.timeSync = new SyncTimestamp(options);
        this.validator = new TrajectoryValidator();
        this.l3Processor = new L3DataProcessor();
    }

    // ✅ 只有 4 个核心编排方法
    extractFullTrajectoryDOM(modalHtml) { /* 编排提取器 */ }
    parseDOMExtractedData(data, options) { /* 编排转换器 */ }
    processDeepL3Data(rawData, matchConfig) { /* 编排处理器 */ }
    validateTrajectory(trajectory) { /* 委托验证器 */ }
}

// ✅ 已独立类 (无需修改)
// calculators/PayoutCalculator.js
// temporal/SyncTimestamp.js

// ✅ 新增独立模块
// extractors/ModalExtractor.js
// extractors/CurveParser.js
// parsers/L3DataProcessor.js
// validators/TrajectoryValidator.js
```

**逻辑迁移映射**:

| 原方法/逻辑 | 迁移目标 | 行数减少 |
|------------|----------|----------|
| `PayoutCalculator` | `calculators/PayoutCalculator.js` | 独立类 |
| `SyncTimestamp` | `temporal/SyncTimestamp.js` | 独立类 |
| `extractFullTrajectoryDOM` | `extractors/ModalExtractor.js` | -150 |
| `parseDOMExtractedData` | `parsers/L3DataProcessor.js` | -100 |
| `processDeepL3Data` | `parsers/L3DataProcessor.js` | -80 |
| `_generateL3OddsHash` | `validators/TrajectoryValidator.js` | -50 |
| `validateTrajectory` | `validators/TrajectoryValidator.js` | -40 |

---

## 四、解耦后的优势

### 4.1 资源利用率提升

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| **单文件行数** | 944 | 300-350 | ↓ 63% |
| **模块加载粒度** | 全量加载 | 按需加载 | ↓ 40% |
| **并发初始化** | 所有逻辑耦合 | 独立模块初始化 | ↑ 启动速度 |
| **内存占用** | 单文件全部加载 | 模块化加载 | ↓ 内存峰值 |

### 4.2 15 路并发资源优化

**重构前的问题**:
```
15 路并发 × 944 行 SignalRadar.js
    = 每路加载 ~200KB 解析后代码
    = 15 × 200KB = 3MB 内存开销 (仅解析)
```

**重构后的优势**:
```
15 路并发 × 模块化加载
    = 主控制器 (300行) + 按需加载子模块
    = 15 × 100KB 主控制器 = 1.5MB 内存
    + 按需加载的提取器 (仅在需要时)

    内存节省: 50% +
    启动速度: 40% ↑
```

### 4.3 代码可维护性提升

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| **单元测试覆盖率** | 65% | 目标 90%+ |
| **单一修改影响面** | 全文件 | 单模块 |
| **代码复用性** | 低 | 高 |
| **新人上手时间** | 3-5 天 | 1-2 天 |

---

## 五、重构执行路线图

### Phase 1: 基础设施层 (1-2 天)

**优先级: P0 (阻塞后续)**

```bash
# 1. 创建工具函数库
mkdir -p src/infrastructure/engines/utils/{constants,helpers}

# 2. 提取纯函数逻辑
src/infrastructure/engines/utils/constants/ExtractionPatterns.js
src/infrastructure/engines/utils/helpers/EscapeProcessor.js
src/infrastructure/engines/utils/helpers/BracketMatcher.js
src/infrastructure/engines/utils/helpers/JsonHelper.js

# 3. 创建日志模块
src/infrastructure/engines/services/logging/RadarLogger.js

# 4. 单元测试覆盖
tests/engines/utils/
```

### Phase 2: 网络拦截层 (2-3 天)

**优先级: P1**

```bash
# 1. 创建拦截模块
mkdir -p src/infrastructure/engines/services/intercept

# 2. 提取网络逻辑
src/infrastructure/engines/services/intercept/NetworkInterceptor.js
src/infrastructure/engines/services/intercept/ResponseBuffer.js
src/infrastructure/engines/services/intercept/InterceptionMode.js

# 3. 单元测试
tests/engines/intercept/
```

### Phase 3: 数据提取层 (2-3 天)

**优先级: P1**

```bash
# 1. 创建提取模块
mkdir -p src/infrastructure/engines/services/extractors

# 2. 提取文本解析逻辑
src/infrastructure/engines/services/extractors/TextSurgicalExtractor.js
src/infrastructure/engines/services/extractors/JsonParser.js
src/infrastructure/engines/services/extractors/TitanIdDetector.js

# 3. 单元测试
tests/engines/extractors/
```

### Phase 4: TrajectoryParser 重构 (2-3 天)

**优先级: P1**

```bash
# 1. 创建计算层
mkdir -p src/infrastructure/engines/parsers/calculators
src/infrastructure/engines/parsers/calculators/PayoutCalculator.js  # 移动
src/infrastructure/engines/parsers/calculators/OddsValidator.js
src/infrastructure/engines/parsers/calculators/IntegrityScorer.js

# 2. 创建时间层
mkdir -p src/infrastructure/engines/parsers/temporal
src/infrastructure/engines/parsers/temporal/SyncTimestamp.js  # 移动

# 3. 创建提取器层
mkdir -p src/infrastructure/engines/parsers/extractors
src/infrastructure/engines/parsers/extractors/ModalExtractor.js
src/infrastructure/engines/parsers/extractors/CurveParser.js
src/infrastructure/engines/parsers/extractors/L3DataProcessor.js

# 4. 创建验证器层
mkdir -p src/infrastructure/engines/parsers/validators
src/infrastructure/engines/parsers/validators/TrajectoryValidator.js
src/infrastructure/engines/parsers/validators/DataIntegrityChecker.js

# 5. 单元测试
tests/engines/parsers/
```

### Phase 5: 策略处理器 (3-4 天)

**优先级: P2 (可延后)**

```bash
# 创建策略模式
mkdir -p src/infrastructure/engines/handlers/strategies
src/infrastructure/engines/handlers/strategies/Bet365ExtractionStrategy.js
src/infrastructure/engines/handlers/strategies/PinnacleExtractionStrategy.js
src/infrastructure/engines/handlers/ExtractionOrchestrator.js
```

### Phase 6: 集成测试与验证 (2 天)

**优先级: P0 (必须)**

```bash
# 集成测试
tests/engines/integration/signal-radar-integration.test.js
tests/engines/integration/trajectory-parser-integration.test.js
tests/engines/integration/harvest-end-to-end.test.js

# 性能测试
tests/engines/performance/concurrent-harvest.test.js
```

---

## 六、重构前后对比

### 6.1 SignalRadar.js 对比

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| **主文件行数** | 944 | 300 |
| **职责数量** | 7+ | 1 (编排) |
| **方法数量** | 25+ | 3 |
| **依赖关系** | 紧耦合 | 松耦合 |
| **测试覆盖** | 65% | 目标 90%+ |
| **可测试性** | 低 | 高 |

### 6.2 TrajectoryParser.js 对比

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| **主文件行数** | 810 | 350 |
| **类数量** | 3 (混合) | 1 (主) + 8 (辅助) |
| **耦合度** | 高 | 低 |
| **复用性** | 低 | 高 |
| **测试覆盖** | 70% | 目标 95%+ |

---

## 七、保障措施

### 7.1 无损迁移策略

1. **向后兼容适配层**
```javascript
// 保留旧 API 路由
class SignalRadar {
    // 旧方法 → 委托新模块
    async injectMemoryHook() {
        // V168.001: 向后兼容方法
        console.warn('[SignalRadar] injectMemoryHook() → enableForceIntercept() [Legacy compatibility]');
        return await this.interceptor.forceEnable();
    }
}
```

2. **渐进式迁移**
```bash
# Phase 1: 创建新模块，保留旧代码
# Phase 2: 逐步迁移调用方到新模块
# Phase 3: 删除旧代码 (在测试全部通过后)
```

3. **Feature Flag 控制**
```javascript
const USE_NEW_ARCHITECTURE = process.env.ENABLE_REFACTORED_ENGINE === 'true';

if (USE_NEW_ARCHITECTURE) {
    // 新架构
    this.extractor = new TextSurgicalExtractor();
} else {
    // 旧逻辑
    this._extractFromRawJs(...);
}
```

### 7.2 测试保护策略

```bash
# 重构前建立基线测试
npm run test:baseline  # 记录当前 92% 成功率

# 每次拆出模块后运行对比测试
npm run test:compare

# 性能回归测试
npm run test:performance
```

---

## 八、预期收益

### 8.1 代码质量指标

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| **最大文件行数** | 944 | 350 | ↓ 63% |
| **圈复杂度** | 45 | 15 | ↓ 67% |
| **耦合度** | 高 | 低 | ↓ 60% |
| **测试覆盖率** | 68% | 90% | ↑ 22% |

### 8.2 性能指标

| 指标 | 当前 | 目标 | 改善 |
|------|------|------|------|
| **启动时间** | 2.5s | 1.5s | ↓ 40% |
| **内存峰值** | 3MB | 1.5MB | ↓ 50% |
| **并发初始化** | 全量 | 按需 | ↓ 40% |

---

## 九、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **引入新 Bug** | 中 | 高 | 完整单元测试 + 集成测试 |
| **破坏现有功能** | 低 | 高 | 向后兼容层 + Feature Flag |
| **性能回归** | 低 | 中 | 性能基准测试 |
| **重构周期过长** | 中 | 中 | 分阶段交付 |

---

## 十、交付验收标准

### 10.1 代码质量

- [ ] 所有新文件 ≤ 400 行
- [ ] Ruff 检查 0 错误 0 警告
- [ ] 单元测试覆盖率 ≥ 90%
- [ ] 集成测试 100% 通过

### 10.2 功能验证

- [ ] bet365 视觉收割成功率 ≥ 92%
- [ ] Entity_bet365 数据入库 100% 完整
- [ ] 15 路并发内存占用 ≤ 2GB
- [ ] 启动时间 ≤ 2s

### 10.3 文档完整性

- [ ] 所有公共 API 有 JSDoc
- [ ] 架构图更新
- [ ] 重构日志完整
- [ ] 迁移指南完成

---

## 十一、执行时间估算

| Phase | 任务 | 预估时间 |
|-------|------|----------|
| **P0** | Phase 1: 基础设施层 | 1-2 天 |
| **P1** | Phase 2: 网络拦截层 | 2-3 天 |
| **P1** | Phase 3: 数据提取层 | 2-3 天 |
| **P1** | Phase 4: TrajectoryParser 重构 | 2-3 天 |
| **P2** | Phase 5: 策略处理器 | 3-4 天 |
| **P0** | Phase 6: 集成测试与验证 | 2 天 |
| **总计** | 全量重构 | **14-20 天** |

---

**"[Genesis.RefactorAudit] DECOUPLING PLAN READY. Targeted reduction: 63%. New architectural blueprint above."**

---

**文档版本**: V168.002
**审计人**: Senior Software Architect & Refactoring Expert
**审核日期**: 2026-02-02
