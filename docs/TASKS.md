# 上线前优化任务看板

## 核心功能
- [x] 📌 数据采集与模型训练服务集成 ✅ 完成于 2025-09-22
  - 🎯 Blocker
  - 📝 CI/CD 启动后，能自动完成采集 → 清洗 → 模型更新 → 预测

## 测试与质量
- [x] 📌 修复 slow-suite（补充 Alembic migration + 初始数据） ✅ 完成于 2025-09-22
  - 🎯 Blocker
  - 📝 CI 中 slow-suite 100% 通过，首次部署不再缺表
- [x] 📌 覆盖率提升至 ≥ 80%（重点补齐 features、lineage、streaming） ✅ 完成于 2025-09-22
  - 🎯 High
  - 📝 全局覆盖率 ≥ 80%，低覆盖模块 ≥ 70%
- [x] 📌 优化慢测试结构（拆分/减少冗余 deselect） ✅ 完成于 2025-09-23
  - 🎯 Medium
  - 📝 执行时间缩短 ≥ 30%，无无效跳过

## 部署与运维
- [x] 📌 自动迁移链路（容器启动和 CI 中自动执行 Alembic upgrade） ✅ 完成于 2025-09-22
  - 🎯 High
  - 📝 `docker compose up` 可直接运行，CI 不再报缺表
- [x] 📌 回滚机制（不可变标签 + 一键回滚） ✅ 完成于 2025-09-22
  - 🎯 High
  - 📝 能切回上一个稳定版本
- [ ] 📌 外部依赖健康检查（Redis / Kafka / MLflow readiness & liveness）
  - 🎯 Medium
  - 📝 健康检查脚本返回 200/ok，熔断策略生效

## 配置与安全
- [x] 📌 替换 .env 默认弱口令，接入 Secrets 管理 ✅ 完成于 2025-09-22
  - 🎯 Blocker
  - 📝 `.env.example` 不含弱口令，生产部署用 Secrets 注入
- [ ] 📌 加固网络与传输安全（TLS、WAF、安全组）
  - 🎯 Low
  - 📝 部署文档包含 TLS 与安全策略

## CI/CD
- [x] 📌 主干 CI 全绿（修复 lint/失败用例，规范 model_reports.yml 触发条件） ✅ 完成于 2025-09-22
  - 🎯 Blocker
  - 📝 main 分支 push 全绿，模型报表仅手动/定时触发
