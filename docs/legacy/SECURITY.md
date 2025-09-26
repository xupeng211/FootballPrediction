# 足球预测系统安全文档

## 概述

本文档描述了足球预测系统的安全架构、权限控制机制、审计功能和合规要求。系统采用多层安全防护策略，确保数据安全和业务连续性。

## 📋 目录

- [权限审计与合规](#权限审计与合规)
- [用户认证与授权](#用户认证与授权)
- [数据加密与保护](#数据加密与保护)
- [网络安全](#网络安全)
- [安全监控与告警](#安全监控与告警)
- [应急响应](#应急响应)
- [合规检查清单](#合规检查清单)

---

## 权限审计与合规

### 🎯 审计目标

足球预测系统实施全面的权限审计机制，旨在：

- **合规性保证**：满足数据保护法规要求（如GDPR、SOX等）
- **安全监控**：实时监控敏感操作和异常行为
- **责任追溯**：提供完整的操作审计轨迹
- **风险管控**：识别和预防潜在的安全威胁

### 📊 审计日志结构

#### 核心审计表：`audit_logs`

```sql
-- 审计日志表结构
CREATE TABLE audit_logs (
    -- 基础信息
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 用户身份信息
    user_id VARCHAR(100) NOT NULL,
    username VARCHAR(100),
    user_role VARCHAR(50),
    session_id VARCHAR(100),

    -- 操作信息
    action VARCHAR(50) NOT NULL,          -- CREATE/READ/UPDATE/DELETE/GRANT/REVOKE等
    severity VARCHAR(20) NOT NULL,        -- LOW/MEDIUM/HIGH/CRITICAL
    table_name VARCHAR(100),
    column_name VARCHAR(100),
    record_id VARCHAR(100),

    -- 数据变更追踪
    old_value TEXT,
    new_value TEXT,
    old_value_hash VARCHAR(64),           -- 敏感数据哈希
    new_value_hash VARCHAR(64),           -- 敏感数据哈希

    -- 请求上下文
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_path VARCHAR(500),
    request_method VARCHAR(10),

    -- 执行结果
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    duration_ms INTEGER,

    -- 扩展信息
    metadata JSONB,
    tags VARCHAR(500),

    -- 合规分类
    compliance_category VARCHAR(100),     -- PII/ACCESS_CONTROL/DATA_PROTECTION/FINANCIAL/GENERAL
    retention_period_days INTEGER DEFAULT 2555,  -- 7年保留期
    is_sensitive BOOLEAN DEFAULT FALSE
);
```

#### 审计操作类型分类

| 操作类型 | 严重级别 | 描述 | 示例 |
|---------|---------|------|------|
| **CREATE** | MEDIUM | 创建新记录 | 创建用户、添加比赛数据 |
| **READ** | LOW | 读取数据 | 查询比赛结果、获取赔率 |
| **UPDATE** | MEDIUM | 更新记录 | 修改用户信息、更新比分 |
| **DELETE** | HIGH | 删除记录 | 删除用户、清理历史数据 |
| **GRANT** | HIGH | 授予权限 | 赋予数据库访问权限 |
| **REVOKE** | HIGH | 撤销权限 | 撤销用户权限 |
| **LOGIN** | LOW | 用户登录 | 系统登录认证 |
| **LOGOUT** | LOW | 用户登出 | 退出系统 |
| **BACKUP** | CRITICAL | 数据备份 | 数据库备份操作 |
| **RESTORE** | CRITICAL | 数据恢复 | 从备份恢复数据 |
| **SCHEMA_CHANGE** | CRITICAL | 架构变更 | 修改表结构、索引 |
| **CONFIG_CHANGE** | HIGH | 配置变更 | 修改系统配置 |

### 🔒 敏感数据保护

#### 敏感数据识别

系统自动识别以下类型的敏感数据：

**敏感表**：
- `users` - 用户信息表
- `permissions` - 权限配置表
- `tokens` - 访问令牌表
- `api_keys` - API密钥表
- `user_profiles` - 用户档案表
- `payment_info` - 支付信息表

**敏感字段**：
- `password` - 密码相关字段
- `token` - 令牌字段
- `secret` - 密钥字段
- `key` - 密钥字段
- `email` - 邮箱地址
- `phone` - 电话号码
- `ssn` - 社会保障号
- `credit_card` - 信用卡信息
- `bank_account` - 银行账户信息

#### 敏感数据处理策略

```python
# 敏感数据处理流程
if is_sensitive_data(table_name, column_name):
    # 1. 对原始值进行SHA256哈希
    value_hash = hashlib.sha256(original_value.encode()).hexdigest()

    # 2. 在日志中使用掩码
    logged_value = "[SENSITIVE]"

    # 3. 存储哈希值用于数据完整性验证
    audit_log.old_value_hash = value_hash
    audit_log.old_value = logged_value
```

### 📈 合规要求与标准

#### 数据保护法规合规

**GDPR (通用数据保护条例)**
- ✅ 数据主体权利：提供数据访问、修改、删除的审计记录
- ✅ 数据最小化：仅记录必要的审计信息
- ✅ 数据保留：默认7年保留期，可根据法规要求调整
- ✅ 数据安全：敏感数据哈希存储，防止明文泄露

**SOX (萨班斯-奥克斯利法案)**
- ✅ 财务数据审计：所有财务相关数据变更完整记录
- ✅ 内部控制：权限变更和系统配置变更审计
- ✅ 管理层责任：高级管理员操作特别标记

**HIPAA (健康保险便携性和责任法案)**
- ✅ 访问控制：详细的数据访问日志
- ✅ 审计日志：完整的操作审计轨迹
- ✅ 数据完整性：哈希验证确保数据未被篡改

#### 行业标准合规

**ISO 27001 信息安全管理**
- ✅ 访问管理：完整的权限审计
- ✅ 事件管理：安全事件记录和分析
- ✅ 业务连续性：审计日志备份和恢复

**PCI DSS 支付卡行业数据安全标准**
- ✅ 访问控制：用户权限变更审计
- ✅ 监控测试：持续的安全监控
- ✅ 信息安全策略：完整的安全政策执行

### 🛠️ 审计日志管理

#### 自动审计装饰器

系统提供多种装饰器，实现自动审计：

```python
from src.services.audit_service import audit_create, audit_update, audit_delete

# API层审计
@audit_create("users")
async def create_user(user_data: dict, request: Request):
    """创建用户 - 自动记录审计日志"""
    # 用户创建逻辑
    pass

@audit_update("users")
async def update_user(user_id: int, user_data: dict, request: Request):
    """更新用户 - 自动记录变更审计"""
    # 用户更新逻辑
    pass

@audit_delete("users")
async def delete_user(user_id: int, request: Request):
    """删除用户 - 记录高风险操作审计"""
    # 用户删除逻辑
    pass
```

#### 手动审计记录

对于复杂业务逻辑，支持手动记录：

```python
from src.services.audit_service import audit_service

# 手动记录审计日志
await audit_service.log_operation(
    action="CUSTOM_OPERATION",
    table_name="business_rules",
    record_id="rule_123",
    old_value="old_rule_config",
    new_value="new_rule_config",
    metadata={
        "business_context": "risk_rule_update",
        "approval_id": "approval_456"
    }
)
```

#### 审计日志查询接口

```python
# 获取用户操作历史
user_summary = await audit_service.get_user_audit_summary(
    user_id="user123",
    days=30
)

# 获取高风险操作
high_risk_ops = await audit_service.get_high_risk_operations(
    hours=24,
    limit=100
)
```

### 📊 监控与告警

#### Prometheus 监控指标

```prometheus
# 高危操作计数
football_audit_high_risk_operations_total{user_id, action, severity}

# 审计日志总量
football_audit_logs_total{table_name, action}

# 失败操作计数
football_audit_failed_operations_total{user_id, table_name, action}

# 敏感数据访问计数
football_audit_sensitive_operations_total{table_name, user_id}

# 操作耗时分布
football_audit_operation_duration_seconds{table_name, action}
```

#### 告警规则配置

```yaml
# 高危操作告警
- alert: HighRiskOperationDetected
  expr: increase(football_audit_high_risk_operations_total[5m]) > 0
  for: 0s
  labels:
    severity: warning
  annotations:
    summary: "检测到高危操作"
    description: "用户 {{ $labels.user_id }} 执行了 {{ $labels.action }} 操作"

# 批量删除告警
- alert: BulkDeleteOperation
  expr: increase(football_audit_delete_operations_total[1m]) > 10
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "检测到批量删除操作"
    description: "1分钟内删除操作超过10次，可能存在异常"

# 权限变更告警
- alert: PermissionChanged
  expr: increase(football_audit_permission_changes_total[1m]) > 0
  for: 0s
  labels:
    severity: warning
  annotations:
    summary: "权限变更检测"
    description: "检测到权限授予或撤销操作"

# 失败操作率告警
- alert: HighFailureRate
  expr: rate(football_audit_failed_operations_total[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "操作失败率过高"
    description: "5分钟内操作失败率超过10%"
```

### 📋 报告生成流程

#### 自动化报告

**日报生成**（每日凌晨2:00执行）：
```bash
# 生成日报脚本
python scripts/generate_daily_audit_report.py --date=$(date -d "yesterday" +%Y-%m-%d)
```

**周报生成**（每周一凌晨3:00执行）：
```bash
# 生成周报脚本
python scripts/generate_weekly_audit_report.py --week=$(date -d "last week" +%Y-W%U)
```

**月报生成**（每月1日凌晨4:00执行）：
```bash
# 生成月报脚本
python scripts/generate_monthly_audit_report.py --month=$(date -d "last month" +%Y-%m)
```

#### 报告内容结构

**高层管理报告**：
- 系统安全态势概览
- 高风险操作统计
- 合规性评估结果
- 安全事件摘要
- 改进建议

**技术详细报告**：
- 详细操作日志分析
- 用户行为分析
- 系统性能影响评估
- 异常模式识别
- 技术建议

**合规专项报告**：
- 法规合规性检查
- 数据保护措施评估
- 审计轨迹完整性验证
- 合规差距分析
- 整改计划

#### 报告分发机制

```python
# 报告分发配置
REPORT_DISTRIBUTION = {
    "daily": {
        "recipients": ["security-team@company.com"],
        "format": ["pdf", "json"],
        "retention_days": 90
    },
    "weekly": {
        "recipients": ["management@company.com", "security-team@company.com"],
        "format": ["pdf", "excel"],
        "retention_days": 365
    },
    "monthly": {
        "recipients": ["ceo@company.com", "ciso@company.com", "audit-committee@company.com"],
        "format": ["pdf", "powerpoint"],
        "retention_days": 2555  # 7年
    }
}
```

### 🔧 数据保留与清理

#### 保留策略

| 数据类型 | 保留期限 | 清理策略 | 合规依据 |
|---------|---------|---------|----------|
| **一般审计日志** | 2年 | 自动归档 | 内部政策 |
| **敏感数据审计** | 7年 | 加密存储 | GDPR/SOX要求 |
| **财务相关审计** | 7年 | 离线备份 | SOX法案 |
| **安全事件日志** | 永久 | 冷存储 | 安全政策 |

#### 自动清理机制

```sql
-- 自动清理过期审计日志的存储过程
CREATE OR REPLACE FUNCTION cleanup_expired_audit_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 根据保留期限删除过期日志
    WITH deleted AS (
        DELETE FROM audit_logs
        WHERE timestamp < NOW() - INTERVAL '1 day' * retention_period_days
        AND compliance_category != 'PERMANENT'
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;

    -- 记录清理操作
    INSERT INTO audit_logs (
        user_id, action, table_name,
        metadata, compliance_category
    ) VALUES (
        'system', 'CLEANUP', 'audit_logs',
        jsonb_build_object('deleted_count', deleted_count),
        'SYSTEM_MAINTENANCE'
    );

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

#### 数据归档流程

```bash
# 每月执行的归档脚本
#!/bin/bash
# scripts/archive_audit_logs.sh

ARCHIVE_DATE=$(date -d "1 year ago" +%Y-%m-%d)
ARCHIVE_PATH="/archive/audit_logs"

# 1. 导出历史数据
pg_dump -t audit_logs \
    --where="timestamp < '$ARCHIVE_DATE'" \
    football_prediction > "$ARCHIVE_PATH/audit_logs_$ARCHIVE_DATE.sql"

# 2. 压缩归档文件
gzip "$ARCHIVE_PATH/audit_logs_$ARCHIVE_DATE.sql"

# 3. 上传到云存储
aws s3 cp "$ARCHIVE_PATH/audit_logs_$ARCHIVE_DATE.sql.gz" \
    s3://company-audit-archive/football-prediction/

# 4. 清理本地归档文件（保留云备份）
rm "$ARCHIVE_PATH/audit_logs_$ARCHIVE_DATE.sql.gz"

# 5. 清理数据库中的历史数据
psql football_prediction -c "DELETE FROM audit_logs WHERE timestamp < '$ARCHIVE_DATE';"
```

### 🚨 异常检测与响应

#### 异常行为模式

**用户行为异常**：
- 非工作时间大量操作
- 短时间内大量高风险操作
- 访问非授权数据表
- 异常IP地址登录

**系统操作异常**：
- 批量数据修改
- 频繁的权限变更
- 异常的数据库连接
- 大量操作失败

#### 自动响应机制

```python
# 异常检测触发器
class AnomalyDetectionTrigger:
    async def check_user_behavior(self, user_id: str):
        """检测用户行为异常"""
        # 获取用户最近1小时的操作
        recent_ops = await get_user_operations(user_id, hours=1)

        # 异常检测规则
        if len(recent_ops) > 100:  # 操作频率异常
            await self.trigger_alert("SUSPICIOUS_ACTIVITY", user_id)

        high_risk_ops = [op for op in recent_ops if op.severity in ['HIGH', 'CRITICAL']]
        if len(high_risk_ops) > 5:  # 高风险操作过多
            await self.trigger_alert("HIGH_RISK_PATTERN", user_id)

    async def trigger_alert(self, alert_type: str, user_id: str):
        """触发安全告警"""
        # 1. 记录安全事件
        await log_security_event(alert_type, user_id)

        # 2. 发送即时告警
        await send_security_alert(alert_type, user_id)

        # 3. 可选：临时锁定用户（根据策略）
        if alert_type == "CRITICAL_THREAT":
            await temporarily_lock_user(user_id)
```

### 📋 合规检查清单

#### 月度合规检查

- [ ] **审计日志完整性**
  - [ ] 所有关键操作已记录
  - [ ] 日志数据完整无缺失
  - [ ] 敏感数据正确脱敏

- [ ] **访问控制合规**
  - [ ] 权限最小化原则执行
  - [ ] 定期权限审查完成
  - [ ] 临时权限及时回收

- [ ] **数据保护合规**
  - [ ] 敏感数据加密存储
  - [ ] 数据备份定期测试
  - [ ] 数据保留政策执行

- [ ] **监控告警有效性**
  - [ ] 告警规则覆盖完整
  - [ ] 误报率在可接受范围
  - [ ] 响应时间符合SLA要求

#### 年度合规评估

- [ ] **法规符合性评估**
  - [ ] GDPR合规性全面审查
  - [ ] SOX内控制度评估
  - [ ] 行业标准符合性检查

- [ ] **安全策略更新**
  - [ ] 安全政策年度更新
  - [ ] 应急响应计划演练
  - [ ] 员工安全培训完成

- [ ] **技术架构评估**
  - [ ] 安全架构设计审查
  - [ ] 漏洞扫描和修复
  - [ ] 第三方安全评估

### 🔗 相关文档链接

- [数据设计文档](../architecture/DATA_DESIGN.md) - 数据库架构和权限设计
- [API文档](../reference/API_REFERENCE.md) - 审计API接口说明
- [部署指南](../legacy/DEPLOYMENT.md) - 安全部署配置
- [运维手册](../legacy/OPERATIONS.md) - 安全运维流程

---

*本文档最后更新时间：2025-09-12*
*文档版本：v1.0*
*维护团队：安全工程团队*
