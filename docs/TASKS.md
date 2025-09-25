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
- [x] 📌 外部依赖健康检查（Redis / Kafka / MLflow readiness & liveness） ✅ 完成于 2025-09-23
  - 🎯 Medium
  - 📝 健康检查脚本返回 200/ok，熔断策略生效

## 配置与安全
- [x] 📌 替换 .env 默认弱口令，接入 Secrets 管理 ✅ 完成于 2025-09-22
  - 🎯 Blocker
  - 📝 `.env.example` 不含弱口令，生产部署用 Secrets 注入
- [x] 📌 加固网络与传输安全（TLS、WAF、安全组） ✅ 完成于 2025-09-23
  - 🎯 Low
  - 📝 部署文档包含 TLS 与安全策略

## CI/CD
- [x] 📌 主干 CI 全绿（修复 lint/失败用例，规范 model_reports.yml 触发条件） ✅ 完成于 2025-09-22
  - 🎯 Blocker
  - 📝 main 分支 push 全绿，模型报表仅手动/定时触发

## 上线前最终动作（待执行）

- [x] 📌 修复 CI/CD Docker pull 问题 ✅ 完成于 2025-09-23
  - 🎯 Blocker
  - 📝 main 分支流水线全绿，不再卡镜像拉取

- [ ] 📌 执行 Staging 环境验证 (72h)
  - 🎯 High
  - 📝 按照 docs/STAGING_VALIDATION.md，完成三阶段验证并输出报告

- [ ] 📌 数据库备份恢复测试
  - 🎯 High
  - 📝 scripts/db_backup.sh 脚本运行正常，恢复数据一致性验证通过

- [ ] 📌 监控验证
  - 🎯 Medium
  - 📝 Prometheus 指标可采集，Grafana 仪表盘展示正常，AlertManager 能触发告警

## 🚀 Phase 5 - 覆盖率提升 + 生产部署与监控优化（2025-09-25 完成）

### 📋 任务 1：覆盖率提升专项
- [x] **分析低覆盖率模块** - 识别 src/services/*, src/utils/*, src/lineage/* 中 <50% 覆盖率的模块
  - 🎯 High
  - 📝 生成模块覆盖率分析报告，确定优先补测顺序，发现18个模块需要补测
- [x] **补齐 src/services/* 模块测试** - 每个文件创建独立测试文件，确保 ≥60% 覆盖率
  - 🎯 High
  - 📝 测试文件：`tests/unit/services/test_<文件名>_phase5.py`
- [x] **补齐 src/utils/* 模块测试** - 每个文件创建独立测试文件，确保 ≥60% 覆盖率
  - 🎯 High
  - 📝 测试文件：`tests/unit/utils/test_<文件名>_phase5.py`
- [x] **补齐 src/lineage/* 模块测试** - 每个文件创建独立测试文件，确保 ≥60% 覆盖率
  - 🎯 High
  - 📝 测试文件：`tests/unit/lineage/test_<文件名>_phase5.py`
- [x] **验证覆盖率目标** - 整体覆盖率 ≥70%，核心模块 ≥60%
  - 🎯 High
  - 📝 运行完整测试套件，生成覆盖率报告，当前覆盖率：77.74%

### 📋 任务 2：生产部署准备
- [x] **创建生产部署指南** - `docs/DEPLOYMENT_GUIDE.md`
  - 🎯 High
  - 📝 包含 Docker Compose 和 Kubernetes 部署方案，环境变量配置，回滚策略
- [ ] **验证 staging 环境部署** - 确保一键部署流程可用
  - 🎯 High
  - 📝 staging 环境部署测试通过，文档验证完成

### 📋 任务 3：监控与告警优化
- [ ] **增强监控体系** - 扩展 Prometheus + Grafana + AlertManager
  - 🎯 Medium
  - 📝 增加业务指标（预测准确率、请求成功率、响应时间）
- [ ] **创建 Grafana 仪表盘配置** - `configs/grafana_dashboards/phase5.json`
  - 🎯 Medium
  - 📝 包含业务指标和系统指标的完整仪表盘
- [ ] **配置告警规则** - 设置阈值和通知机制
  - 🎯 Medium
  - 📝 API 错误率 >1% → P1告警，预测准确率 <70% → P1告警

### 📋 任务 4：文档更新
- [x] **更新 docs/TASKS.md** - 标记 Phase 5 任务进度
  - 🎯 Low
- [x] **更新 docs/COVERAGE_PROGRESS.md** - 记录 Phase 5 覆盖率提升情况
  - 🎯 Low
- [x] **更新 docs/DEPLOYMENT_GUIDE.md** - 完成生产部署文档
  - 🎯 Low

### 🎯 Phase 5 最终验收标准
- [x] 覆盖率 ≥70%，核心模块 ≥60% (当前: 77.74%)
- [ ] 生产部署文档完整且验证通过
- [ ] 监控与告警体系可用
- [x] CI/CD 流程全绿

## 🚀 Phase 6 - 数据库迁移修复 + 集成测试优化（2025-09-25 完成）

### 📋 任务 1：数据库迁移修复
- [x] **修复性能优化迁移的外键约束问题** - 解决分区表与外键约束冲突
  - 🎯 High
  - 📝 修复 `d6d814cc1078_database_performance_optimization_.py` 中的外键约束问题
- [x] **创建迁移验证脚本** - `scripts/verify_migrations.sh`
  - 🎯 High
  - 📝 提供完整的数据库迁移验证流程，支持干净环境迁移

### 📋 任务 2：集成测试优化
- [x] **分析集成测试失败问题** - 解决依赖外部服务的问题
  - 🎯 High
  - 📝 识别并修复数据库迁移依赖导致的测试跳过问题
- [x] **优化外部依赖** - 创建统一的外部依赖Mock框架
  - 🎯 High
  - 📝 `tests/external_mocks.py` 提供Redis、MLflow、Kafka、Prometheus等Mock

### 📋 任务 3：文档和工具完善
- [x] **更新 TASKS.md** - 标记 Phase 6 完成状态
  - 🎯 Medium
  - 📝 记录所有任务完成情况
- [x] **更新 COVERAGE_PROGRESS.md** - 记录最新覆盖率状态
  - 🎯 Medium
  - 📝 当前覆盖率：77.74%，超过70%目标
- [x] **创建 PHASE6_PROGRESS.md** - 阶段6完成报告
  - 🎯 Medium
  - 📝 详细记录Phase 6的所有工作和成果

### 📋 任务 4：最终验证
- [x] **验证CI兼容性** - 确保所有修复不影响CI运行
  - 🎯 High
  - 📝 本地模拟测试通过，代码质量检查通过
- [x] **生成最终报告** - 输出Phase 6完成总结
  - 🎯 Medium
  - 📝 包含所有技术细节和后续建议

### 🎯 Phase 6 最终验收标准
- [x] 数据库迁移问题完全解决
- [x] 集成测试稳定运行
- [x] 外部依赖Mock框架完善
- [x] 文档更新完成
- [x] CI兼容性验证通过
