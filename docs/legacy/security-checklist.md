# 🛡️ FootballPrediction 项目安全检查清单

## 📋 部署前安全检查清单

### 🔐 密码和凭据安全

- [ ] **移除所有默认密码**
  - [ ] 确认没有 `change_me` 占位符
  - [ ] 确认没有 `minioadmin` 或其他默认凭据
  - [ ] 验证所有密码长度 ≥ 32 字符
  - [ ] 验证所有密码包含大小写字母、数字和特殊字符

- [ ] **环境变量配置**
  - [ ] 创建 `.env` 文件（从 `env.secure.template` 复制）
  - [ ] 设置 `.env` 文件权限为 600: `chmod 600 .env`
  - [ ] 确认 `.env` 文件在 `.gitignore` 中
  - [ ] 验证所有敏感信息都使用环境变量

### 🔒 数据库安全

- [ ] **PostgreSQL 安全配置**
  - [ ] 使用强密码（已生成随机密码）
  - [ ] 启用权限分离（reader/writer/admin用户）
  - [ ] 验证数据库不对外暴露（仅内部网络访问）
  - [ ] 检查连接加密配置

- [ ] **数据库用户权限**
  - [ ] 验证 `football_reader` 仅有只读权限
  - [ ] 验证 `football_writer` 仅能写入指定表
  - [ ] 验证 `football_admin` 有完整管理权限
  - [ ] 测试权限分离是否正常工作

### 🔴 Redis 安全

- [ ] **Redis 安全配置**
  - [ ] 启用密码认证
  - [ ] 移除外部端口映射
  - [ ] 验证所有客户端使用密码连接
  - [ ] 启用 AOF 持久化

### 📦 MinIO 安全

- [ ] **MinIO 访问控制**
  - [ ] 使用强密码替换默认凭据
  - [ ] 移除公开桶策略
  - [ ] 设置最小权限原则
  - [ ] 验证所有桶为私有访问

- [ ] **MinIO 网络安全**
  - [ ] 验证 MinIO 仅在内部网络可访问
  - [ ] 配置正确的 CORS 策略
  - [ ] 启用 HTTPS（生产环境）

### 🌐 网络安全

- [ ] **端口暴露检查**
  - [ ] 仅必要的服务端口对外开放
  - [ ] Redis 不对外暴露端口
  - [ ] 数据库仅在开发环境暴露端口
  - [ ] 监控服务端口访问控制

- [ ] **容器网络安全**
  - [ ] 使用独立的 Docker 网络
  - [ ] 验证服务间通信仅在内部网络
  - [ ] 配置适当的网络隔离

### 🔍 监控和审计

- [ ] **安全监控**
  - [ ] 配置 Grafana 管理员密码
  - [ ] 启用访问日志
  - [ ] 配置异常访问告警
  - [ ] 设置密码策略监控

- [ ] **审计日志**
  - [ ] 启用数据库审计日志
  - [ ] 配置应用访问日志
  - [ ] 设置日志轮转策略
  - [ ] 确保日志安全存储

## 🧪 安全验证步骤

### 1. 密码强度验证

```bash
# 运行密码生成器验证
python3 scripts/generate-passwords.py --format json

# 检查密码复杂度
python3 -c "
import re
password = 'YOUR_PASSWORD_HERE'
checks = [
    (len(password) >= 32, '密码长度 ≥ 32'),
    (re.search(r'[a-z]', password), '包含小写字母'),
    (re.search(r'[A-Z]', password), '包含大写字母'),
    (re.search(r'[0-9]', password), '包含数字'),
    (re.search(r'[!@#$%^&*()_+=\-]', password), '包含特殊字符')
]
for check, desc in checks:
    print(f'{'✅' if check else '❌'} {desc}')
"
```

### 2. 服务连接测试

```bash
# 测试数据库连接（使用新密码）
docker-compose exec db psql -U football_user -d football_prediction_dev -c "SELECT version();"

# 测试 Redis 连接（使用密码）
docker-compose exec redis redis-cli -a "$REDIS_PASSWORD" ping

# 测试 MinIO 连接
docker-compose exec minio-init mc ls myminio/
```

### 3. 权限验证测试

```bash
# 测试数据库权限分离
docker-compose exec db psql -U football_reader -d football_prediction_dev -c "SELECT current_user;"
docker-compose exec db psql -U football_writer -d football_prediction_dev -c "SELECT current_user;"

# 测试 Redis 访问控制
docker-compose exec redis redis-cli ping  # 应该失败（无密码）
docker-compose exec redis redis-cli -a "$REDIS_PASSWORD" ping  # 应该成功
```

### 4. 网络安全测试

```bash
# 检查暴露的端口
docker-compose ps --services | xargs -I {} docker-compose port {}

# 测试外部访问
curl -f http://localhost:6379  # 应该失败（Redis不对外）
curl -f http://localhost:5432  # 开发环境可能成功，生产环境应该失败
```

### 5. 配置文件安全扫描

```bash
# 扫描配置文件中的敏感信息
grep -r "change_me\|password.*=" docker-compose.yml scripts/ --exclude-dir=.git
grep -r "minioadmin\|admin.*admin" docker-compose.yml scripts/ --exclude-dir=.git

# 检查环境变量使用
grep -r "\${.*PASSWORD" docker-compose.yml
```

## 🚨 安全事件响应

### 密码泄露响应流程

1. **立即响应**
   - [ ] 停止所有相关服务
   - [ ] 轮换所有受影响的密码
   - [ ] 检查访问日志

2. **恢复步骤**
   - [ ] 重新生成所有密码
   - [ ] 更新所有配置文件
   - [ ] 重新部署服务
   - [ ] 验证新配置

3. **事后分析**
   - [ ] 分析泄露原因
   - [ ] 加强安全措施
   - [ ] 更新安全流程
   - [ ] 培训团队成员

## 📚 安全最佳实践

### 🔐 密码管理

- **使用密钥管理服务**: 生产环境推荐使用 HashiCorp Vault、AWS Secrets Manager 等
- **定期轮换**: 至少每 90 天轮换一次密码
- **密码复杂度**: 最少 32 字符，包含大小写字母、数字、特殊字符
- **访问控制**: 实施最小权限原则

### 🛡️ 容器安全

- **镜像安全**: 使用官方镜像，定期更新
- **运行时安全**: 非 root 用户运行，只读文件系统
- **网络隔离**: 使用 Docker 网络隔离
- **资源限制**: 设置内存和 CPU 限制

### 📊 监控和告警

- **实时监控**: 配置关键指标监控
- **异常告警**: 设置异常访问告警
- **日志审计**: 启用详细审计日志
- **定期评估**: 定期进行安全评估

### 🔒 数据保护

- **传输加密**: 使用 TLS/SSL 加密传输
- **存储加密**: 敏感数据加密存储
- **备份安全**: 备份数据加密保护
- **访问日志**: 记录所有数据访问

## 📞 紧急联系信息

| 角色 | 联系方式 | 职责 |
|------|----------|------|
| 安全负责人 | security@company.com | 安全事件响应 |
| 系统管理员 | admin@company.com | 系统恢复 |
| 开发负责人 | dev@company.com | 技术支持 |

---

**⚠️ 重要提醒**: 本检查清单应在每次部署前完整执行，确保系统安全性。
