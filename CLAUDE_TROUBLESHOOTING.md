# Claude 故障排除指南

本文档帮助解决开发过程中遇到的常见问题。

## 🔧 环境问题

### 问题：虚拟环境激活失败

**症状**：

```
make: venv: No such file or directory
```

**解决方案**：

```bash
# 1. 删除旧环境
rm -rf .venv

# 2. 重新创建
make venv

# 3. 安装依赖
make install

# 4. 验证
make env-check
```

### 问题：依赖冲突

**症状**：

```
ERROR: pip's dependency resolver does not currently take into account...
```

**解决方案**：

```bash
# 方法1：清理并重装
pip uninstall -y -r requirements.txt
pip install -r requirements.txt

# 方法2：使用pip-tools
pip install pip-tools
pip-compile requirements.in
pip-sync requirements.txt

# 方法3：完全重建
make clean && make install
```

### 问题：Python版本不匹配

**症状**：

```
Python 3.8+ required but 3.7.9 is installed
```

**解决方案**：

```bash
# 检查版本
python3 --version

# 使用正确的Python
make venv PYTHON=python3.11

# 或设置别名
alias python=python3.11
```

## 🧪 测试问题

### 问题：测试数据库连接失败

**症状**：

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方案**：

```bash
# 1. 检查Docker服务
docker-compose ps

# 2. 启动数据库服务
docker-compose up -d db

# 3. 等待服务就绪
sleep 5

# 4. 重新运行测试
make test
```

### 问题：测试覆盖率不足

**症状**：

```
FAILED: Coverage 75% < 80%
```

**解决方案**：

```bash
# 1. 查看覆盖率报告
make coverage-unit

# 2. 找到未覆盖的文件
open htmlcov/index.html

# 3. 针对性添加测试
pytest tests/unit/missing_coverage_file.py

# 4. 快速验证
make coverage-fast
```

### 问题：导入错误

**症状**：

```
ModuleNotFoundError: No module named 'src'
```

**解决方案**：

```bash
# 1. 设置PYTHONPATH
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# 2. 或在pytest.ini中配置
# pytest.ini已包含pythonpath = src

# 3. 永久设置
echo 'export PYTHONPATH="$(pwd):${PYTHONPATH}"' >> ~/.bashrc
```

### 问题：异步测试失败

**症状**：

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

**解决方案**：

```bash
# 使用pytest-asyncio
pytest tests/unit/test_async.py -v

# 或添加标记
pytest -m asyncio tests/unit/
```

## 🐳 Docker问题

### 问题：端口冲突

**症状**：

```
Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use
```

**解决方案**：

```bash
# 1. 查找占用端口的进程
lsof -i :5432

# 2. 停止冲突服务
docker-compose down

# 3. 或使用不同端口
docker-compose up -d --scale db=0
docker-compose -f docker-compose.override.yml up -d
```

### 问题：Docker构建失败

**症状**：

```
failed to solve: process "/bin/sh -c pip install" didn't complete
```

**解决方案**：

```bash
# 1. 清理Docker缓存
docker system prune -a

# 2. 重新构建
docker-compose build --no-cache

# 3. 检查Dockerfile
cat Dockerfile
```

## 🏗️ 代码质量问题

### 问题：类型检查失败

**症状**：

```
error: Incompatible types in assignment
```

**解决方案**：

```bash
# 1. 查看具体错误
make type-check 2>&1 | grep -A 5 error

# 2. 添加类型注解
from typing import List, Optional

def my_function(param: Optional[str] = None) -> bool:
    return True

# 3. 使用# type:忽略
variable = value  # type: ignore
```

### 问题：代码格式化失败

**症状**：

```
would reformat src/file.py
```

**解决方案**：

```bash
# 自动格式化
make fmt

# 或手动格式化
black src/
isort src/

# 检查特定文件
black --diff src/problematic_file.py
```

## 🚀 性能问题

### 问题：测试运行缓慢

**症状**：
单个测试运行时间 > 10秒

**解决方案**：

```bash
# 1. 找到慢测试
pytest --durations=10

# 2. 使用mock
from unittest.mock import Mock, patch

@patch('src.module.slow_function')
def test_fast_version(mock_slow):
    mock_slow.return_value = expected_value
    # 测试代码

# 3. 使用pytest标记
@pytest.mark.slow
def test_slow_integration():
    pass

# 运行时排除慢测试
pytest -m "not slow"
```

### 问题：内存不足

**症状**：

```
MemoryError: Unable to allocate array
```

**解决方案**：

```bash
# 1. 使用生成器
def large_generator():
    for item in large_list:
        yield process(item)

# 2. 分批处理
def process_in_batches(data, batch_size=1000):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]

# 3. 监控内存
make profile-memory
```

## 🔐 权限问题

### 问题：.env文件权限

**症状**：

```
PermissionError: [Errno 13] Permission denied: '.env'
```

**解决方案**：

```bash
# 1. 检查权限
ls -la .env

# 2. 修改权限
chmod 644 .env

# 3. 复制模板
cp .env.example .env
```

## 📝 IDE问题

### 问题：VSCode无法识别模块

**症状**：

```
Import "src.utils" could not be resolved
```

**解决方案**：

```bash
# 1. 创建.vscode/settings.json
mkdir -p .vscode
cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.analysis.extraPaths": ["./src"]
}
EOF

# 2. 重新加载VSCode窗口
# Ctrl+Shift+P -> Python: Select Interpreter -> ./.venv/bin/python
```

## 🆘 紧急恢复

### 完全重置环境

```bash
# 1. 备份当前更改
git stash

# 2. 清理所有
git clean -fdx
docker system prune -a

# 3. 重新开始
git checkout main
make install
make context
make test
```

### 快速健康检查

```bash
# 一键诊断
make env-check && \
make test-quick && \
make fmt && \
echo "✅ 系统正常"
```

## 📞 获取帮助

### 查看日志

```bash
# 应用日志
docker-compose logs -f app

# 测试日志
pytest tests/ -v --tb=short

# CI日志
./ci-verify.sh 2>&1 | tee ci.log
```

### 有用的命令

```bash
# 查看项目状态
make context

# 查看所有可用命令
make help

# 查看特定命令帮助
make help | grep test
```

## 📋 问题检查清单

遇到问题时，按顺序检查：

- [ ] 运行 `make env-check`
- [ ] 检查Python版本是否 ≥3.11
- [ ] 确认虚拟环境已激活
- [ ] 检查Docker服务状态
- [ ] 查看最近的代码变更
- [ ] 搜索错误信息
- [ ] 查看相关日志

---
*最后更新：2025-10-02*
