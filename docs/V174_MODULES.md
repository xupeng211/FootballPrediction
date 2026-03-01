# V174 模块架构文档

> **版本**: V174.0.0 | **更新日期**: 2026-03-01

---

## 概述

V174 采用 **Master-Worker 分布式架构**，将原本 1500+ 行的巨型文件拆分为 **12 个独立模块**，实现高内聚、低耦合的设计目标。

---

## 模块清单

### 1. IPC 通信层 (`src/core/ipc/`)

#### 1.1 WorkerMessenger
- **文件**: `WorkerMessenger.js`
- **职责**: Worker → Master 消息发送
- **行数**: ~80 行
- **依赖**: MessageTypes
- **API**:
  ```javascript
  const messenger = new WorkerMessenger(workerId);
  messenger.notifyReady();
  messenger.notifyTaskStart(matchId);
  messenger.notifyTaskSuccess(matchId, { responseTime, rawSize });
  messenger.notifyTaskFailed(matchId, error);
  ```

#### 1.2 MasterGate
- **文件**: `MasterGate.js`
- **职责**: Master 消息路由与熔断
- **行数**: ~180 行
- **依赖**: MessageTypes
- **API**:
  ```javascript
  const gate = new MasterGate({ circuitBreakerThreshold: 5 });
  gate.on(MessageTypes.READY, (workerId) => { ... });
  gate.handle(workerId, message);
  ```

#### 1.3 MessageTypes
- **文件**: `MessageTypes.js`
- **职责**: 消息类型常量定义
- **行数**: ~50 行
- **常量**:
  - `READY` - Worker 就绪
  - `TASK_START` - 任务开始
  - `TASK_SUCCESS` - 任务成功
  - `TASK_FAILED` - 任务失败
  - `TASK_RETRY` - 任务重试
  - `WORKER_CIRCUIT_BREAK` - 熔断
  - `WORKER_COOL_DOWN` - 冷却

---

### 2. 进程管理层 (`src/core/process/`)

#### 2.1 ZombieKiller
- **文件**: `ZombieKiller.js`
- **职责**: 僵尸进程清理、浏览器强制终止
- **行数**: ~120 行
- **API**:
  ```javascript
  preFlightCleanup(workerId);  // 启动前清理
  forceKillBrowser(workerId);  // 强制终止浏览器
  ```

---

### 3. 浏览器管理层 (`src/core/browser/`)

#### 3.1 BrowserManager
- **文件**: `BrowserManager.js`
- **职责**: 浏览器生命周期管理
- **行数**: ~150 行
- **功能**:
  - 浏览器启动/关闭
  - 代理端口切换
  - 页面创建/回收
  - 指纹伪装
- **API**:
  ```javascript
  const manager = new BrowserManager({ workerId, proxyPort, headless });
  await manager.ensureBrowser();
  const page = await manager.newPage();
  await manager.switchProxyPort(newPort);
  await manager.safeClose();
  ```

#### 3.2 StealthInjector
- **文件**: `StealthInjector.js`
- **职责**: 反检测脚本注入
- **行数**: ~60 行
- **功能**:
  - 隐藏 webdriver 属性
  - 修改 navigator 属性
  - 注入 stealth 脚本

---

### 4. 调度层 (`src/core/scheduler/`)

#### 4.1 TaskPool
- **文件**: `TaskPool.js`
- **职责**: 任务队列管理、去重、重试
- **行数**: ~120 行
- **API**:
  ```javascript
  const pool = new TaskPool(dbClient, { minSizeBytes: 5000 });
  await pool.loadTasks();
  const task = pool.getNext();
  pool.requeue(task, backoffDelay);
  pool.markCompleted(matchId);
  ```

---

### 5. 网络层 (`src/core/network/`)

#### 5.1 ProxyRegistry
- **文件**: `ProxyRegistry.js`
- **职责**: 代理池管理、端口分配
- **行数**: ~100 行
- **功能**:
  - 22 个代理端口管理 (7890-7911)
  - Worker → Port 映射
  - 代理健康状态跟踪
- **API**:
  ```javascript
  const registry = new ProxyRegistry({ ports: [7890..7911], host: '172.25.16.1' });
  const port = registry.assign(workerId);
  registry.release(workerId);
  registry.markUnhealthy(port, reason);
  ```

---

### 6. UI 层 (`src/core/ui/`)

#### 6.1 Dashboard
- **文件**: `Dashboard.js`
- **职责**: 终端 UI 渲染、统计展示
- **行数**: ~150 行
- **功能**:
  - 实时进度显示
  - Worker 状态可视化
  - 成功/失败统计
- **API**:
  ```javascript
  const dashboard = new Dashboard({ total: 100, title: '收割器' });
  dashboard.updateWorker(workerId, 'RUNNING', { currentMatch: matchId });
  dashboard.recordResult(true);  // 成功
  dashboard.summary();           // 打印总结
  ```

---

### 7. 解析器层 (`src/parsers/fotmob/`)

