# FeatureSmelter V4.0 模块化重构计划

> **重构目标**: 将 698 行的 FeatureSmelter 拆分为高内聚、低耦合的模块  
> **参考架构**: Harvester 成功经验 (DataFetcher → Processor → Writer)  
> **预期收益**: 测试覆盖率 80%+，支持并发处理，可插拔 Extractor

---

## 📊 当前架构分析

### FeatureSmelter V3.0-PRO 组件分布

```
FeatureSmelter.js (698 行)
├── StructuredLogger      120 行  (日志管理)
├── DEFAULT_CONFIG         10 行  (配置)
├── FeatureSmelter Class  568 行
│   ├── 初始化 (init)              60 行
│   ├── Elo 缓存管理              80 行
│   ├── 数据获取 (getPending)     70 行
│   ├── 单场比赛处理 (process)    90 行
│   ├── 批量保存 (saveFeatures)   80 行
│   ├── 主运行循环 (run)         120 行
│   └── 关闭清理 (close)          30 行
```

### 当前问题诊断

| 问题 | 影响 | 优先级 |
|------|------|--------|
| 单体类 568 行 | 难以测试、维护困难 | 🔴 高 |
| 数据库操作与业务逻辑耦合 | 无法单元测试 | 🔴 高 |
| 无并发支持 | 处理 1.2 万场需 60 秒 | 🟡 中 |
| Extractor 硬编码 | 新增特征需修改核心 | 🟡 中 |
| 日志与业务混合 | 职责不单一 | 🟢 低 |

---

## 🎯 V4.0 目标架构

### 模块拆分设计

```
src/feature_engine/smelter/v4/
├── index.js                    # 统一导出入口
├── SmelterOrchestrator.js      # 编排器 (原 run 方法)
├── components/
│   ├── DataFetcher.js          # 数据获取器
│   ├── SmelterCore.js          # 熔炼核心
│   ├── L3Writer.js             # 写入器
│   └── EloResolver.js          # Elo 解析器
├── utils/
│   ├── StructuredLogger.js     # 日志器 (独立)
│   └── BatchProcessor.js       # 批处理工具
└── extractors/
    ├── index.js                # Extractor 注册中心
    ├── BaseExtractor.js        # 抽象基类
    ├── GoldenExtractor.js      # 黄金特征
    ├── TacticalExtractor.js    # 战术特征
    ├── OddsExtractor.js        # 赔率特征
    └── EloExtractor.js         # Elo 特征
```

---

## 📦 模块详细设计

### 1. DataFetcher (数据获取器)

**职责**: 从数据库获取原始数据

```javascript
class DataFetcher {
  constructor(dbPool, config = {}) {
    this.pool = dbPool;
    this.batchSize = config.batchSize || 500;
  }

  // 获取待处理比赛
  async *fetchPendingMatches(options = {}) {
    // 返回 AsyncGenerator，支持流式处理
  }

  // 获取 Elo 缓存
  async fetchEloRatings() {
    // 返回 Map<teamName, rating>
  }

  // 获取单场比赛原始数据
  async fetchMatchRawData(matchId) {
    // 返回 raw_data JSON
  }
}
```

**测试策略**:
- 使用内存数据库 (sqlite) 进行单元测试
- Mock 数据库连接测试边界情况
- 集成测试使用 testcontainers

---

### 2. SmelterCore (熔炼核心)

**职责**: 特征提取与转换

```javascript
class SmelterCore {
  constructor(extractors = [], config = {}) {
    this.extractors = extractors;  // 可插拔 Extractor 列表
    this.config = config;
  }

  // 注册 Extractor
  registerExtractor(extractor) {
    this.extractors.push(extractor);
  }

  // 处理单场比赛
  async processMatch(matchData, context = {}) {
    const features = {};
    
    for (const extractor of this.extractors) {
      const result = await extractor.extract(matchData, context);
      features[extractor.name] = result;
    }

    return features;
  }

  // 批量处理
  async processBatch(matches, context = {}) {
    return Promise.all(
      matches.map(m => this.processMatch(m, context))
    );
  }
}
```

**测试策略**:
- 纯函数测试，无需数据库
- Mock Extractor 测试编排逻辑
- 边界条件测试

---

### 3. L3Writer (写入器)

**职责**: 批量写入 l3_features 表

```javascript
class L3Writer {
  constructor(dbPool, config = {}) {
    this.pool = dbPool;
    this.batchSize = config.batchSize || 100;
  }

  // 批量写入
  async writeBatch(features) {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      
      for (const batch of chunk(features, this.batchSize)) {
        await this._insertBatch(client, batch);
      }
      
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // 单条写入 (用于错误恢复)
  async writeSingle(feature) {
    // INSERT ... ON CONFLICT
  }
}
```

