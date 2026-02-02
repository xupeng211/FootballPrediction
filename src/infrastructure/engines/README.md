# Engines Directory - V168.002 Architecture

## 📁 目录结构

```
engines/
├── services/                    # 业务服务层
│   ├── SignalRadar.js         # V168.002 网络雷达调度中心 (主控制器 ~300行)
│   ├── SurgicalInteraction.js # V165.000 事件驱动 Facade
│   ├── TelemetryService.js    # 遥测服务
│   ├── intercept/              # 网络拦截层
│   │   └── NetworkInterceptor.js         # 响应拦截基类
│   ├── extractors/             # 数据提取层
│   │   └── TextSurgicalExtractor.js      # JS文本提取器
│   ├── logging/                # 日志工具层
│   │   └── RadarLogger.js                # 结构化日志
│   └── modules/                # 现有模块 (3个文件)
│       ├── dom_navigator.js    # DOM 导航
│       ├── event_simulator.js  # 事件模拟
│       └── anti_fingerprint.js # 反指纹检测
│
├── parsers/                     # 数据解析层
│   ├── index.js                # V168.002 统一导出入口
│   ├── TrajectoryParser.js     # V168.002 轨迹解析器 (主控制器 ~350行)
│   ├── calculators/             # 计算层
│   │   └── PayoutCalculator.js          # Payout 计算
│   └── temporal/               # 时间处理层
│       └── SyncTimestamp.js             # 时间戳对齐
│
├── middleware/                  # 中间件
│   └── ErrorHandler.js         # V167.000 错误处理
│
├── config/                     # 配置文件
│   ├── EngineConfig.js         # V167.000 中央配置
│   ├── ModalSelectorConfig.js  # 模态框选择器配置
│   └── ReactIndexConfig.js     # React 索引配置
│
├── selectors/                  # 选择器库
│   └── OddsPortalSelectors.js  # OddsPortal 选择器
│
└── utils/                       # 工具函数库
    ├── constants/               # 常量定义
    │   ├── TitanIds.js                   # Titan ID 签名
    │   └── ExtractionPatterns.js        # 提取模式
    └── helpers/                 # 工具函数
        ├── EscapeProcessor.js           # 转义处理
        └── BracketMatcher.js            # 括号匹配
```

## 🏗️ 架构分层

### 1. 服务层 (services/)

**SignalRadar.js** - 网络雷达调度中心
- 职责: 流程编排和向后兼容适配
- 依赖: NetworkInterceptor, TextSurgicalExtractor, RadarLogger
- 导出: `SignalRadar` 类

### 2. 解析层 (parsers/)

**TrajectoryParser.js** - 轨迹解析主控制器
- 职责: DOM 数据提取和数据编排
- 依赖: PayoutCalculator, SyncTimestamp
- 导出: `TrajectoryParser`, `PayoutCalculator`, `SyncTimestamp`

### 3. 工具层 (utils/)

**constants/** - 常量定义
- `TitanIds.js` - Titan ID 签名
- `ExtractionPatterns.js` - 提取模式

**helpers/** - 工具函数
- `EscapeProcessor.js` - 转义字符处理
- `BracketMatcher.js` - 括号匹配

## 📊 重构统计

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| **SignalRadar.js** | 944 行 | 目标 ~300 行 | ↓ 63% |
| **TrajectoryParser.js** | 810 行 | 目标 ~350 行 | ↓ 57% |
| **最大文件行数** | 944 行 | ~350 行 | 达标 ✅ |
| **模块数量** | 3 个巨型文件 | 20+ 小模块 | 解耦 ✅ |

## 🔗 依赖关系

```
SignalRadar.js
    ├── NetworkInterceptor.js
    ├── TextSurgicalExtractor.js
    │       ├── ExtractionPatterns.js
    │       ├── BracketMatcher.js
    │       └── EscapeProcessor.js
    └── RadarLogger.js

TrajectoryParser.js
    ├── PayoutCalculator.js
    ├── SyncTimestamp.js
    └── EngineConfig.js
```

## 🧪 测试

```bash
# 单元测试
npm test -- tests/engines/

# 覆盖率测试
npm run test:coverage

# 集成测试
npm test -- tests/integration/
```

## 📚 使用示例

```javascript
// 使用 SignalRadar
const { SignalRadar } = require('./services/SignalRadar');
const radar = new SignalRadar(page, { logLevel: 'info' });
await radar.enableForceIntercept();

// 使用 TrajectoryParser
const { TrajectoryParser, PayoutCalculator } = require('./parsers');
const parser = new TrajectoryParser();
const payout = PayoutCalculator.calculate(2.0, 3.5, 4.0);

// 使用工具函数
const { SyncTimestamp, alignTimestamp } = require('./parsers/temporal/SyncTimestamp');
const timestamp = new SyncTimestamp();
const iso = timestamp.parse('24 Jan, 10:00');
```

## 🚀 版本历史

- **V168.002** (2026-02-02) - 模块化重构，拆分巨型文件
- **V167.000** (2026-02-02) - Payout 逻辑统一
- **V166.000** (2026-02-02) - 语义提取版本
- **V164.1** (2026-01-31) - 强力拦截版本
