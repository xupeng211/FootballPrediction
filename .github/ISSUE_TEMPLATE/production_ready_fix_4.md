---
name: ⚠️ P1-High: 依赖和环境兼容性问题修复
about: 修复依赖缺失、版本冲突和环境兼容性问题
title: '[P1-High] 依赖和环境兼容性修复 - 解决测试环境问题'
labels: 'high, production-ready, dependencies, environment'
assignees: ''

---

## ⚠️ High Priority Issue: 依赖和环境兼容性问题修复

### 📋 问题描述
发现多个依赖和环境兼容性问题，包括缺失的数据科学库、yaml库版本冲突、测试环境导入错误等。这些问题影响开发、测试和部署流程。

### 🔍 发现的问题

#### 🚨 **缺失的关键依赖**
1. **数据科学库缺失**
   ```bash
   # 测试时发现的缺失依赖
   - pandas
   - numpy
   - scikit-learn
   - aiohttp
   - psutil
   ```

2. **yaml库版本冲突**
   ```bash
   # 错误信息示例
   re.error: unbalanced parenthesis at position 280 (line 6, column 51)
   # yaml/__init__.py 中的正则表达式问题
   ```

#### ⚠️ **测试环境问题**
3. **导入错误**
   ```bash
   # 兼容性模块中的导入问题
   - tests/compatibility/test_basic_compatibility.py
   - 其他5个测试收集错误
   ```

4. **Docker环境问题**
   - 容器启动循环重启
   - 依赖安装失败
   - 环境变量配置问题

### 🎯 修复目标
- [ ] 安装所有缺失的依赖库
- [ ] 解决yaml库版本冲突
- [ ] 修复测试导入错误
- [ ] 确保Docker环境稳定运行
- [ ] 验证开发和测试环境一致性

### 🔧 具体修复步骤

#### Step 1: 更新requirements文件
```bash
# requirements.txt 添加缺失依赖
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
aiohttp>=3.8.0
psutil>=5.9.0

# 固定yaml版本避免冲突
PyYAML>=6.0.0,<7.0.0
```

#### Step 2: 修复yaml版本冲突
```bash
# 卸载并重新安装yaml
pip uninstall PyYAML
pip install PyYAML>=6.0.0,<7.0.0

# 或者降级到稳定版本
pip install PyYAML==6.0.1
```

#### Step 3: 修复测试导入错误
```python
# 检查并修复 tests/compatibility/ 目录中的导入问题
# 确保测试文件中的导入路径正确
```

#### Step 4: 更新Docker依赖
```dockerfile
# docker/Dockerfile 中确保依赖安装
RUN pip install --no-cache-dir \
    pandas>=2.0.0 \
    numpy>=1.24.0 \
    scikit-learn>=1.3.0 \
    aiohttp>=3.8.0 \
    psutil>=5.9.0 \
    PyYAML>=6.0.0,<7.0.0
```

### 🧪 环境验证步骤

#### 本地环境验证
```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. 验证关键依赖
python -c "
import pandas
import numpy
import sklearn
import aiohttp
import psutil
import yaml
print('✅ 所有关键依赖导入成功')
"

# 4. 运行语法检查
find src/ -name "*.py" -exec python -m py_compile {} \;
```

#### Docker环境验证
```bash
# 1. 重新构建镜像
docker-compose build

# 2. 启动容器
docker-compose up -d

# 3. 验证容器状态
docker-compose ps

# 4. 测试Python导入
docker-compose exec app python -c "
import pandas
import numpy
import sklearn
import yaml
print('✅ Docker容器中依赖正常')
"
```

#### 测试环境验证
```bash
# 1. 运行测试收集
pytest --collect-only -q

# 2. 运行核心测试
pytest -m "unit and not slow" -v --maxfail=5

# 3. 检查覆盖率
pytest --cov=src --cov-report=term-missing -x
```

### 📋 依赖检查清单

#### ✅ **基础依赖**
- [ ] Python 3.11+
- [ ] FastAPI + Uvicorn
- [ ] SQLAlchemy 2.0
- [ ] Alembic
- [ ] Pydantic

#### ✅ **数据科学依赖**
- [ ] pandas (>=2.0.0)
- [ ] numpy (>=1.24.0)
- [ ] scikit-learn (>=1.3.0)

#### ✅ **异步和网络依赖**
- [ ] aiohttp (>=3.8.0)
- [ ] asyncpg (PostgreSQL)
- [ ] aioredis (Redis)

#### ✅ **系统工具依赖**
- [ ] psutil (>=5.9.0)
- [ ] PyYAML (>=6.0.0,<7.0.0)
- [ ] python-multipart (文件上传)

#### ✅ **开发和测试依赖**
- [ ] pytest
- [ ] pytest-asyncio
- [ ] pytest-cov
- [ ] black/ruff (代码格式化)
- [ ] mypy (类型检查)

### 🔧 环境配置优化

#### requirements.txt 示例
```txt
# Web框架
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6

# 数据库
sqlalchemy>=2.0.0
alembic>=1.12.0
asyncpg>=0.29.0

# 数据科学
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0

# 缓存和消息
redis>=5.0.0
aioredis>=2.0.0

# 配置和工具
PyYAML>=6.0.0,<7.0.0
python-dotenv>=1.0.0
aiohttp>=3.8.0
psutil>=5.9.0

# 认证和安全
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

#### requirements-dev.txt 示例
```txt
# 测试
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0

# 代码质量
ruff>=0.1.0
mypy>=1.6.0
black>=23.0.0

# 开发工具
ipython>=8.15.0
jupyter>=1.0.0
```

### ⚠️ 常见问题和解决方案

#### 问题1: yaml库冲突
```bash
# 解决方案
pip uninstall PyYAML
pip install PyYAML==6.0.1
```

#### 问题2: 测试导入错误
```bash
# 解决方案
# 检查Python路径
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# 或在pytest.ini中配置
echo "pythonpath = src" >> pytest.ini
```

#### 问题3: Docker容器重启
```bash
# 解决方案
# 检查容器日志
docker-compose logs app

# 重新构建镜像
docker-compose build --no-cache app

# 检查环境变量
docker-compose exec app env | grep -E "(SECRET_KEY|DATABASE_URL)"
```

### ⏱️ 预计工作量
- **依赖修复**: 2-3小时
- **环境测试**: 2小时
- **Docker配置**: 1-2小时
- **总计**: 5-7小时

### ✅ 验收标准
- [ ] 本地开发环境正常启动
- [ ] Docker容器稳定运行
- [ ] 测试可以正常收集和执行
- [ ] 所有依赖导入无错误
- [ ] CI/CD pipeline通过依赖检查

### 🔗 相关Issues
- #1 - 修复语法错误 (前置依赖)
- #2 - 测试覆盖率提升 (并行进行)
- #3 - 安全配置强化 (并行进行)

---
**优先级**: P1-High
**处理时限**: 24小时内
**负责人**: 待分配
**创建时间**: 2025-10-30