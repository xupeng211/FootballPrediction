# NetworkShield - V1.1.0

## 工业级跨语言代理管理组件

> **[Genesis.Standardization]** Production-Grade Proxy Management System
>
> 统一管理 Python (L2) 和 Node.js (L3) 的网络出口，深度对接 Windows 端的 Clash Verge (22个节点)。

---

## 目录

- [快速开始](#快速开始)
- [系统架构](#系统架构)
- [核心特性](#核心特性)
- [环境依赖](#环境依赖)
- [使用指南](#使用指南)
- [配置说明](#配置说明)
- [错误码](#错误码)
- [测试](#测试)
- [故障排除](#故障排除)

---

## 快速开始

### 安装依赖

```bash
# Node.js 核心模块（无外部依赖）
# NetworkShield 完全基于 Node.js 内置模块实现
```

### 基本使用

```javascript
const { NetworkShield } = require('./src/infrastructure/network/NetworkShield');

// 1. 创建实例
const shield = new NetworkShield({
    proxyHost: '172.25.16.1',
    portRange: { start: 7891, end: 7912 },
    logLevel: 'info'
});

// 2. 初始化
await shield.initialize();

// 3. 获取代理
const proxy = await shield.getNextHealthyProxy('session-123');
console.log(`Using proxy: ${proxy.url}`);

// 4. 使用代理完成请求
// ... your network request here ...

// 5. 标记成功/失败
await shield.markProxySuccess(proxy.port, 150);

// 6. 释放会话
shield.releaseSession('session-123');
```

### Python 适配器

```python
from src.infrastructure.network.network_shield import NetworkShieldAdapter

# 创建适配器
shield = NetworkShieldAdapter(
    proxy_host='172.25.16.1',
    port_range=(7891, 7912),
    log_level='info'
)

# 初始化
await shield.initialize()

# 获取代理
proxy = await shield.get_next_healthy_proxy('session-123')
print(f"Using proxy: {proxy['url']}")

# 释放会话
shield.release_session('session-123')
```

---

## 系统架构

### 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NetworkShield V1.1.0                                  │
│                        中央代理管理编排层                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    LRUSessionManager                                  │  │
│  │                    LRU 会话管理器                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  LRUCache (Doubly-Linked List)                                 │  │  │
│  │  │  • Max Size: 500                                                │  │  │
│  │  │  • TTL: 30 minutes                                              │  │  │
│  │  │  • Memory Pressure Detection                                    │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                     ↓                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    RegistryManager                                     │  │
│  │                    中央注册表管理器                                     │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  AbstractFileSystem (DI Layer)                                  │  │  │
│  │  │  ├── NodeFileSystem (Production)                                │  │  │
│  │  │  └── MemoryFileSystem (Testing)                                 │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │  • File Locking (Atomic)                                             │  │
│  │  • Cache TTL: 1 second                                               │  │
│  │  • Auto Backup/Restore                                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                     ↓                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    CircuitBreakerRegistry                             │  │
│  │                    熔断器注册表                                         │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  CircuitBreaker (Per-Port)                                      │  │  │
│  │  │  States: CLOSED → OPEN → HALF_OPEN → CLOSED                    │  │  │
│  │  │  Trigger: 2 consecutive failures                                │  │  │
│  │  │  Cooldown: 15 minutes                                           │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                     ↓                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    BatchHealthChecker                                 │  │
│  │                    批量健康检查器                                      │  │
│  │  • Concurrent HEAD requests (oddsportal.com)                        │  │
│  │  • Response time measurement                                         │  │
│  │  • IP address detection                                              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    active_registry.json (持久化存储)                          │
│                                                                             │
│  {                                                                          │
│    "registry_id": "REG-CLASH-22",                                           │
│    "version": "V1.1.0",                                                     │
│    "nodes": [                                                               │
│      { "id": "NODE-7891", "port": 7891, "status": "active", ... },         │
│      ...                                                                    │
│    ]                                                                        │
│  }                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    跨语言同步层                                              │
│                                                                             │
│  ┌─────────────────────┐         ┌─────────────────────┐                    │
│  │   Node.js (L3)      │         │   Python (L2)       │                    │
│  │   QuantHarvester    │         │   proxy_manager.py   │                    │
│  │                     │         │                     │                    │
│  │   NetworkShield.js  │◄───────►│   network_shield.py  │                    │
│  └─────────────────────┘         └─────────────────────┘                    │
│          ↑                                ↑                                  │
│          └────────────────────────────────┘                                  │
│                    File Lock + Registry Sync                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  会话绑定流程 (Session Binding)                                             │
│                                                                             │
│  1. Browser Session 创建                                                   │
│     ↓                                                                       │
│  2. NetworkShield.getNextHealthyProxy(sessionId)                           │
│     ↓                                                                       │
│  3. LRUSessionManager.createSession(port)                                  │
│     ├─ 检查端口是否已占用                                                   │
│     ├─ 创建 ProxySession 对象                                              │
│     └─ 添加到 LRU 缓存                                                     │
│     ↓                                                                       │
│  4. 返回 { sessionId, port, url, health_score }                            │
│     ↓                                                                       │
│  5. Browser 使用该端口发起请求                                              │
│     ↓                                                                       │
│  6. 请求完成后调用 markProxySuccess(port) 或 markProxyFailed(port)         │
│     ↓                                                                       │
│  7. 会话关闭时调用 releaseSession(sessionId)                                │
│     └─ 端口被释放，可供其他会话使用                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 核心特性

### 1. 中央注册制 (Central Registry Management)

- **单一数据源**: `active_registry.json` 作为跨语言状态同步的权威来源
- **原子更新**: 基于文件锁的原子写入，避免竞态条件
- **自动备份**: 写入前自动备份，支持故障恢复
- **缓存优化**: 1秒 TTL 缓存，减少磁盘 I/O

### 2. 会话绑定 (Session Binding)

- **一对一绑定**: 一个浏览器会话 = 一个干净 IP
- **LRU 淘汰**: 超过 500 个会话自动淘汰最久未使用的
- **TTL 过期**: 30 分钟未活动的会话自动释放
- **内存保护**: 堆内存超过 100MB 自动淘汰 10% 会话

### 3. 自适应健康检查 (Adaptive Health Checking)

- **并发测试**: 启动时并发测试所有 22 个节点
- **健康分数**: 基于响应时间、成功率的动态评分 (0-100)
- **自动调度**: 每 60 秒自动执行健康检查

### 4. 智能轮换 (Smart Rotation)

- **健康优先**: 优先分配健康分数最高的节点
- **端口去重**: 确保同一会话始终使用同一端口
- **负载均衡**: 多个会话均匀分布到不同端口

### 5. 自愈熔断 (Self-Healing Circuit Breaker)

- **失败阈值**: 连续 2 次失败自动熔断
- **冷却期**: 15 分钟冷却期，避免持续使用故障节点
- **半开状态**: 冷却期后允许测试请求
- **自动恢复**: 测试成功自动恢复到正常状态

---

## 环境依赖

### Windows Clash Verge 配置

NetworkShield 依赖 Clash Verge 的 HTTP 代理端口映射：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Clash Verge 端口映射 (Windows 宿主机)                                      │
│                                                                             │
│  HTTP Proxy:  172.25.16.1:7890  (Mixed Port)                               │
│                                                                             │
│  代理节点端口映射 (7891-7912):                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Port   │  Group              │  Rule                               │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │  7891   │  PROXY*             │  Default                            │  │
│  │  7892   │  PROXY*             │  Default                            │  │
│  │  ...    │  ...                │  ...                                │  │
│  │  7912   │  PROXY*             │  Default                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  * PROXY 组包含所有可用代理节点，Clash 自动负载均衡                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 网络配置

| 环境 | 代理主机 | 配置方式 |
|------|----------|----------|
| **WSL2** | `172.25.16.1` | 自动探测宿主机 IP |
| **Docker** | `host.docker.internal` | Docker 内置 DNS |
| **本地** | `localhost` | 直接连接 |

### 环境变量

```bash
# 禁用代理（直连模式）
export PROXY_ENABLED=false

# 自定义注册表路径
export NETWORK_SHIELD_REGISTRY_PATH=/path/to/registry.json

# 日志级别
export NETWORK_SHIELD_LOG_LEVEL=debug
```

---

## 使用指南

### Node.js 完整示例

```javascript
const { NetworkShield, getNetworkShield } = require('./NetworkShield');
const axios = require('axios');

async function main() {
    // 1. 获取单例
    const shield = getNetworkShield({
        proxyHost: '172.25.16.1',
        portRange: { start: 7891, end: 7912 },
        logLevel: 'info',
        enabled: true
    });

    // 2. 初始化
    const status = await shield.initialize();
    console.log('NetworkShield initialized:', status);

    // 3. 创建会话并获取代理
    const sessionId = `session-${Date.now()}`;
    const proxy = await shield.getNextHealthyProxy(sessionId);

    console.log(`Assigned proxy: ${proxy.url} (Health: ${proxy.health_score})`);

    try {
        // 4. 使用代理发起请求
        const response = await axios.get('https://api.example.com/data', {
            proxy: {
                host: shield.options.proxyHost,
                port: proxy.port
            },
            timeout: 10000
        });

        // 5. 标记成功
        await shield.markProxySuccess(proxy.port, 150);
        console.log('Request successful');

    } catch (error) {
        // 6. 标记失败
        await shield.markProxyFailed(proxy.port, error.message);
        console.error('Request failed:', error.message);
    } finally {
        // 7. 释放会话
        shield.releaseSession(sessionId);
    }

    // 8. 获取状态
    const finalStatus = shield.getStatus();
    console.log('Final status:', finalStatus);
}

main().catch(console.error);
```

### Python 完整示例

```python
import asyncio
import aiohttp
from src.infrastructure.network.network_shield import NetworkShieldAdapter

async def main():
    # 1. 创建适配器
    shield = NetworkShieldAdapter(
        proxy_host='172.25.16.1',
        port_range=(7891, 7912),
        log_level='info'
    )

    # 2. 初始化
    status = await shield.initialize()
    print(f"NetworkShield initialized: {status}")

    # 3. 创建会话并获取代理
    session_id = f"session-{int(time.time())}"
    proxy = await shield.get_next_healthy_proxy(session_id)

    print(f"Assigned proxy: {proxy['url']} (Health: {proxy['health_score']})")

    try:
        # 4. 使用代理发起请求
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.example.com/data',
                proxy=proxy['url'],
                timeout=10
            ) as response:
                data = await response.json()

                # 5. 标记成功
                await shield.mark_proxy_success(proxy['port'], 150)
                print('Request successful')

    except Exception as error:
        # 6. 标记失败
        await shield.mark_proxy_failed(proxy['port'], str(error))
        print(f'Request failed: {error}')

    finally:
        # 7. 释放会话
        shield.release_session(session_id)

    # 8. 获取状态
    final_status = shield.get_status()
    print(f'Final status: {final_status}')

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 配置说明

### 完整配置选项

```javascript
const shield = new NetworkShield({
    // 代理配置
    proxyHost: '172.25.16.1',           // 代理主机
    portRange: {                         // 端口范围
        start: 7891,
        end: 7912
    },
    protocol: 'http',                    // 代理协议

    // 健康检查
    healthCheckInterval: 60000,          // 健康检查间隔（毫秒）
    cooldownMinutes: 15,                 // 冷却时间（分钟）
    maxConsecutiveFailures: 2,           // 最大连续失败次数

    // 会话管理
    sessionTimeoutMinutes: 30,           // 会话超时时间（分钟）
    lruMaxSize: 500,                     // LRU 最大容量
    maxSessions: 1000,                   // 最大会话数

    // 日志
    logLevel: 'info',                    // 日志级别

    // 启用/禁用
    enabled: true,                       // 是否启用代理

    // 测试模式
    useMemoryFS: false                   // 是否使用内存文件系统
});
```

### 注册表文件结构

```json
{
  "registry_id": "REG-CLASH-22",
  "version": "V1.1.0",
  "last_updated": "2026-02-03T12:00:00.000Z",
  "registry_config": {
    "proxy_host": "172.25.16.1",
    "port_range": { "start": 7891, "end": 7912 },
    "protocol": "http",
    "cooldown_minutes": 15,
    "max_consecutive_failures": 2
  },
  "nodes": [
    {
      "id": "NODE-7891",
      "port": 7891,
      "status": "active",
      "health_score": 100,
      "consecutive_failures": 0,
      "last_check": "2026-02-03T12:00:00.000Z",
      "last_success": "2026-02-03T12:00:00.000Z",
      "last_failure": null,
      "cooldown_until": null,
      "ip_address": "192.168.1.100",
      "avg_latency_ms": 150,
      "total_requests": 1000,
      "successful_requests": 980,
      "metadata": {
        "provider": "clash_verge",
        "region": "default"
      }
    }
  ],
  "active_sessions": {
    "next_session_id": 1,
    "sessions": []
  },
  "statistics": {
    "total_nodes": 22,
    "active_nodes": 22,
    "cooled_nodes": 0,
    "total_requests": 22000,
    "successful_requests": 21560,
    "failed_requests": 440,
    "avg_health_score": 98.5
  }
}
```

---

## 错误码

### 标准化错误

NetworkShield 使用 `NetworkShieldError` 统一错误处理：

```javascript
const {
    NetworkShieldError,
    authFail,           // NS_AUTH_FAIL
    proxyDead,          // NS_PROXY_DEAD
    registryLocked,     // NS_REGISTRY_LOCKED
    noProxyAvailable,   // NS_NO_PROXY_AVAILABLE
    sessionExpired,     // NS_SESSION_EXPIRED
    filesystemError,    // NS_FILESYSTEM_ERROR
    invalidConfig       // NS_INVALID_CONFIG
} = require('./core/NetworkShieldError');
```

### 错误码列表

| 错误码 | 名称 | 严重级别 | 可重试 | 说明 |
|--------|------|----------|--------|------|
| `NS_AUTH_FAIL` | 认证失败 | HIGH | 否 | 代理认证失败 |
| `NS_PROXY_DEAD` | 代理失效 | CRITICAL | 是 | 代理节点无响应 |
| `NS_REGISTRY_LOCKED` | 注册表锁定 | MEDIUM | 是 | 文件锁获取超时 |
| `NS_NO_PROXY_AVAILABLE` | 无可用代理 | HIGH | 否 | 所有节点均不可用 |
| `NS_SESSION_EXPIRED` | 会话过期 | LOW | 否 | 会话已过期 |
| `NS_FILESYSTEM_ERROR` | 文件系统错误 | CRITICAL | 否 | 磁盘操作失败 |
| `NS_INVALID_CONFIG` | 配置无效 | HIGH | 否 | 配置参数错误 |
| `NS_CIRCUIT_OPEN` | 熔断器打开 | MEDIUM | 是 | 节点熔断中 |

### 错误处理示例

```javascript
try {
    const proxy = await shield.getNextHealthyProxy(sessionId);
} catch (error) {
    if (error.code === 'NS_NO_PROXY_AVAILABLE') {
        console.error('All proxies are down:', error.context);
        // 触发告警或重试逻辑
    } else if (error.retryable) {
        console.warn('Retryable error:', error.message);
        // 延迟重试
    } else {
        console.error('Fatal error:', error.message);
        // 终止操作
    }
}
```

---

## 测试

### 运行测试

```bash
# 单元测试
npm test src/infrastructure/network/tests/CircuitBreaker.test.js

# 集成测试
npm test src/infrastructure/network/tests/integration.test.js

# 所有测试
npm test src/infrastructure/network/tests/
```

### 测试覆盖率

```bash
# 生成覆盖率报告
npm test -- --coverage
```

---

## 故障排除

### 常见问题

**Q: 所有节点显示 "cooled" 状态**

A: 检查 `cooldownMinutes` 配置，可能需要等待冷却期结束。使用 `resetAllNodes()` 手动重置。

**Q: 会话数量持续增长**

A: 确保 `releaseSession()` 被正确调用。检查 `maxSessions` 和 `lruMaxSize` 配置。

**Q: 文件锁超时**

A: 检查是否有其他进程持有锁。删除 `.registry.lock` 文件并重试。

**Q: 健康检查失败**

A: 验证 Clash Verge 是否正常运行，确保 `proxyHost` 可访问。

---

## 版本历史

### V1.1.0 (2026-02-03)

- 依赖注入：支持 AbstractFileSystem 和 LRUSessionManager
- 错误码标准化：使用 NetworkShieldError
- RadarLogger 集成：统一的日志标准
- 改进的并发锁：基于文件系统的原子锁
- LRU 会话管理：解决长时间运行的内存泄漏

### V1.0.0 (2026-02-01)

- 初始版本
- 中央注册表管理
- 会话绑定机制
- 自适应健康检查
- 自愈熔断器

---

## 许可证

MIT License

---

**作者**: [Genesis.Standardization]
**最后更新**: 2026-02-03
**版本**: V1.1.0
