# 🔒 安全问题修复操作指南

**文档版本**: 1.0  
**创建日期**: 2025-10-04  
**状态**: 🔴 需要立即执行

---

## 📋 执行清单

### ✅ 已完成的修复

- [x] 修复代码bug（缺少import、Prometheus指标重复）
- [x] 从Git索引移除 `.env.production`
- [x] 创建 `.env.example` 模板
- [x] 强制数据库密码配置
- [x] 添加API速率限制（已安装slowapi）
- [x] 生成新的安全密钥

### ⚠️ 待执行的关键步骤

- [ ] 清理Git历史中的敏感文件
- [ ] 轮换所有泄露的密钥
- [ ] 更新生产环境配置
- [ ] 测试所有功能

---

## 🚨 立即执行步骤

### 第1步: 清理Git历史（破坏性操作）

#### 选项A: 使用 git filter-branch（经典方法）

```bash
# 运行自动化脚本
./scripts/clean_git_history.sh

# 脚本会：
# 1. 创建完整备份
# 2. 要求双重确认
# 3. 清理Git历史
# 4. 给出后续指令
```

#### 选项B: 使用 BFG Repo-Cleaner（推荐，更快）

```bash
# 1. 下载 BFG（如果未安装）
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
mv bfg-1.14.0.jar bfg.jar

# 2. 运行清理脚本
./scripts/clean_git_with_bfg.sh
```

#### 清理后验证

```bash
# 检查文件是否还在历史中
git log --all --full-history -- .env.production

# 应该返回空结果
```

#### 强制推送到远程（谨慎！）

```bash
# ⚠️  警告：这会重写远程仓库历史！
git push origin --force --all
git push origin --force --tags

# 通知所有协作者重新克隆仓库
```

---

### 第2步: 轮换密钥

#### 2.1 备份当前生产配置

```bash
# 备份现有配置
cp .env.production .env.production.backup_$(date +%Y%m%d)
```

#### 2.2 使用新生成的密钥

新密钥已保存在: `.env.production.new_20251004_214417`

```bash
# 查看新密钥
cat .env.production.new_*

# 或手动更新每个密钥到生产环境
```

#### 2.3 更新密钥清单

必须更新的密钥：

```bash
# 应用密钥
SECRET_KEY=<新值>
JWT_SECRET_KEY=<新值>
JWT_REFRESH_SECRET_KEY=<新值>

# API密钥
API_KEY=<新值>
API_SECRET_KEY=<新值>

# 数据库加密
DB_ENCRYPTION_KEY=<新值>
DB_SALT=<新值>

# Redis密码
REDIS_PASSWORD=<新值>

# MLflow密码
MLFLOW_TRACKING_PASSWORD=<新值>

# 其他加密密钥
ENCRYPTION_KEY=<新值>
HASH_SALT=<新值>
SESSION_SECRET=<新值>
CSRF_SECRET=<新值>
```

#### 2.4 重启服务

```bash
# 使用Docker
docker-compose down
docker-compose up -d

# 或使用系统服务
systemctl restart football-prediction
```

---

### 第3步: 验证和测试

#### 3.1 测试API功能

```bash
# 健康检查
curl http://localhost:8000/health

# 测试认证
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# 测试速率限制
for i in {1..25}; do 
  curl http://localhost:8000/api/predictions/1 &
done
# 应该看到 429 Too Many Requests
```

#### 3.2 验证数据库连接

```bash
# 测试数据库密码是否生效
make db-init

# 如果失败并提示密码未配置，说明安全修复生效
```

#### 3.3 检查日志

```bash
# 查看应用日志
tail -f logs/app.log

# 查看速率限制日志
grep "rate limit" logs/app.log
```

---

## 📊 生成的工具和脚本

### 1. 密钥轮换工具

**文件**: `scripts/rotate_keys.py`

```bash
# 生成新密钥
python scripts/rotate_keys.py

# 输出新的.env文件
```

### 2. Git历史清理脚本

**文件**: 
- `scripts/clean_git_history.sh` (filter-branch方法)
- `scripts/clean_git_with_bfg.sh` (BFG方法)

```bash
# 执行清理
./scripts/clean_git_history.sh
```

---

## ⚠️ 重要注意事项

### Git历史清理的影响

1. **破坏性操作**: 所有提交SHA会改变
2. **团队协作**: 所有协作者需要重新克隆
3. **CI/CD**: 可能需要重新配置
4. **不可逆**: 一旦推送无法撤销

### 密钥轮换的影响

1. **现有会话**: 所有JWT token会失效
2. **加密数据**: 使用旧密钥加密的数据需要重新加密
3. **Redis数据**: 需要重新验证连接
4. **外部服务**: 需要更新API密钥

---

## 🔐 安全最佳实践

### 密钥管理建议

1. **使用密钥管理服务**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault

2. **定期轮换密钥**
   - 每90天轮换一次
   - 设置自动提醒

3. **访问控制**
   - 限制密钥访问权限
   - 记录所有访问日志

### Git安全建议

1. **启用分支保护**
   ```bash
   # GitHub: Settings -> Branches -> Add rule
   - Require pull request reviews
   - Require status checks
   - Include administrators
   ```

2. **使用 pre-commit hooks**
   ```bash
   # 已配置在 .pre-commit-config.yaml
   pre-commit install
   ```

3. **定期审计**
   ```bash
   # 扫描敏感文件
   git log --all --full-history --source --find-object=$(git hash-object .env)
   ```

---

## 📞 应急联系

如果发现额外的安全问题：

1. **立即操作**: 
   - 轮换相关密钥
   - 禁用受影响的API端点
   - 通知安全团队

2. **记录事件**:
   - 记录发现时间
   - 记录影响范围
   - 记录修复步骤

3. **事后分析**:
   - 分析根本原因
   - 更新安全流程
   - 培训团队成员

---

## ✅ 完成检查清单

执行完所有步骤后，确认：

- [ ] Git历史已清理（.env.production不在历史中）
- [ ] 所有密钥已轮换
- [ ] 生产环境已更新新密钥
- [ ] 所有服务正常运行
- [ ] API速率限制已启用
- [ ] 数据库强制密码配置已生效
- [ ] 所有协作者已通知
- [ ] 安全日志已记录
- [ ] 备份已妥善保管
- [ ] 旧密钥文件已安全删除

---

## 📚 相关文档

- `SECURITY_FIX_SUMMARY.md` - 修复总结
- `.env.example` - 环境变量模板
- `scripts/rotate_keys.py` - 密钥生成工具
- `scripts/clean_git_history.sh` - Git清理脚本

---

**最后更新**: 2025-10-04  
**下次审查**: 2025-11-04（30天后）

