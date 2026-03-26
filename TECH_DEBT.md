# 技术债台账 (Tech Debt Register)

本文档登记已确认、可量化、且已获发布决策接受的工程技术债。

---

## [P1] `AbstractHarvester.js` 上帝类膨胀

- 状态: 已登记，允许随 V11.0 合入主干
- 发现时间: 2026-03-26
- 影响范围: `src/infrastructure/harvesters/base/AbstractHarvester.js`
- 当前规模: 当前工作树实测 1026 行，已超过单类可维护阈值
- 风险等级: P1

### 问题描述

`AbstractHarvester.js` 当前同时承担了以下职责：

- 网络请求编排与页面访问
- 错误分类、重试与冷却
- 会话刷新与 AutoAuth 触发
- Context 池管理与浏览器行为模拟
- 文件读写与 Cookie 状态加载
- 统计、报告与调度辅助逻辑

这已经形成典型的“上帝类”结构，带来以下问题：

- 单文件认知负担过高，回归验证成本持续上升
- 测试需要构造大量跨职责 mock，导致历史用例易漂移
- 小修复容易引发跨域副作用，放大发布风险
- 后续 L2/V11/V12 演进会继续把横切逻辑堆进同一抽象层

### 已接受的发布决策

为避免阻塞德甲 25/26 赛季全量收割，本次 V11.0 发布接受该技术债，先完成主干合并与生产交付，不在当前窗口内做高风险结构性拆分。

### 建议重构方向

建议在 V12.0 或本轮全量收割完成后启动专项重构，至少拆出以下边界：

- `HarvesterRetryService`: 错误分类、退避、冷却、重试策略
- `HarvesterSessionService`: AutoAuth、Session 热刷新、Cookie 装载
- `HarvesterContextPool`: Context 生命周期、LRU 淘汰、端口切换
- `HarvesterIOService`: 文件落盘、状态读取、浏览器状态持久化
- `HarvesterBehaviorMixin` 或独立 `BrowserBehaviorService`: Stealth 注入、鼠标移动、首页预热

### 验收标准

- `AbstractHarvester.js` 压缩到单一抽象职责，目标小于 500 行
- 错误重试、会话管理、IO、行为模拟均有独立单测入口
- 旧测试不再依赖注入私有方法 wrapper 维持兼容
- 新组件边界写入 ADR 或对应架构文档

### 计划窗口

- 目标版本: V12.0 或德甲全量收割完成后的第一个重构窗口
- 优先级说明: 高于常规清理，低于生产故障修复与数据链路阻断项
