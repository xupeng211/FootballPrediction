# 应急响应预案
# Emergency Response Plan

## 🎯 概述

本文档定义了足球预测系统在生产环境中遇到紧急情况时的应急响应流程，确保系统问题能够快速、有效地得到解决。

## 🚨 应急响应级别

### Level 1: 紧急 (P0) - 5分钟内响应
- 系统完全宕机
- 数据丢失或泄露
- 安全攻击正在进行
- 所有用户无法访问

### Level 2: 高优先级 (P1) - 15分钟内响应
- 系统性能严重下降
- 部分功能不可用
- 数据不一致
- 高错误率 (> 10%)

### Level 3: 中等优先级 (P2) - 1小时内响应
- 系统性能轻微下降
- 非核心功能异常
- 配置需要调整
- 中等错误率 (5-10%)

### Level 4: 低优先级 (P3) - 4小时内响应
- 优化需求
- 文档更新
- 监控告警调整
- 低错误率 (< 5%)

## 🆘 应急联系人

### 核心响应团队
| 角色 | 姓名 | 联系方式 | 响应级别 |
|------|------|----------|----------|
| 技术负责人 | [姓名] | [电话/邮箱] | P0-P1 |
| 运维负责人 | [姓名] | [电话/邮箱] | P0-P2 |
| 安全负责人 | [姓名] | [电话/邮箱] | P0-P1 |
| 产品负责人 | [姓名] | [电话/邮箱] | P1-P3 |

### 备用联系人
| 角色 | 姓名 | 联系方式 | 响应级别 |
|------|------|----------|----------|
| 后备技术 | [姓名] | [电话/邮箱] | P1-P3 |
| 后备运维 | [姓名] | [电话/邮箱] | P2-P3 |

## 🚨 常见紧急场景

### 场景1: 系统完全宕机
**症状**:
- 所有服务无法访问
- 健康检查失败
- 监控显示服务离线

**响应步骤**:
1. **立即响应 (0-5分钟)**
   ```bash
   # 检查服务状态
   docker-compose ps

   # 查看系统日志
   docker-compose logs --tail=100

   # 检查系统资源
   top
   df -h
   ```

2. **快速诊断 (5-15分钟)**
   ```bash
   # 重启服务
   docker-compose restart

   # 如果重启失败，强制重建
   docker-compose down
   docker-compose up -d
   ```

3. **系统恢复 (15-30分钟)**
   ```bash
   # 验证服务状态
   ./scripts/deploy-automation.sh health

   # 运行性能检查
   ./scripts/performance-check.sh basic
   ```

4. **通知团队**
   ```bash
   ./scripts/notify-team.sh "系统宕机已恢复" success
   ```

### 场景2: 数据库连接失败
**症状**:
- API返回数据库错误
- 数据库连接池耗尽
- 数据查询超时

**响应步骤**:
1. **立即检查**
   ```bash
   # 检查数据库状态
   docker-compose exec db pg_isready -U prod_user

   # 查看数据库连接
   docker-compose exec db psql -U prod_user -c "SELECT count(*) FROM pg_stat_activity;"
   ```

2. **连接问题处理**
   ```bash
   # 重启数据库服务
   docker-compose restart db

   # 检查连接配置
   docker-compose exec app env | grep DATABASE_URL
   ```

3. **性能问题处理**
   ```bash
   # 检查慢查询
   docker-compose exec db psql -U prod_user -c "
   SELECT query, mean_time, calls
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;"
   ```

### 场景3: 高CPU/内存使用率
**症状**:
- 系统响应缓慢
- CPU使用率 > 90%
- 内存使用率 > 90%

**响应步骤**:
1. **资源诊断**
   ```bash
   # 检查进程资源使用
   docker stats

   # 找到高资源使用容器
   docker stats --no-stream
   ```

2. **容器级处理**
   ```bash
   # 重启高资源使用容器
   docker-compose restart app

   # 扩容服务
   docker-compose up -d --scale app=3
   ```

3. **系统级处理**
   ```bash
   # 清理Docker资源
   docker system prune -f

   # 清理日志文件
   find /var/lib/docker -name "*.log" -mtime +7 -delete
   ```

### 场景4: 安全攻击检测
**症状**:
- 异常访问模式
- 大量失败登录
- 可疑API调用

**响应步骤**:
1. **立即隔离**
   ```bash
   # 查看访问日志
   docker-compose logs nginx | grep -E "(error|401|403)"

   # 阻止可疑IP
   # 编辑 nginx/nginx.conf 添加 deny 规则
   docker-compose restart nginx
   ```