#### 7.1 CloudflareDetector
- **文件**: `CloudflareDetector.js`
- **职责**: CF 拦截检测
- **行数**: ~40 行
- **API**:
  ```javascript
  const result = await detectFromPage(page);
  if (result.blocked) { /* CF 拦截 */ }
  ```

#### 7.2 NextDataParser
- **文件**: `NextDataParser.js`
- **职责**: Next.js 数据提取
- **行数**: ~80 行
- **API**:
  ```javascript
  const result = await extractAndTransform(page, externalId);
  if (result.success) { const apiData = result.data; }
  ```

#### 7.3 XGExtractor
- **文件**: `XGExtractor.js`
- **职责**: xG/统计数据提取
- **行数**: ~100 行
- **API**:
  ```javascript
  const stats = extractAllStats(apiData);
  // { xg_home, xg_away, shots_home, shots_away, ... }
  ```

---

### 8. 数据库模型层 (`src/models/`)

#### 8.1 MatchQueries
- **文件**: `MatchQueries.js`
- **职责**: 比赛数据 CRUD
- **行数**: ~80 行
- **API**:
  ```javascript
  const queries = new MatchQueries(dbClient);
  await queries.updateStats(matchId, stats);
  ```

#### 8.2 RawDataQueries
- **文件**: `RawDataQueries.js`
- **职责**: 原始 JSON 存储
- **行数**: ~60 行
- **API**:
  ```javascript
  const queries = new RawDataQueries(dbClient);
  await queries.storeRawJson(matchId, apiData);
  ```

---

## 模块依赖关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         harvest_fleet_master.js                             │
│                       (Master 主控 - 薄层入口)                               │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│   TaskPool    │           │  ProxyRegistry│           │  MasterGate   │
│  (scheduler)  │           │   (network)   │           │     (ipc)     │
└───────────────┘           └───────────────┘           └───────────────┘
        │                             │                             │
        │                             ▼                             │
        │                   ┌───────────────┐                       │
        │                   │   Dashboard   │                       │
        │                   │      (ui)     │                       │
        │                   └───────────────┘                       │
        │                                                             │
        └─────────────────────────────────────────────────────────────┘
                                      │ IPC (fork/send)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          harvest_worker.js                                   │
│                        (Worker 薄层入口)                                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
        ┌───────────┬─────────────────┼─────────────────┬───────────┐
        ▼           ▼                 ▼                 ▼           ▼
┌───────────┐ ┌───────────┐   ┌───────────┐   ┌───────────┐ ┌───────────┐
│WorkerMessenger│ │BrowserManager│   │CloudflareDetector│ │NextDataParser│ │MatchQueries│
│   (ipc)   │ │ (browser) │   │ (parsers) │   │ (parsers) │ │  (models) │
└───────────┘ └───────────┘   └───────────┘   └───────────┘ └───────────┘
        │           │                 │                 │           │
        ▼           ▼                 └────────┬────────┘           ▼
┌───────────┐ ┌───────────┐                    ▼              ┌───────────┐
│ZombieKiller│ │StealthInjector│          ┌───────────┐       │RawDataQueries│
│ (process) │ │ (browser) │          │XGExtractor│       │  (models) │
└───────────┘ └───────────┘          └───────────┘       └───────────┘
```

---

## 消息协议

### Worker → Master

| 消息类型 | 方向 | 说明 |
|----------|------|------|
| `READY` | W → M | Worker 已就绪 |
| `TASK_START` | W → M | 任务开始处理 |
| `TASK_SUCCESS` | W → M | 任务成功完成 |
| `TASK_FAILED` | W → M | 任务最终失败 |
| `TASK_RETRY` | W → M | 任务请求重试 |
| `WORKER_COOL_DOWN` | W → M | Worker 进入冷却 |

### Master → Worker

| 消息类型 | 方向 | 说明 |
|----------|------|------|
| `TASK` | M → W | 分配新任务 |
| `SHUTDOWN` | M → W | 关闭信号 |

---

## 配置系统

所有模块配置通过 `config/factory_config.js` 统一管理：

```javascript
const FactoryConfig = require('./config/factory_config');

// 延时配置
FactoryConfig.TIMING.minDelayMs  // 最小延时
FactoryConfig.TIMING.maxDelayMs  // 最大延时

// 代理配置
FactoryConfig.PROXY_CONFIG.ports  // 端口池
FactoryConfig.PROXY_CONFIG.getServer(port)  // 代理地址

// 重试配置
FactoryConfig.RETRY.maxAttempts  // 最大重试次数
FactoryConfig.RETRY.isRetryable(errorType)  // 是否可重试
```

---

## 错误处理

### 熔断机制
```
连续失败 5 次 → MasterGate 触发熔断 → _recloneWorker()
```

### 深度静默 (Cool Down)
```
连续 Cloudflare 失败 3 次 → WORKER_COOL_DOWN → 切换代理端口
```

---

*文档维护者: V174 Engineering Team | 最后更新: 2026-03-01*
