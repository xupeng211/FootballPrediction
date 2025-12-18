# Claude Skills 配置说明

这个目录包含了为FootballPrediction项目专门配置的Claude Skills，主要用于自动化代码质量管理和测试保证。

## 配置文件概览

### 1. `skills.json`
主要的Claude Skills配置文件，定义了"代码质量管理"技能：

**核心功能：**
- 集成项目的27个Makefile质量检查命令
- 支持自动代码修复（格式化、导入排序等）
- 项目特定的架构模式检查（async-first、Service Layer v2.0等）
- 完整的CI/CD集成支持

**关键触发器：**
- 代码修改、PR提交、质量检查、测试运行、代码审查

### 2. `project-quality-config.json`
项目特定的质量管理配置：

**包含信息：**
- 当前v2.0稳定版本的架构详情
- 质量目标（覆盖率80%+、响应时间<100ms等）
- 已知问题和解决方案
- 改进领域优先级排序

**特别关注：**
- V2测试状态（51个测试，29个通过，22个跳过）
- Git状态提醒（多个文件处于staging状态）
- Docker服务连接问题解决方案

### 3. `test-management.json`
专门的测试管理配置：

**测试结构：**
- V2测试：最高优先级，关注新架构
- 单元测试：业务逻辑验证
- 集成测试：数据库和外部API
- 端到端测试：完整工作流
- 性能测试：响应时间和并发

**执行命令：**
```bash
# 快速测试
make test

# 覆盖率测试
make coverage

# 完整CI模拟
make ci

# Docker中测试
./scripts/docker-manager.sh test

# V2测试专用
pytest tests/v2/ -v
```

## 使用指南

### 日常开发工作流

1. **开始开发前：**
   ```bash
   make dev              # 环境设置
   docker-compose up -d  # 启动服务
   sleep 30             # 等待服务就绪
   ```

2. **代码修改后：**
   ```bash
   make quality          # 运行所有质量检查
   make test            # 运行测试
   make coverage        # 检查覆盖率
   ```

3. **提交前：**
   ```bash
   make prepush         # 完整预提交检查
   ./ci-verify.sh       # 本地CI验证
   ```

### 常见问题快速解决

**V2测试跳过问题：**
```bash
# 启动完整环境
docker-compose up -d
sleep 30
./scripts/docker-manager.sh test

# 或运行特定可用测试
pytest tests/v2/test_health_schema.py -v
pytest tests/v2/test_inference_logic.py::test_single_match_prediction -v
```

**数据库连接问题：**
```bash
# 检查服务状态
docker-compose ps
docker-compose logs db

# 重启服务
docker-compose down && docker-compose up -d
```

**Git状态处理：**
```bash
# 查看当前状态
git status
git diff --cached

# 重置staging（如需要）
git reset HEAD
```

### 质量目标

- **测试覆盖率：** 80%+
- **响应时间：** <100ms（单次预测）
- **缓存命中率：** >80%
- **代码质量：** 通过所有make quality检查

### 监控和报告

- **Grafana仪表板：** http://localhost:3000 (admin/admin123)
- **Prometheus指标：** http://localhost:9090
- **覆盖率报告：** htmlcov/index.html

## 项目特色

这个Claude Skills配置专门针对FootballPrediction项目的以下特点：

1. **Service Layer v2.0架构** - 现代微服务架构
2. **ML推理引擎** - XGBoost模型集成
3. **异步优先设计** - FastAPI + async/await
4. **完整容器化** - Docker + docker-compose
5. **生产就绪** - 监控、日志、健康检查齐全

## 更新日志

- **2025-12-17:** 初始配置创建，支持v2.0稳定版本的代码质量管理
- **配置状态:** 已启用，准备用于代码质量改进工作

---

**注意:** 这个配置与项目的Makefile、CI/CD工作流和Docker环境紧密集成，确保与现有开发流程的无缝衔接。