# 🔒 Docker 部署安全配置指南

## 🚨 重要安全提醒

本项目的 Docker 配置已修复硬编码密码漏洞。所有敏感信息现在都通过环境变量安全管理。

## 📋 必需的环境变量

在运行任何 Docker Compose 配置之前，请确保在 `.env` 文件中设置以下安全变量：

### 核心安全配置
```bash
# 应用主密钥（至少64字符）
SECRET_KEY=your-super-secret-key-minimum-64-characters-long-for-production-security

# JWT令牌密钥（至少32字符）
JWT_SECRET_KEY=your-jwt-secret-key-minimum-32-characters-long

# Grafana管理员密码
GRAFANA_ADMIN_PASSWORD=your_secure_grafana_admin_password_here
```

### 数据库安全配置
```bash
# PostgreSQL数据库密码（至少32字符）
POSTGRES_PASSWORD=your_secure_postgres_password_here_minimum_32_chars
```

### 缓存安全配置
```bash
# Redis缓存密码（至少16字符）
REDIS_PASSWORD=your_secure_redis_password_here_minimum_16_chars
```

### 邮件服务配置
```bash
SMTP_HOST=smtp.example.com:587
SMTP_USER=alerts@football-prediction.com
SMTP_PASSWORD=your_smtp_app_password_here
SMTP_FROM_ADDRESS=alerts@football-prediction.com
```

## 🔧 快速设置步骤

### 1. 复制环境变量模板
```bash
cp .env.example .env
```

### 2. 生成安全密钥
```bash
# 运行项目提供的密钥生成脚本
./generate_secure_keys.sh
```

### 3. 手动设置密码（如果脚本不可用）
```bash
# 生成强密码的示例命令
openssl rand -base64 32  # 生成32字符的随机密钥
openssl rand -base64 64  # 生成64字符的随机密钥
```

### 4. 验证配置
```bash
# 检查环境变量是否正确设置
grep -E "(SECRET_KEY|GRAFANA_ADMIN_PASSWORD|POSTGRES_PASSWORD|REDIS_PASSWORD)" .env
```

## ⚠️ 安全最佳实践

### 🔐 密码要求
- **SECRET_KEY**: 最少64字符，包含大小写字母、数字和特殊字符
- **JWT_SECRET_KEY**: 最少32字符，高熵随机字符串
- **POSTGRES_PASSWORD**: 最少32字符，包含大小写字母、数字和特殊字符
- **REDIS_PASSWORD**: 最少16字符，高熵随机字符串
- **GRAFANA_ADMIN_PASSWORD**: 最少12字符，包含大小写字母、数字和特殊字符

### 🛡️ 生产环境注意事项
1. **永远不要**在代码中硬编码密码
2. **永远不要**将 `.env` 文件提交到版本控制系统
3. **定期轮换**所有密码和密钥
4. **使用**密码管理器（如 HashiCorp Vault、AWS Secrets Manager）
5. **限制**对 `.env` 文件的访问权限（`chmod 600 .env`）

### 🔍 安全检查
运行安全检查脚本验证配置：
```bash
./scripts/security_check.sh
```

## 🚀 部署示例

### 开发环境
```bash
# 使用默认开发配置
make up
```

### 生产环境
```bash
# 确保设置了所有必需的环境变量
export $(grep -v '^#' .env | xargs)
make deploy
```

## 🆘 故障排除

### 常见问题
1. **容器启动失败**：检查环境变量是否正确设置
2. **Grafana无法访问**：确认 `GRAFANA_ADMIN_PASSWORD` 已设置
3. **数据库连接失败**：验证 `POSTGRES_PASSWORD` 配置
4. **Redis连接失败**：检查 `REDIS_PASSWORD` 设置

### 调试命令
```bash
# 检查容器状态
docker-compose ps

# 查看容器日志
docker-compose logs [service_name]

# 验证环境变量
docker-compose config
```

## 📞 安全事件报告

如果发现任何安全漏洞或配置问题，请立即：
1. 停止相关服务：`make down`
2. 更新安全配置
3. 重新启动服务：`make up`
4. 监控系统日志

---

**⚠️ 重要提醒**：本配置修复了之前版本中的硬编码密码漏洞（CVE-2024-XXXX）。请确保所有环境都使用新的安全配置。