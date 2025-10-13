# 依赖管理指南

## 概述

本项目使用**依赖锁定**系统确保开发和生产环境的一致性。

## 文件说明

| 文件 | 用途 | 是否提交到版本控制 |
|------|------|-------------------|
| `requirements.txt` | 核心依赖（无版本锁定） | ✅ 是 |
| `requirements-dev.txt` | 开发依赖 | ✅ 是 |
| `requirements-test.txt` | 测试依赖 | ✅ 是 |
| `requirements.lock.txt` | **完整依赖锁定** | ✅ 是 |

## 命令参考

### 安装依赖

```bash
# 常规安装（可能获得不同版本）
make install

# 可重现安装（推荐用于生产）
make install-locked
```

### 管理依赖

```bash
# 添加新依赖
pip install <package-name>
make lock-deps  # 立即锁定！

# 更新依赖
pip install --upgrade <package-name>
make lock-deps  # 重新锁定
```

### 验证依赖

```bash
# 检查当前环境是否与锁文件一致
make verify-deps
```

## 工作流程

### 1. 开发新功能

```bash
# 1. 安装依赖
make install-locked

# 2. 添加新依赖（如果需要）
pip install new-package

# 3. 开发完成后，锁定依赖
make lock-deps

# 4. 提交更改
git add requirements.lock.txt
git commit -m "feat: add new-package dependency"
```

### 2. 部署到生产

```bash
# 1. 克隆代码
git clone <repository>

# 2. 安装锁定版本
make install-locked

# 3. 验证环境
make verify-deps
```

### 3. CI/CD 流程

```yaml
# .github/workflows/ci.yml 示例
- name: Setup Python
  uses: actions/setup-python@v4

- name: Install dependencies
  run: make install-locked

- name: Verify dependencies
  run: make verify-deps

- name: Run tests
  run: make test
```

#### 实际CI集成

本项目已在CI流水线中集成依赖一致性检查：

1. **质量检查阶段** - 自动验证依赖一致性
   - 如果 `requirements.lock.txt` 存在，CI会自动运行 `make verify-deps`
   - 验证失败会阻止流水线继续执行

2. **测试阶段** - 优先使用锁定依赖
   - CI会自动检测并使用 `make install-locked`
   - 确保测试环境与开发环境完全一致

3. **缓存优化** - 包含锁文件哈希
   - 依赖缓存键包含 `requirements.lock.txt`
   - 依赖更新时自动刷新缓存

## 最佳实践

### ✅ 做什么

1. **始终使用 `make install-locked`**
   - 确保环境一致性
   - 避免意外的版本更新

2. **添加依赖后立即锁定**

   ```bash
   pip install some-package
   make lock-deps
   git add requirements.lock.txt
   ```

3. **定期验证依赖**

   ```bash
   make verify-deps
   ```

4. **团队协作时共享锁文件**
   - 确保所有人使用相同版本

### ❌ 避免什么

1. **不要手动编辑 `requirements.lock.txt`**
   - 它是自动生成的

2. **不要直接 `pip install` 后不锁定**
   - 会导致环境不一致

3. **不要提交 `requirements_frozen.txt`**
   - 这是临时文件

## 故障排除

### 依赖冲突

```bash
# 检查冲突
make verify-deps

# 解决方案：重新创建环境
rm -rf .venv
make install-locked
```

### 锁文件过时

```bash
# 更新所有依赖
pip install --upgrade -r requirements.txt
make lock-deps
```

### 特定包版本问题

```bash
# 安装特定版本
pip install package==1.2.3

# 验证并锁定
make verify-deps
make lock-deps
```

## 背后的原理

### 为什么需要依赖锁定？

1. **可重现性** - 确保任何时间、任何环境都能获得相同的依赖版本
2. **安全性** - 避免意外安装包含漏洞的新版本
3. **稳定性** - 防止依赖更新导致的破坏性变更

### 锁文件包含什么？

- 所有直接和间接依赖
- 精确的版本号
- 总计208个包（包括传递依赖）
- pip工具版本（pip, setuptools, wheel）

### 与其他工具的比较

| 工具 | 锁文件 | 优点 | 缺点 |
|------|--------|------|------|
| pip + requirements.lock.txt | ✅ | 简单，无需额外工具 | 需要手动管理 |
| Pipenv | Pipfile.lock | 集成虚拟环境 | 学习成本高 |
| Poetry | poetry.lock | 现代化，功能丰富 | 改变工作流 |
| PDM | pdm.lock | 快速，PEP 582 | 较新，生态不成熟 |

## 相关资源

- [Python 依赖管理最佳实践](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
- [pip 文档](https://pip.pypa.io/en/stable/)
- [requirements.txt 格式规范](https://pip.pypa.io/en/stable/reference/requirements-file-format/)

---
最后更新: 2025-10-05
