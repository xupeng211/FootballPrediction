---
name: ⚠️ P1-High: 安全配置强化和敏感信息处理
about: 修复安全配置问题，移除硬编码敏感信息
title: '[P1-High] 安全配置强化 - 移除硬编码敏感信息'
labels: 'high, production-ready, security'
assignees: ''

---

## ⚠️ High Priority Issue: 安全配置强化和敏感信息处理

### 📋 问题描述
发现多个安全配置问题，包括硬编码的敏感信息、弱密钥配置、不安全的默认值等。这些问题在生产环境中会带来严重安全风险。

### 🔍 发现的安全问题

#### 🚨 **硬编码敏感信息**
1. **src/api/dependencies.py:46**
   ```python
   SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "your-secret-key-here"))
   ```
   - 使用了不安全的默认值 "your-secret-key-here"
   - 生产环境中绝对不能使用默认密钥

2. **environments/.env.production**
   ```bash
   SECRET_KEY=${SECRET_KEY}  # 引用未设置的环境变量
   DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/football_prediction_prod
   ```
   - SECRET_KEY变量未实际设置
   - DB_PASSWORD变量未定义

#### ⚠️ **其他安全配置问题**
3. **调试模式配置**
   - 部分配置文件中DEBUG=true
   - 生产环境应该关闭调试模式

4. **CORS配置**
   - 需要验证CORS配置是否严格限制允许的域名

### 🎯 修复目标
- [ ] 移除所有硬编码的密钥和敏感信息
- [ ] 生成强随机SECRET_KEY
- [ ] 确保生产环境配置安全
- [ ] 验证CORS和其他安全配置
- [ ] 添加环境变量验证

### 🔧 具体修复步骤

#### Step 1: 生成安全的SECRET_KEY
```bash
# 生成强随机密钥
python3 -c "
import secrets
print(f'SECRET_KEY={secrets.token_urlsafe(32)}')
"
```

#### Step 2: 修复dependencies.py
```python
# 当前代码 (不安全)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "your-secret-key-here"))

# 修复后代码
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set in production")
```

#### Step 3: 更新环境配置文件
```bash
# environments/.env.production
ENV=production
DEBUG=false
LOG_LEVEL=INFO
# 生成实际的安全密钥
SECRET_KEY=<生成的强随机密钥>
DATABASE_URL=postgresql+asyncpg://football_user:${DB_PASSWORD}@db:5432/football_prediction_prod
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
MONITORING_ENABLED=true
```

#### Step 4: 添加环境变量验证
```python
# src/core/config.py 或类似文件
import os
from typing import Optional

def validate_required_env_vars():
    """验证生产环境必需的环境变量"""
    required_vars = ['SECRET_KEY', 'DATABASE_URL', 'REDIS_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")

# 在应用启动时调用
if os.getenv('ENV') == 'production':
    validate_required_env_vars()
```

### ✅ 安全检查清单

#### 🔐 **密钥和认证**
- [ ] SECRET_KEY使用强随机值 (32+字符)
- [ ] 移除所有硬编码的密钥
- [ ] JWT配置安全 (合理的过期时间)
- [ ] 密码哈希算法正确 (bcrypt)

#### 🌐 **网络和访问控制**
- [ ] DEBUG=false (生产环境)
- [ ] CORS配置严格限制允许域名
- [ ] HTTPS强制启用 (生产环境)
- [ ] 安全HTTP头配置

#### 🗄️ **数据库安全**
- [ ] 数据库密码使用强随机值
- [ ] 数据库连接使用SSL (如果可能)
- [ ] 数据库权限最小化原则

#### 📊 **监控和日志**
- [ ] 敏感信息不记录到日志
- [ ] 错误页面不泄露敏感信息
- [ ] 访问日志记录关键操作

### 🧪 安全测试
```bash
# 检查环境变量
python -c "
import os
print('SECRET_KEY set:', bool(os.getenv('SECRET_KEY')))
print('DEBUG mode:', os.getenv('DEBUG', 'false'))
"

# 检查硬编码密钥
grep -r "your-secret-key-here" src/ --include="*.py"
grep -r "password.*=" src/ --include="*.py" | grep -v "password_hash"
```

### 🚨 安全最佳实践

#### ✅ **必须做到**
1. 使用强随机SECRET_KEY (32+字符)
2. 生产环境关闭DEBUG模式
3. 使用HTTPS和严格CORS配置
4. 数据库密码强随机
5. 环境变量验证和错误处理

#### ❌ **必须避免**
1. 硬编码任何密钥或密码
2. 使用默认的示例密钥
3. 在生产环境启用DEBUG
4. 在日志中记录敏感信息
5. 使用弱密码或常见密钥

### ⏱️ 预计工作量
- **配置修复**: 2-3小时
- **密钥生成和配置**: 1小时
- **安全测试验证**: 2小时
- **总计**: 5-6小时

### 🔗 相关Issues
- #1 - 修复语法错误 (前置依赖)
- #2 - 测试覆盖率提升 (并行进行)

---
**优先级**: P1-High
**处理时限**: 24小时内
**负责人**: 待分配
**创建时间**: 2025-10-30