2. **安全扫描**
   ```bash
   # 运行安全审计
   ./scripts/security_audit.py

   # 检查文件完整性
   find /app -name "*.py" -exec md5sum {} \; > checksums.txt
   ```

3. **漏洞修复**
   ```bash
   # 更新依赖
   pip-audit --requirement requirements/requirements.lock

   # 应用安全补丁
   make security-fix
   ```

## 🔧 应急工具集

### 快速诊断脚本
```bash
#!/bin/bash
# 快速系统诊断
echo "=== 系统状态 ==="
docker-compose ps
echo ""

echo "=== 资源使用 ==="
docker stats --no-stream
echo ""

echo "=== 最近错误日志 ==="
docker-compose logs --tail=50 | grep -i error
echo ""

echo "=== 健康检查 ==="
curl -s http://localhost/health/ | jq .
```

### 服务重启脚本
```bash
#!/bin/bash
# 安全重启所有服务
./scripts/notify-team.sh "开始紧急重启服务" warning

docker-compose down
sleep 10
docker-compose up -d

# 等待服务启动
sleep 30

./scripts/deploy-automation.sh health
./scripts/notify-team.sh "服务重启完成" success
```

### 数据库紧急修复脚本
```bash
#!/bin/bash
# 数据库紧急修复
docker-compose restart db
sleep 20

# 检查数据库连接
if docker-compose exec -T db pg_isready -U prod_user; then
    echo "数据库连接正常"

    # 运行一致性检查
    docker-compose exec -T db psql -U prod_user -c "
    SELECT schemaname, tablename, attname, n_distinct, correlation
    FROM pg_stats
    WHERE schemaname = 'public';"
else
    echo "数据库连接失败，需要进一步处理"
    ./scripts/notify-team.sh "数据库连接失败" error
fi
```

## 📊 监控和告警

### 关键指标监控
1. **系统可用性**
   - 服务在线状态
   - 健康检查成功率
   - 网络连通性

2. **性能指标**
   - API响应时间
   - 数据库查询时间
   - 缓存命中率

3. **资源使用**
   - CPU使用率
   - 内存使用率
   - 磁盘使用率
   - 网络带宽

4. **业务指标**
   - 请求成功率
   - 错误率统计
   - 用户活跃度

### 自动告警规则
```yaml
# Prometheus告警规则示例
groups:
  - name: emergency_alerts
    rules:
      - alert: SystemDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "系统服务宕机"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "错误率过高"

      - alert: HighResourceUsage
        expr: cpu_usage > 0.9
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "资源使用率过高"
```

## 🔄 事后处理流程

### 问题分析
1. **根本原因分析**
   - 收集相关日志
   - 分析时间线
   - 确定触发因素

2. **影响评估**
   - 用户影响范围
   - 业务损失评估
   - 数据影响分析

3. **解决措施**
   - 立即修复措施
   - 长期改进方案
   - 预防措施制定

### 改进计划
1. **流程改进**
   - 优化响应流程
   - 完善监控告警
   - 更新应急预案

2. **技术改进**
   - 系统架构优化
   - 性能调优
   - 安全加固

3. **团队培训**
   - 应急响应培训
   - 技术技能提升
   - 流程演练

## 📋 应急检查清单

### 系统检查
- [ ] 服务状态正常
- [ ] 数据库连接正常
- [ ] 缓存服务正常
- [ ] 监控系统正常
- [ ] 日志收集正常

### 性能检查
- [ ] API响应时间正常
- [ ] 系统资源使用正常
- [ ] 数据库查询性能正常
- [ ] 网络连接正常

### 安全检查
- [ ] 无异常访问
- [ ] 无安全漏洞
- [ ] 权限配置正常
- [ ] 数据加密正常

### 业务检查
- [ ] 核心功能正常
- [ ] 数据一致性正常
- [ ] 用户体验正常
- [ ] 业务指标正常

## 📞 应急联系流程

1. **发现紧急情况**
   - 监控自动告警
   - 用户反馈
   - 人工检查发现

2. **立即通知**
   - 联系技术负责人
   - 启动应急响应团队
   - 记录问题开始时间

3. **协同处理**
   - 分工处理不同方面
   - 定期同步进展
   - 及时更新状态

4. **问题解决**
   - 验证解决方案
   - 确认系统恢复
   - 通知相关人员

5. **事后总结**
   - 编写事故报告
   - 分析改进方案
   - 更新应急预案

---

*最后更新: 2025-10-22*