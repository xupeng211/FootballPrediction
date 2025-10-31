# 🚨 Emergency Response Plan

## 紧急响应计划

**版本**: v1.0
**最后更新**: 2025-10-31
**维护团队**: FootballPrediction DevOps Team

---

## 📋 目录

- [🚨 紧急情况分级](#-紧急情况分级)
- [📞 联系方式](#-联系方式)
- [⚡ 网站/服务宕机](#-网站服务宕机)
- [🗄️ 数据库故障](#-数据库故障)
- [🔒 安全漏洞](#-安全漏洞)
- [📊 性能问题](#-性能问题)
- [🔄 部署失败](#-部署失败)
- [📧 通知流程](#-通知流程)
- [🔧 故障排查工具](#-故障排查工具)
- [📋 恢复检查清单](#-恢复检查清单)

## 🚨 紧急情况分级

### 🔴 P0 - Critical (立即响应)
- 网站完全无法访问
- 数据库连接失败
- 安全漏洞被利用
- 数据丢失或泄露
- **响应时间**: 15分钟内
- **解决目标**: 2小时内恢复基本服务

### 🟡 P1 - High (1小时内响应)
- 性能严重下降
- 部分功能无法使用
- 非关键安全漏洞
- **响应时间**: 1小时内
- **解决目标**: 6小时内修复

### 🟢 P2 - Medium (4小时内响应)
- 轻微性能问题
- 非核心功能bug
- 文档或配置问题
- **响应时间**: 4小时内
- **解决目标**: 24小时内修复

### ⚪ P3 - Low (24小时内响应)
- 改进建议
- 轻微优化需求
- 文档更新
- **响应时间**: 24小时内
- **解决目标**: 下个版本

## 📞 联系方式

### 🚨 紧急联系人

| 角色 | 姓名 | 联系方式 | 备注 |
|------|------|----------|------|
| 技术负责人 | [姓名] | 电话: [号码] | P0问题直接联系 |
| DevOps工程师 | [姓名] | 电话: [号码] | 基础设施问题 |
| 安全负责人 | [姓名] | 电话: [号码] | 安全相关问题 |
| 产品负责人 | [姓名] | 邮箱: [邮箱] | 产品相关问题 |

### 📧 通知渠道

1. **Slack**: #emergency-alerts (P0/P1)
2. **邮件**: devops-team@company.com
3. **电话**: 紧急情况直接呼叫
4. **GitHub Issues**: P2/P3问题

## ⚡ 网站/服务宕机

### 🚨 症状识别
- 用户无法访问网站
- 所有HTTP请求返回5xx错误
- 健康检查端点无响应
- 监控系统告警

### 🔧 立即响应 (P0)

#### 1. 快速诊断 (5分钟内)
```bash
# 检查服务状态
docker-compose ps

# 检查日志
docker-compose logs app --tail=50

# 检查资源使用
docker stats --no-stream

# 检查网络连通性
curl -f http://localhost/health
```

#### 2. 服务重启 (10分钟内)
```bash
# 重启应用服务
docker-compose restart app

# 重启nginx
docker-compose restart nginx

# 重启数据库 (如需要)
docker-compose restart db
```

#### 3. 回滚到稳定版本 (30分钟内)
```bash
# 查看最近标签
git tag --sort=-v:refname | head -5

# 回滚到稳定版本
git checkout LAST_STABLE_TAG
docker-compose down
docker-compose up -d

# 验证服务
curl -f http://localhost/health
```

### 📊 根本原因分析

#### 常见原因
1. **内存不足**: Docker容器OOMKilled
2. **数据库连接池满**: 连接未正确释放
3. **配置错误**: 环境变量或配置文件错误
4. **依赖问题**: 第三方服务不可用
5. **代码错误**: 最新部署的代码有问题

#### 诊断命令
```bash
# 检查内存使用
docker stats --no-stream | grep app

# 检查磁盘空间
df -h

# 检查系统负载
top -i 1

# 检查Docker日志
journalctl -u docker.service
```

## 🗄️ 数据库故障

### 🚨 症状识别
- 数据库连接超时
- 查询执行失败
- 数据不一致
- 备份失败

### 🔧 立即响应 (P0)

#### 1. 数据库状态检查
```bash
# 检查PostgreSQL状态
docker-compose exec db pg_isready -U postgres

# 检查连接数
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 检查慢查询
docker-compose exec db psql -U postgres -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

#### 2. 连接池优化
```bash
# 重启应用以释放连接
docker-compose restart app

# 检查连接池配置
docker-compose exec app python -c "
from src.database.connection import get_db_pool_status
print(get_db_pool_status())
"
```

#### 3. 数据恢复 (如需要)
```bash
# 从最新备份恢复
docker-compose exec -T db psql -U postgres -d football_prediction < /path/to/latest_backup.sql

# 检查数据完整性
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM users;"
```

### 📋 预防措施

#### 1. 连接池配置
```python
# DATABASE_URL示例
DATABASE_URL=postgresql://user:password@localhost:5432/football_prediction?pool_size=20&max_overflow=30&pool_pre_ping=true
```

#### 2. 定期备份
```bash
# 自动备份脚本 (每天2点和14点)
0 2,14 * * * /opt/football-prediction/scripts/backup_database.sh
```

#### 3. 监控告警
```yaml
# Prometheus告警规则
- alert: DatabaseDown
  expr: up{job="postgres"} == 0
  for: 1m
  labels:
    severity: critical
```

## 🔒 安全漏洞

### 🚨 症状识别
- 发现安全漏洞
- 异常访问日志
- 数据泄露迹象
- 系统被入侵

### 🔧 立即响应 (P0)

#### 1. 隔离受影响系统
```bash
# 检查活跃用户
docker-compose exec db psql -U postgres -c "SELECT usename, client_addr FROM pg_stat_activity WHERE state = 'active';"

# 限制访问 (如需要)
ufw deny from可疑_ip to any port
ufw reload
```

#### 2. 评估影响范围
```bash
# 检查敏感数据访问
grep -r "password\|secret\|token" . --include="*.py" --include="*.yml" --include="*.env*" | head -10

# 检查异常进程
ps aux | grep -E "(python|node|java)" | grep -v grep
```

#### 3. 修复漏洞
```bash
# 更新依赖包
pip install --upgrade affected-package

# 重新部署应用
docker-compose down
docker-compose pull
docker-compose up -d --build

# 验证修复
python3 scripts/security_check.py
```

### 📋 事后处理

1. **安全审计**: 全面安全评估
2. **漏洞报告**: 记录详细的问题和修复
3. **改进计划**: 制定预防措施
4. **团队培训**: 安全意识培训

## 📊 性能问题

### 🚨 症状识别
- 响应时间超过5秒
- CPU使用率超过80%
- 内存使用率超过90%
- 并发处理能力下降

### 🔧 立即响应 (P1)

#### 1. 性能诊断
```bash
# 检查资源使用
docker stats --no-stream

# 检查应用性能
curl -w "Time: %{time_total}s\n" -o /dev/null -s http://localhost/health

# 分析慢查询
docker-compose exec db psql -U postgres -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

#### 2. 优化措施
```bash
# 重启应用清理内存
docker-compose restart app

# 扩展资源
docker-compose up -d --scale app=2

# 清理临时文件
docker-compose exec app python -c "
import shutil
shutil.rmtree('/tmp/cache', ignore_errors=True)
"
```

#### 3. 监控优化
```python
# 性能监控配置
import time
import psutil

def check_performance():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent

    if cpu_percent > 80:
        print(f"⚠️ High CPU usage: {cpu_percent}%")

    if memory_percent > 90:
        print(f"⚠️ High memory usage: {memory_percent}%")
```

## 🔄 部署失败

### 🚨 症状识别
- 部署过程失败
- 新版本服务无法启动
- 健康检查失败
- 回滚到上一个版本

### 🔧 立即响应 (P1)

#### 1. 部署状态检查
```bash
# 检查部署日志
docker-compose logs app

# 检查镜像状态
docker images | grep football-prediction

# 检查服务状态
docker-compose ps
```

#### 2. 问题诊断
```bash
# 检查配置文件
docker-compose config

# 检查环境变量
env | grep -E "(DATABASE_URL|SECRET_KEY|REDIS_URL)"

# 检查端口占用
netstat -tulpn | grep -E ":80|:443|:5432|:6379"
```

#### 3. 快速修复
```bash
# 回滚到上一个工作版本
git checkout HEAD~1
docker-compose down
docker-compose up -d

# 重新部署
docker-compose up -d --build

# 验证部署
curl -f http://localhost/health
```

## 📧 通知流程

### 🔴 P0级 (立即通知)
1. **Slack**: #emergency-alerts
2. **电话**: 直接呼叫技术负责人
3. **邮件**: devops-team@company.com, management@company.com
4. **短信**: 管理层通知

### 🟡 P1级 (1小时内)
1. **Slack**: #devops-alerts
2. **邮件**: devops-team@company.com
3. **GitHub Issues**: 创建紧急Issue
4. **监控系统**: 自动告警

### 🟢 P2级 (4小时内)
1. **Slack**: #general
2. **邮件**: 相关团队
3. **GitHub Issues**: 标准Issue创建
4. **项目管理**: 更新项目状态

## 🔧 故障排查工具

### 🖥️ 系统工具
```bash
# Docker相关
docker-compose ps                    # 查看服务状态
docker-compose logs <service>        # 查看服务日志
docker stats --no-stream          # 查看资源使用
docker exec -it <service> bash    # 进入容器调试

# 系统监控
top -i 1                           # 实时系统状态
htop                              # 交互式进程查看器
df -h                              # 磁盘使用情况
free -h                             # 内存使用情况

# 网络诊断
curl -I http://localhost            # HTTP头检查
ping -c 4 8.8.8.8                   # 网络连通性
netstat -tulpn                      # 端口占用情况
```

### 🔍 应用工具
```bash
# 健康检查
curl -f http://localhost/health

# API测试
curl -X GET http://localhost/api/v1/health

# 性能测试
ab -n 100 -c 10 http://localhost/health

# 日志分析
docker-compose logs app | grep ERROR
docker-compose logs app | tail -100
```

### 📊 监控工具
```bash
# Prometheus
curl http://localhost:9090/targets

# Grafana
curl http://localhost:3000/api/health

# 应用指标
curl http://localhost/metrics
```

## 📋 恢复检查清单

### ✅ 服务恢复确认
- [ ] 所有服务状态为Up
- [ ] 健康检查端点返回200
- [ ] 网站可正常访问
- [ ] API端点响应正常
- [ ] 数据库连接正常
- [ ] Redis连接正常

### ✅ 数据完整性确认
- [ ] 数据库查询正常
- [ ] 关键数据存在
- [ ] 数据一致性检查通过
- [ ] 备份系统正常工作

### ✅ 安全状态确认
- [ ] 无异常登录活动
- [ ] 安全漏洞已修复
- [ ] 访问控制正常
- [ ] 加密连接正常工作

### ✅ 性能状态确认
- [ ] 响应时间 < 2秒
- [ ] CPU使用率 < 80%
- [ ] 内存使用率 < 85%
- [ ] 并发处理能力正常

### ✅ 监控系统确认
- [ ] 监控数据正常收集
- [ ] 告警系统正常工作
- [ ] 日志正常收集
- [ ] 通知系统正常发送

### ✅ 文档更新确认
- [ ] 事故报告已创建
- [] 根本原因已记录
- [ ] 预防措施已制定
- [ ] 团队已得到通知

---

## 📞 24/7 紧急联系

**中国地区**: +86-xxx-xxxx-xxxx
**国际地区**: +1-xxx-xxx-xxxx
**邮箱**: emergency@company.com
**Slack**: #emergency-alerts

---

*此紧急响应计划应定期审查和更新，以确保所有团队成员都了解正确的应急流程。*