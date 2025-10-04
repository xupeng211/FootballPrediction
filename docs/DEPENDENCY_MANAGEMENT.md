# 依赖管理文档

## 概述

本文档描述了FootballPrediction系统的依赖管理策略和最佳实践。

## 依赖文件说明

### requirements.txt
生产环境依赖，包含运行系统所需的核心包：
- FastAPI Web框架
- SQLAlchemy ORM
- PostgreSQL和Redis客户端
- 认证和安全库
- 数据处理库（pandas, numpy）
- MLflow机器学习平台

### requirements-dev.txt
开发环境依赖，包含生产依赖和开发工具：
- 测试框架（pytest）
- 代码质量工具（black, flake8, mypy）
- 文档生成工具
- 调试和分析工具

## 安装依赖

### 生产环境
```bash
pip install -r requirements.txt
```

### 开发环境
```bash
pip install -r requirements-dev.txt
```

## 依赖更新策略

### 定期更新
- 每月检查一次依赖更新
- 优先更新安全补丁
- 次要更新每季度进行

### 安全更新
- 使用 `pip-audit` 扫描漏洞
- 紧急安全修复立即应用
- 记录所有安全更新

## 锁定依赖

项目使用以下方式锁定依赖版本：
- `requirements.txt` - 精确版本控制
- `requirements.lock` - 完整依赖树（计划中）

## 虚拟环境

推荐使用Python虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

## 最佳实践

1. **定期清理**
   ```bash
   pip list --outdated
   pip-autoremove
   ```

2. **安全扫描**
   ```bash
   pip-audit
   bandit -r src/
   ```

3. **依赖检查**
   ```bash
   pip check
   ```

4. **使用预提交钩子**
   ```bash
   pre-commit install
   pre-commit run --all-files
   ```

## 常见问题

### Q: 如何添加新依赖？
A:
1. 开发依赖添加到 `requirements-dev.txt`
2. 生产依赖添加到 `requirements.txt`
3. 运行 `pip install -r requirements.txt` 测试
4. 更新文档

### Q: 如何处理依赖冲突？
A:
1. 使用 `pip-tools` 生成锁定文件
2. 检查 `pip check` 输出
3. 考虑使用虚拟环境隔离

### Q: 如何减少依赖大小？
A:
1. 移除未使用的依赖
2. 使用可选依赖 (`extras_require`)
3. 考虑轻量级替代品

## 更新日志

### 2025-10-04
- 创建标准化的requirements.txt和requirements-dev.txt
- 添加依赖管理文档
- 实施定期安全扫描

---
最后更新: 2025-10-04