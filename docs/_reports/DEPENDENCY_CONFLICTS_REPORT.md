# 依赖冲突详细报告

## 严重级别分类

### 🔴 高风险冲突（需要立即解决）

| 包名 | 版本冲突 | 影响 |
|------|----------|------|
| numpy | 1.26.4 (生产) vs 2.3.3 (环境) | 数据处理API不兼容 |
| pydantic | 2.10.5 (生产) vs 2.10.6 (环境) | 模型验证可能失败 |
| mlflow | 2.18.0 (生产) vs 3.4.0 (requirements_full) | 重大版本差异 |

### 🟡 中等风险冲突

| 包名 | 版本冲突 | 建议 |
|------|----------|------|
| fastapi | 0.115.6 vs 0.116.1 | 统一到生产版本 |
| pandas | 2.2.3 vs 2.3.2 | 统一到生产版本 |
| scikit-learn | 1.6.0 vs 1.7.1 | 统一到生产版本 |

### 🟢 低风险冲突

主要是测试工具和开发工具的版本差异，不影响生产运行。

## 冲突原因分析

1. **requirements_full.txt** 存在大量更新版本的依赖
2. **tests/requirements.txt** 使用灵活的版本范围
3. **setup.py** 中的 extras_require 可能过时

## 解决方案

### 方案一：清理依赖文件（推荐）

```bash
# 1. 备份当前文件
cp requirements.txt requirements.txt.backup
cp requirements-dev.txt requirements-dev.txt.backup

# 2. 删除不必要的文件
rm requirements_full.txt
rm tests/requirements.txt

# 3. 更新 setup.py 移除重复的依赖定义
```

### 方案二：使用 pip-tools 重构

```bash
# 1. 安装 pip-tools
pip install pip-tools

# 2. 创建 requirements.in
echo "-e ." > requirements.in
cat requirements.txt | grep -v "^#" | grep -v "^$" >> requirements.in

# 3. 编译生成锁定文件
pip-compile requirements.in -o requirements.lock.txt
```

## 优先级

1. **立即**: 解决 numpy 版本冲突
2. **今天**: 统一核心依赖版本
3. **本周**: 清理重复定义
4. **下周**: 实施 pip-tools