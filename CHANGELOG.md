# 更新日志 (Changelog)

所有重要的更改都将记录在此文件中。

---

## [V173.0.0] - 2026-02-28 - Sentinel Edition

### 🚀 重大突破 (Breaking Changes)

- **网页渗透模式 (Web Infiltration Mode)**: 绕过 FotMob API 层的 Turnstile 拦截，直接从网页 `__NEXT_DATA__` 提取数据
  - 新增 `_extractNextData()` 方法提取 Next.js 数据
  - 新增 `_transformNextDataToApiFormat()` 转换数据格式
  - 新增 `_simulateHumanBehavior()` 模拟真人行为（滚动、阅读延时）
  - 新增 `_checkCloudflareBlock()` 检测 Cloudflare 拦截页面

### 🛡️ 系统加固 (Security Hardening)

- **preFlightCleanup (自动清道夫)**: 启动前物理清空 Chrome/Chromium 僵尸进程
  - 清理残留的 `chrome-headless` 进程
  - 清理残留的 `harvest_fleet_master` 和 `harvest_worker` 进程
  - 确保每一轮收割都在"洁净室"环境下开始

- **熔断机制优化**: 提高熔断阈值至 10 次，避免过早触发
- **动态 UA 轮换**: 20 个主流 User-Agent 随机切换
- **随机视口尺寸**: 每次创建 Context 时随机选择视口

### 📊 运维升级 (Operations)

- **中央监控大屏 (Dashboard)**:
  - 新增 `npm run watch` 命令启动实时监控
  - 支持 22 个代理端口状态监控
  - 实时显示 Worker 状态、成功/失败计数

- **心跳机制**: 每 10 秒写入 `/app/logs/live_status.json`
  - 包含进度百分比、预估剩余时间
  - Worker 状态快照、代理端口状态

### 🗄️ 数据治理 (Data Governance)

- **任务查询优化**: 简化 SQL 查询，任务加载速度提升 80%
- **质量门禁增强**: 智能错误关键字检查，只检测核心数据区域

### 🔧 配置变更 (Configuration)

- **安全默认值调整**:
  - `MAX_WORKERS`: 5 → 1 (最稳模式)
  - `MIN_DELAY_MS`: 5000 → 10000 (潜行频率)
  - `MAX_DELAY_MS`: 12000 → 15000 (潜行频率)

### 📦 依赖清理 (Dependencies)

- 移除未使用的依赖: `js-yaml`, `playwright-extra`, `puppeteer-extra-plugin-stealth`
- 保留核心依赖: `dotenv`, `jsdom`, `p-limit`, `pg`, `playwright`

### 🧪 测试覆盖 (Testing)

- 新增 `tests/v173_core.test.js`: 6 个核心测试用例
  - ID 格式校验测试
  - URL 拼接逻辑测试
  - 配置加载测试
  - 质量门禁验证测试
  - 代理端口映射测试
  - 重试逻辑测试

---

## [V172.1.0] - 2026-02-27

### 新增功能

- 装甲群收割器 (Master-Worker 模式)
- 任务重试队列 (质量门禁失败自动回队)
- 指数退避重试策略
- 连接池 100% 释放保障

### 修复

- 修复 `page` 未定义 Bug
- 数据库组件正规化

---

## [V171.2.0] - 2026-02-25

### 新增功能

- L1 Discovery: 自动发现未来 7 天的比赛
- C++ Fuzzy Bridge: RapidFuzz 高性能队名匹配
- L2/L3 Harvest: 多源数据采集 (FotMob + OddsPortal)
- V171 Prediction: 3 模型共识预测
- NetworkShield: 22 节点代理池熔断保护

---

## 版本命名规范

- **主版本号 (Major)**: 架构重大变更
- **次版本号 (Minor)**: 新功能添加
- **修订号 (Patch)**: Bug 修复和小改进

---

**维护者**: V173 Engineering Team
**许可证**: MIT
