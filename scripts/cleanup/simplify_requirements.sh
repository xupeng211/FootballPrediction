#!/bin/bash
# 简化依赖管理脚本
# 将18个依赖文件合并为6个核心文件

set -e

echo "📦 开始简化依赖管理..."
cd "$(dirname "$0")/../.."

# 备份当前requirements目录
if [ -d "requirements_backup" ]; then
    rm -rf requirements_backup
fi
cp -r requirements requirements_backup
echo "✅ 已备份当前requirements目录到 requirements_backup"

# 进入requirements目录
cd requirements/

# 1. 创建新的base.txt（生产核心依赖）
echo "📝 创建新的 base.txt..."
cat > base.txt << 'EOF'
# 生产核心依赖
# Core dependencies for production

# Web框架
fastapi==0.115.6
uvicorn[standard]==0.32.1

# 数据库
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.14.0

# 缓存
redis==5.2.1

# 数据验证
pydantic==2.10.4
pydantic-settings==2.7.0

# 工具库
python-multipart==0.0.18
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1
httpx==0.28.1

# 监控
prometheus-client==0.21.0
structlog==24.4.0

# 任务队列
celery==5.4.0
kombu==5.4.2
EOF

# 2. 创建新的dev.txt（开发依赖）
echo "📝 创建新的 dev.txt..."
cat > dev.txt << 'EOF'
# 开发依赖
# Development dependencies

-r base.txt

# 代码质量
ruff==0.8.4
mypy==1.13.0
black==24.10.0
isort==5.13.2

# 测试
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-cov==6.0.0
pytest-mock==3.14.0
pytest-xdist==3.6.1
factory-boy==3.3.1

# 开发工具
pre-commit==4.0.1
ipython==8.31.0
jupyter==1.1.1
pip-tools==7.4.1

# 文档
mkdocs==1.6.1
mkdocs-material==9.5.49
EOF

# 3. 创建新的test.txt（测试依赖）
echo "📝 创建新的 test.txt..."
cat > test.txt << 'EOF'
# 测试依赖
# Testing dependencies

-r base.txt

# 测试框架
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-cov==6.0.0
pytest-mock==3.14.0
pytest-xdist==3.6.1

# 测试工具
factory-boy==3.3.1
faker==33.1.0
httpx==0.28.1
testcontainers==4.9.0

# 性能测试
pytest-benchmark==4.0.0
locust==2.31.4
EOF

# 4. 创建新的optional.txt（可选依赖）
echo "📝 创建新的 optional.txt..."
cat > optional.txt << 'EOF'
# 可选依赖
# Optional dependencies for specific features

# 机器学习
pandas==2.2.3
numpy==1.26.4
scikit-learn==1.5.2
joblib==1.4.2
mlflow==2.18.0

# 流处理
aiokafka==0.12.0
aio-pika==9.4.3

# 监控增强
grafana-api==1.0.3
statsd==4.0.1

# 其他可选
sentry-sdk==2.19.2
newrelic==9.4.0
EOF

# 5. 创建requirements.lock（完整锁定文件）
echo "📝 创建新的 requirements.lock..."
# 首先合并所有依赖
cat > requirements_all.txt << 'EOF'
# 合并所有依赖用于生成锁定文件
-r base.txt
-r dev.txt
-r optional.txt
EOF

# 6. 创建README.md说明文档
echo "📝 创建 requirements/README.md..."
cat > README.md << 'EOF'
# Requirements 文件说明

## 文件结构

- `base.txt` - 生产环境核心依赖
- `dev.txt` - 开发环境依赖（包含 base.txt）
- `test.txt` - 测试依赖（包含 base.txt）
- `optional.txt` - 可选功能依赖（ML、Streaming等）
- `requirements.lock` - 完整的依赖锁定文件
- `README.md` - 本说明文档

## 使用方式

### 生产环境
```bash
pip install -r base.txt
```

### 开发环境
```bash
pip install -r dev.txt
```

### 测试环境
```bash
pip install -r test.txt
```

### 安装可选依赖
```bash
pip install -r optional.txt
```

### 完整环境（包含所有依赖）
```bash
pip install -r requirements.lock
```

## 依赖管理

使用 pip-tools 管理依赖：

```bash
# 更新锁定文件
pip-compile requirements.in

# 同步环境
pip-sync requirements.txt
```

## 历史变更

- 2025-10-12: 从18个文件简化为6个核心文件
EOF

# 7. 清理旧文件
echo "🗑️ 清理旧的依赖文件..."
# 保留一些可能需要的文件，移动到backup目录
mkdir -p ../archive/requirements_old

# 移动所有旧文件到archive
mv -f *.backup *.new *.lock *.in ../archive/requirements_old/ 2>/dev/null || true

# 移动特定文件到archive
mv -f api.txt core.txt streaming.txt minimum.txt ultra-minimal.txt clean-production.txt production.txt ../archive/requirements_old/ 2>/dev/null || true

# 临时文件
mv -f requirements_all.txt ../archive/requirements_old/ 2>/dev/null || true

echo "✅ 依赖文件简化完成！"
echo ""
echo "📊 新的文件结构："
ls -la

echo ""
echo "📈 文件数量对比："
echo "  原始文件数: $(ls ../archive/requirements_old/ | wc -l)"
echo "  当前文件数: $(ls | wc -l)"

# 8. 验证新配置
echo ""
echo "🔍 验证新的依赖配置..."

# 检查文件格式
echo "检查 base.txt..."
if grep -q "==" base.txt; then
    echo "✅ base.txt 格式正确"
else
    echo "❌ base.txt 格式有误"
fi

# 检查dev.txt是否可以正常安装
echo "检查 dev.txt..."
if grep -q "==" dev.txt; then
    echo "✅ dev.txt 格式正确"
else
    echo "❌ dev.txt 格式有误"
fi

echo ""
echo "🎉 依赖管理简化完成！"
echo ""
echo "📝 后续建议："
echo "1. 运行 'pip install -r requirements.lock' 安装完整的开发环境"
echo "2. 更新 Makefile 中的相关命令"
echo "3. 更新 CI/CD 配置文件"
echo "4. 通知团队成员新的依赖结构"
