# 📋 脚本工具索引
# Scripts Index

## 🎯 概述

本文档提供了足球预测系统所有自动化脚本的快速索引和使用指南。

## 🚀 部署脚本

### 主要部署脚本
```bash
# 完整部署自动化
./scripts/deploy-automation.sh
├── deploy     # 执行完整部署流程
├── rollback   # 回滚到指定版本
├── health     # 执行健康检查
└── validate   # 验证部署前置条件
```

### 快速部署命令
```bash
# 一键部署
./scripts/deploy-automation.sh deploy

# 快速健康检查
./scripts/deploy-automation.sh health

# 验证部署环境
./scripts/deploy-automation.sh validate
```

## 🔍 监控脚本

### 监控仪表板
```bash
./scripts/monitoring-dashboard.sh
├── overview    # 显示完整监控概览
├── system      # 系统指标
├── application # 应用指标
├── database    # 数据库指标
├── cache       # 缓存指标
├── business    # 业务指标
├── alerts      # 告警状态
├── health      # 健康总结
├── report      # 生成监控报告
└── links       # Grafana仪表板链接
```

### 自动化监控
```bash
./scripts/auto-monitoring.sh
├── check    # 执行一次监控检查
├── start    # 启动后台监控进程
├── stop     # 停止后台监控进程
├── status   # 检查监控进程状态
├── summary  # 生成监控摘要报告
├── cleanup  # 清理过期日志
└── daemon   # 守护进程模式
```

## 🆘 应急响应脚本

### 应急响应
```bash
./scripts/emergency-response.sh
├── check      # 系统健康检查
├── restart    # 紧急重启服务 (all|app|db|redis|nginx)
├── database   # 紧急数据库修复
├── cleanup    # 紧急资源清理
├── backup     # 紧急备份
├── security   # 安全检查
└── full       # 完整应急响应流程
```

### 快速诊断
```bash
./scripts/quick-diagnosis.sh
# 一键系统健康诊断和问题排查
```

## 🧪 测试脚本

### 性能测试
```bash
./scripts/performance-check.sh
├── basic # 基础性能检查
├── full  # 完整性能检查
└── load  # 负载测试
```

### 压力测试
```bash
python scripts/stress_test.py
# API端点压力测试，支持并发测试和性能分析
```

### 功能测试
```bash
make test-phase1    # 核心API测试
make test.unit      # 单元测试
make test.int       # 集成测试
make test.e2e       # 端到端测试
make coverage       # 测试覆盖率检查
```

## 📊 质量保证脚本

### 代码质量
```bash
make fmt            # 代码格式化
make lint           # 代码质量检查
make type-check     # 类型安全检查
make prepush        # 提交前完整检查
```

### 安全检查
```bash
make security-check # 安全漏洞扫描
make secret-scan    # 敏感信息扫描
make audit          # 完整安全审计
```

## 📞 通知脚本

### 团队通知
```bash
./scripts/notify-team.sh "消息内容" "通知类型"
# 通知类型: info, warning, error, success
```

## 🔧 系统管理脚本

### 最终检查
```bash
./scripts/final-check.sh
├── full   # 完整的系统就绪检查
├── quick  # 快速检查关键组件
└── report # 生成最终检查报告
```

### 数据库管理
```bash
make db-init      # 初始化数据库
make db-migrate   # 运行数据库迁移
make db-backup    # 创建数据库备份
make db-reset     # 重置数据库 (谨慎使用)
```

### Docker管理
```bash
make up           # 启动开发环境
make down         # 停止服务
make logs         # 查看日志
make deploy       # 构建生产镜像
make rollback     # 回滚到上一版本
```

## 📈 监控和维护

### 日常监控
```bash
# 每日监控检查
./scripts/monitoring-dashboard.sh overview

# 生成每日报告
./scripts/monitoring-dashboard.sh report daily

# 清理过期数据
./scripts/auto-monitoring.sh cleanup
```

### 性能调优
```bash
# 性能基线测试
./scripts/performance-check.sh full

# 压力测试
python scripts/stress_test.py

# 系统诊断
./scripts/quick-diagnosis.sh
```

## 🚨 应急处理流程

### 系统故障处理
```bash
# 1. 快速诊断问题
./scripts/quick-diagnosis.sh

# 2. 检查系统状态
./scripts/emergency-response.sh check

# 3. 如果需要，重启服务
./scripts/emergency-response.sh restart all

# 4. 生成事故报告
./scripts/emergency-response.sh full
```

### 数据库故障处理
```bash
# 1. 数据库紧急修复
./scripts/emergency-response.sh database

# 2. 数据库备份
./scripts/emergency-response.sh backup

# 3. 数据库健康检查
docker-compose exec db pg_isready -U prod_user
```

## 📋 使用建议

### 开发环境
```bash
# 启动开发环境
make up

# 运行测试
make test

# 代码质量检查
make prepush
```

### 生产部署
```bash
# 1. 部署前检查
./scripts/final-check.sh full

# 2. 执行部署
./scripts/deploy-automation.sh deploy

# 3. 启动监控
./scripts/auto-monitoring.sh start

# 4. 验证部署
./scripts/monitoring-dashboard.sh overview
```

### 日常运维
```bash
# 每日检查
./scripts/quick-diagnosis.sh

# 监控报告
./scripts/monitoring-dashboard.sh report daily

# 性能检查
./scripts/performance-check.sh basic
```

## 🔗 相关文档

- 📖 [部署指南](DEPLOYMENT_GUIDE.md)
- 🚀 [上线流程](DEPLOYMENT_PROCESS.md)
- 🆘 [应急预案](EMERGENCY_RESPONSE_PLAN.md)
- 📊 [监控指南](POST_DEPLOYMENT_MONITORING.md)
- 🎯 [部署就绪总结](DEPLOYMENT_READINESS_SUMMARY.md)

## 📞 技术支持

如需帮助，请：
1. 查看相关文档
2. 运行快速诊断脚本
3. 查看错误日志
4. 联系技术支持团队

---

*最后更新: 2025-10-22*