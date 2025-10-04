# 分层依赖管理方案

## 策略概述

采用分层依赖管理，将依赖分为多个层次，确保生产环境稳定：

1. **core** - 核心运行时依赖
2. **ml** - 机器学习依赖
3. **api** - API服务依赖
4. **dev** - 开发工具依赖
5. **test** - 测试依赖
6. **lint** - 代码质量工具

## 目录结构

```
requirements/
├── base.txt          # Python基础版本
├── core.txt           # 核心依赖（FastAPI等）
├── ml.txt             # 机器学习依赖
├── api.txt            # API相关依赖
├── dev.txt            # 开发工具
├── test.txt           # 测试工具
├── lint.txt           # 代码检查工具
├── production.txt     # 生产环境（core + ml + api）
├── development.txt     # 开发环境（production + dev + test + lint）
└── minimum.txt        # 最小运行环境
```

## 冲突解决原则

1. **生产环境优先** - 生产环境不包含开发工具
2. **版本锁定** - 所有版本精确锁定
3. **环境隔离** - 不同环境使用不同依赖集
4. **最小化原则** - 生产环境只安装必需的包