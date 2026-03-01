# V174 模块化架构文档

> **版本**: V174.0.0 (Refactor) | **更新日期**: 2026-03-01

---

## 1. 架构概览

V174 采用 **Master-Worker 分布式架构**，将原本 1500+ 行的巨型文件拆分为 12 个独立模块，实现高内聚、低耦合的设计目标。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         harvest_fleet_master.js                             │
│                       (Master 主控 - 薄层入口 ~300 行)                        │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ IPC (fork/send)
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│   Worker 1          │   │   Worker 2          │   │   Worker N          │
│   (harvest_worker)  │   │   (harvest_worker)  │   │   (harvest_worker)  │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

---

## 2. 模块清单 (12 个模块)

### 2.1 IPC 通信层 (`src/core/ipc/`)

| 模块 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **WorkerMessenger** | `WorkerMessenger.js` | Worker → Master 消息发送 | ~80 |
| **MasterGate** | `MasterGate.js` | Master 消息路由与熔断 | ~180 |
| **MessageTypes** | `MessageTypes.js` | 消息类型常量定义 | ~50 |

**依赖关系:**
```
MasterGate ──▶ MessageTypes
WorkerMessenger ──▶ MessageTypes
```

### 2.2 进程管理层 (`src/core/process/`)

| 模块 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **ZombieKiller** | `ZombieKiller.js` | 僵尸进程清理、浏览器强制终止 | ~120 |

**关键函数:**
- `preFlightCleanup()` - 启动前清理
- `forceKillBrowser()` - 强制终止浏览器进程

### 2.3 浏览器管理层 (`src/core/browser/`)

| 模块 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **BrowserManager** | `BrowserManager.js` | 浏览器生命周期管理 | ~150 |
| **StealthInjector** | `StealthInjector.js` | 反检测脚本注入 | ~60 |

**功能:**
- 浏览器启动/关闭
- 代理端口切换
- 页面创建/回收
- 指纹伪装

### 2.4 调度层 (`src/core/scheduler/`)

| 模块 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **TaskPool** | `TaskPool.js` | 任务队列管理、去重、重试 | ~120 |

**核心方法:**
- `loadTasks()` - 从数据库加载待收割任务
- `getNext()` - 获取下一个任务
- `requeue(task)` - 任务重新入队
- `getStats()` - 获取统计信息

### 2.5 网络层 (`src/core/network/`)

| 模块 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **ProxyRegistry** | `ProxyRegistry.js` | 代理池管理、端口分配 | ~100 |

**功能:**
- 22 个代理端口管理 (7890-7911)
- Worker → Port 映射
- 代理健康状态跟踪

### 2.6 UI 层 (`src/core/ui/`)

| 模块 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **Dashboard** | `Dashboard.js` | 终端 UI 渲染、统计展示 | ~150 |

**功能:**
- 实时进度显示
- Worker 状态可视化
- 成功/失败统计

### 2.7 解析器层 (`src/parsers/fotmob/`)

| 模块 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **CloudflareDetector** | `CloudflareDetector.js` | CF 拦截检测 | ~40 |
| **NextDataParser** | `NextDataParser.js` | Next.js 数据提取 | ~80 |
| **XGExtractor** | `XGExtractor.js` | xG/统计数据提取 | ~100 |

**数据流:**
```
Page HTML ──▶ CloudflareDetector ──▶ NextDataParser ──▶ XGExtractor
                     │                      │                  │
                blocked?              apiData            stats
```

### 2.8 数据库模型层 (`src/models/`)

| 模块 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **MatchQueries** | `MatchQueries.js` | 比赛数据 CRUD | ~80 |
| **RawDataQueries** | `RawDataQueries.js` | 原始 JSON 存储 | ~60 |

---

## 3. 消息协议 (IPC Protocol)

### 3.1 消息类型

```javascript
// MessageTypes.js
const MessageTypes = {
    READY: 'READY',               // Worker 就绪
    TASK_START: 'TASK_START',     // 任务开始
    TASK_SUCCESS: 'TASK_SUCCESS', // 任务成功
    TASK_FAILED: 'TASK_FAILED',   // 任务失败
    TASK_RETRY: 'TASK_RETRY',     // 任务重试
    WORKER_CIRCUIT_BREAK: 'WORKER_CIRCUIT_BREAK',  // 熔断
    WORKER_COOL_DOWN: 'WORKER_COOL_DOWN',          // 冷却
    SHUTDOWN: 'SHUTDOWN'          // 关闭信号
};
```

### 3.2 消息流

```
┌─────────┐                              ┌─────────┐
│ Master  │                              │ Worker  │
└────┬────┘                              └────┬────┘
     │ ◀────────── READY ────────────────── │
     │                                      │
     │ ────────── TASK ────────────────────▶│
     │                                      │
     │ ◀───────── TASK_START ────────────── │
     │                                      │
     │ ◀───────── TASK_SUCCESS ──────────── │  (成功)
     │                    或                │
     │ ◀───────── TASK_RETRY ────────────── │  (可重试错误)
     │                    或                │
     │ ◀───────── TASK_FAILED ───────────── │  (最终失败)
     │                                      │
     │ ────────── SHUTDOWN ────────────────▶│
```

