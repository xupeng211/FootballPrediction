# Code Quality Skill

专门为FootballPrediction项目定制的代码质量管理技能。

## 功能概述

这个技能集成了项目的完整质量保证工具链，能够自动化执行代码检查、测试、覆盖率分析等质量保证任务。

## 主要特性

### 1. 集成的质量工具
- **black** - 代码格式化
- **flake8** - 代码风格检查
- **mypy** - 类型检查
- **bandit** - 安全扫描
- **radon** - 复杂度分析
- **vulture** - 死代码检测
- **coverage** - 测试覆盖率
- **pytest** - 测试执行

### 2. 项目特定配置
- 支持Service Layer v2.0架构验证
- ML推理代码质量检查
- FastAPI异步代码模式验证
- Docker容器化环境集成

### 3. 完整的命令集成
```bash
# 完整质量检查
make quality

# 快速测试
make test

# 覆盖率分析
make coverage

# CI模拟
make ci

# Docker环境测试
./scripts/docker-manager.sh test
```

## 使用场景

### 开发阶段
- 代码格式化和风格检查
- 类型检查和安全扫描
- 单元测试执行

### 提交前
- 完整质量检查
- 覆盖率验证
- 预提交检查

### CI/CD集成
- 自动化质量门禁
- 测试报告生成
- 覆盖率追踪

## 项目指标

- **总测试数**: 279个
- **V2测试**: 51个（29个通过，22个跳过）
- **目标覆盖率**: 80%+
- **响应时间目标**: <100ms
- **Makefile命令**: 27个

## 常见问题解决

### V2测试跳过
```bash
docker-compose up -d
sleep 30
./scripts/docker-manager.sh test
```

### Git状态清理
```bash
git status
git diff --cached
git reset HEAD  # 如需重置
```

## 配置文件

- `skill.json` - 技能主配置
- `../skills.json` - 全局技能配置
- `../project-quality-config.json` - 项目质量配置
- `../test-management.json` - 测试管理配置

---

这个技能专门针对FootballPrediction v2.0项目的架构和质量要求设计，确保代码质量和项目稳定性。