**测试策略**:
- Mock 数据库事务
- 测试批量分割逻辑
- 测试错误回滚

---

### 4. Extractor 基类与实现

**基类设计**:

```javascript
abstract class BaseExtractor {
  constructor(config = {}) {
    this.config = config;
    this.name = this.constructor.name;
  }

  // 必须实现
  abstract extract(rawData, context);

  // 可选：验证输入
  validate(rawData) {
    return true;
  }

  // 可选：转换输出
  transform(result) {
    return result;
  }
}
```

**具体实现**:

```javascript
class GoldenExtractor extends BaseExtractor {
  extract(rawData, context) {
    // 提取身价、评分等黄金特征
    return extractGoldenFeatures(rawData);
  }
}

class EloExtractor extends BaseExtractor {
  constructor(config, eloCache) {
    super(config);
    this.eloCache = eloCache;
  }

  extract(rawData, context) {
    const homeElo = this.eloCache.get(rawData.homeTeam) || 1500;
    const awayElo = this.eloCache.get(rawData.awayTeam) || 1500;
    
    return {
      home_elo: homeElo,
      away_elo: awayElo,
      elo_diff: homeElo - awayElo,
      // ...
    };
  }
}
```

---

### 5. SmelterOrchestrator (编排器)

**职责**: 协调各组件完成工作流

```javascript
class SmelterOrchestrator {
  constructor(options = {}) {
    this.fetcher = options.fetcher;
    this.core = options.core;
    this.writer = options.writer;
    this.logger = options.logger;
    this.metrics = options.metrics;
  }

  async run(options = {}) {
    // 1. 获取 Elo 缓存
    const eloCache = await this.fetcher.fetchEloRatings();
    this.core.updateContext({ eloCache });

    // 2. 流式获取待处理比赛
    const matches = this.fetcher.fetchPendingMatches(options);

    // 3. 批量处理
    for await (const batch of matches) {
      // 3.1 特征提取
      const features = await this.core.processBatch(batch);
      
      // 3.2 写入数据库
      await this.writer.writeBatch(features);
      
      // 3.3 记录指标
      this.metrics.record(batch.length);
    }

    return this.metrics.getReport();
  }
}
```

---

## 🔄 迁移路径

### Phase 1: 日志剥离 (1 天)
- [ ] 将 StructuredLogger 移动到 `utils/StructuredLogger.js`
- [ ] 更新所有引用
- [ ] 测试覆盖 100%

### Phase 2: Extractor 抽象 (2 天)
- [ ] 创建 `BaseExtractor` 抽象类
- [ ] 将现有提取器改造为继承模式
- [ ] 添加 Extractor 注册中心
- [ ] 测试覆盖 80%+

### Phase 3: 组件拆分 (3 天)
- [ ] 创建 `DataFetcher` 类
- [ ] 创建 `SmelterCore` 类
- [ ] 创建 `L3Writer` 类
- [ ] 各自独立测试

### Phase 4: 编排器重构 (2 天)
- [ ] 创建 `SmelterOrchestrator`
- [ ] 迁移主运行逻辑
- [ ] 集成测试

### Phase 5: 并发优化 (3 天)
- [ ] 实现 `WorkerPool` 支持
- [ ] 添加并发控制
- [ ] 性能基准测试

---

## 📈 预期收益

### 测试覆盖率

| 模块 | 当前 | 目标 |
|------|------|------|
| FeatureSmelter.js | ~15% | - |
| DataFetcher | 0% | 85%+ |
| SmelterCore | 0% | 90%+ |
| L3Writer | 0% | 85%+ |
| Extractors | ~30% | 90%+ |
| **整体** | **<20%** | **85%+** |

### 性能提升

| 指标 | 当前 | 目标 |
|------|------|------|
| 单线程处理 | ~200 场/秒 | ~200 场/秒 |
| 4 Worker 并发 | 不支持 | ~800 场/秒 |
| 内存使用峰值 | ~4GB | ~2GB |
| 初始化时间 | ~500ms | ~200ms |

### 可维护性

| 指标 | 当前 | 目标 |
|------|------|------|
| 最大文件行数 | 698 | <200 |
| 类职责数量 | 5+ | 1 |
| 新增 Extractor 成本 | 2-4 小时 | 30 分钟 |
| 测试编写成本 | 高 | 低 |

---

## 🚧 风险提示

### 重构风险

1. **功能回归风险**
   - 缓解: 保留 V3.0 为 legacy 版本，并行运行对比

2. **性能下降风险**
   - 缓解: 每个 Phase 都进行性能基准测试

3. **数据一致性风险**
   - 缓解: 端到端测试覆盖所有联赛

### 推荐策略

> **渐进式重构**：保持现有代码运行，新功能使用 V4.0 架构

---

**规划完成** | 版本: V1.0-PLAN | 日期: 2026-03-13