---

## 4. 依赖注入设计

V174 采用**构造函数注入**模式，所有依赖通过构造函数传入，便于测试和替换。

### 4.1 WorkerEntry 示例

```javascript
class HarvestWorkerEntry {
    constructor() {
        // 依赖注入
        this.messenger = new WorkerMessenger(WORKER_ID);
        this.browserManager = new BrowserManager({
            workerId: WORKER_ID,
            proxyPort: PROXY_PORT,
            config: FactoryConfig
        });
        this.matchQueries = new MatchQueries(dbClient);
        this.rawDataQueries = new RawDataQueries(dbClient);
    }
}
```

### 4.2 FleetMaster 示例

```javascript
class FleetMaster {
    constructor() {
        this.taskPool = null;  // 延迟初始化
        this.proxyRegistry = new ProxyRegistry({...});
        this.dashboard = null;  // 延迟初始化
        this.masterGate = new MasterGate({...});
    }
}
```

---

## 5. 错误处理与自愈

### 5.1 熔断机制

```
连续失败 5 次 ──▶ MasterGate 触发熔断 ──▶ _recloneWorker()
                                                │
                                          终止旧 Worker
                                                │
                                          分配新代理端口
                                                │
                                          启动新 Worker
```

### 5.2 深度静默 (Cool Down)

```
连续 Cloudflare 失败 3 次 ──▶ WORKER_COOL_DOWN ──▶ 切换代理端口
```

### 5.3 重试策略

```javascript
// 指数退避
const backoffDelay = baseDelay * Math.pow(2, retryCount);
// 最多重试 3 次
if (retryCount >= maxAttempts) {
    messenger.notifyTaskFailed(matchId, error);
}
```

---

## 6. 配置系统

所有魔术数字统一归口到 `config/factory_config.js`:

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `maxWorkers` | 1 | 最大 Worker 数 |
| `minDelayMs` | 10000 | 最小延时 |
| `maxDelayMs` | 15000 | 最大延时 |
| `circuitBreakerThreshold` | 5 | 熔断阈值 |
| `minSizeBytes` | 5000 | 质量门禁 |

---

## 7. 文件结构

```
src/
├── core/                           # 核心基础设施
│   ├── index.js                    # 统一入口
│   ├── ipc/                        # IPC 通信
│   │   ├── index.js
│   │   ├── WorkerMessenger.js
│   │   ├── MasterGate.js
│   │   └── MessageTypes.js
│   ├── process/                    # 进程管理
│   │   ├── index.js
│   │   └── ZombieKiller.js
│   ├── browser/                    # 浏览器管理
│   │   ├── index.js
│   │   ├── BrowserManager.js
│   │   └── StealthInjector.js
│   ├── scheduler/                  # 调度器
│   │   ├── index.js
│   │   └── TaskPool.js
│   ├── network/                    # 网络层
│   │   ├── index.js
│   │   └── ProxyRegistry.js
│   └── ui/                         # UI 层
│       ├── index.js
│       └── Dashboard.js
├── parsers/                        # 数据解析器
│   └── fotmob/
│       ├── index.js
│       ├── CloudflareDetector.js
│       ├── NextDataParser.js
│       └── XGExtractor.js
├── models/                         # 数据库模型
│   ├── index.js
│   ├── MatchQueries.js
│   └── RawDataQueries.js
└── scripts/                        # 业务入口
    └── harvest_worker_entry.js
```

---

## 8. 测试策略

### 8.1 单元测试

每个模块应有独立的单元测试:

```bash
# 测试单个模块
docker exec dev node --test tests/core/ipc/WorkerMessenger.test.js
```

### 8.2 集成测试

测试 Master-Worker 通信:

```bash
# 启动 2 个 Worker 进行 3 分钟测试
MAX_WORKERS=2 npm run harvest
```

---

## 9. 监控与诊断

### 9.1 状态文件

收割过程中写入 `/app/logs/live_status.json`:

```json
{
  "version": "V174.0.0",
  "timestamp": "2026-03-01T10:00:00Z",
  "total": 50,
  "processed": 25,
  "success": 22,
  "failed": 3,
  "activeWorkers": 2
}
```

### 9.2 日志

```bash
# 实时查看日志
tail -f logs/harvest.log
```

---

## 10. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V174.0.0 | 2026-03-01 | 模块化重构，12 个独立模块 |
| V173.0.0 | 2026-02-28 | 装甲群模式，Master-Worker 架构 |
| V172.0.0 | 2026-02-27 | 数据收割引擎封版 |

---

## 11. 贡献指南

1. **单一职责**: 每个模块只做一件事
2. **依赖注入**: 通过构造函数传入依赖
3. **纯函数优先**: 解析器必须是纯函数
4. **无状态**: 模块间不共享可变状态
5. **中文注释**: 所有注释和日志使用中文

---

*文档维护者: Claude AI | 最后更新: 2026-03-01*
