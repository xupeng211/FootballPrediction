# 🚀 足球预测系统部署指南

## 📋 目录
- [环境要求](#环境要求)
- [本地开发部署](#本地开发部署)
- [AWS生产部署](#aws生产部署)
- [GitHub配置](#github配置)
- [监控和维护](#监控和维护)
- [故障排除](#故障排除)

## 🔧 环境要求

### 本地开发环境
- **操作系统**: Ubuntu 20.04+ / macOS 11+ / Windows 10+
- **Python**: 3.11+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.30+

### 云服务要求
- **AWS账号**: 具备ECS、RDS、ECR权限
- **GitHub账号**: 用于代码托管和CI/CD
- **域名** (可选): 用于生产环境访问

## 🏠 本地开发部署

### 1. 项目克隆和初始化
```bash
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 复制环境配置文件
cp env.template .env

# 编辑环境变量 (重要!)
vim .env  # 或使用你喜欢的编辑器
```

### 2. 配置环境变量
编辑 `.env` 文件，重点配置：
```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction_dev
DB_USER=football_user
DB_PASSWORD=your_secure_password_here

# API密钥 (必须申请)
API_FOOTBALL_KEY=your_api_football_key_here

# 其他配置
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 3. 一键部署
```bash
# 给脚本执行权限
chmod +x scripts/deploy.sh

# 启动开发环境
./scripts/deploy.sh development
```

### 4. 验证部署
部署成功后访问：
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **数据库**: localhost:5432
- **Redis**: localhost:6379

## ☁️ AWS生产部署

### 1. 前置准备

#### AWS服务配置
1. **创建ECR仓库**：
```bash
aws ecr create-repository --repository-name football-prediction
```

2. **创建RDS PostgreSQL实例**：
```bash
aws rds create-db-instance \
    --db-instance-identifier football-prediction-prod \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username football_user \
    --master-user-password YOUR_SECURE_PASSWORD \
    --allocated-storage 20
```

3. **创建ElastiCache Redis集群**：
```bash
aws elasticache create-cache-cluster \
    --cache-cluster-id football-prediction-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1
```

### 2. GitHub Secrets配置

在GitHub仓库的 `Settings > Secrets and variables > Actions` 中添加：

#### AWS凭证
```
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
```

#### Docker Hub凭证 (可选)
```
DOCKERHUB_USERNAME=your_dockerhub_username
DOCKERHUB_TOKEN=your_dockerhub_token
```

#### 应用密钥
```
API_FOOTBALL_KEY=your_api_football_key
JWT_SECRET_KEY=your_super_secret_jwt_key

# 生产环境数据库
PROD_DATABASE_URL=postgresql://user:pass@host:5432/dbname
STAGING_DATABASE_URL=postgresql://user:pass@host:5432/dbname_staging

# 网络配置
PROD_SUBNET_IDS=subnet-12345,subnet-67890
STAGING_SUBNET_IDS=subnet-abc,subnet-def
PROD_SECURITY_GROUP_ID=sg-production
STAGING_SECURITY_GROUP_ID=sg-staging
```

### 3. 部署流程

#### 自动部署 (推荐)
```bash
# 推送到develop分支 → 自动部署到staging
git checkout develop
git push origin develop

# 推送到main分支 → 自动部署到production
git checkout main
git merge develop
git push origin main
```

#### 手动部署
在GitHub Actions中选择 "Deploy to AWS" workflow，手动触发部署。

### 4. 网络与传输安全加固

> 生产环境必须通过 HTTPS + WAF 防护暴露服务，以下步骤默认目标区域为 `us-east-1`，可按需调整。

1. **申请 TLS 证书（AWS ACM）**
   ```bash
   aws acm request-certificate \
     --domain-name api.footballpred.com \
     --validation-method DNS \
     --subject-alternative-names "*.api.footballpred.com"
   ```
   - 在 Route 53 中添加 ACM 提供的 CNAME 记录完成验证。
   - 证书颁发后记录 `CertificateArn`，在 ALB / CloudFront 中引用。

2. **配置应用负载均衡 (ALB)**
   - 监听端口 `443`，关联上一步的 ACM 证书。
   - 创建 HTTP(80) 监听器，仅用于 301 重定向到 HTTPS。
   - 启用 `ELBSecurityPolicy-TLS13-1-2-2021-06` 只允许 TLS 1.2+。
   - 打开 ALB 访问日志与指标：
     ```bash
     aws elbv2 modify-load-balancer-attributes \
       --load-balancer-arn $ALB_ARN \
       --attributes Key=access_logs.s3.enabled,Value=true,Key=access_logs.s3.bucket,Value=footballpred-alb-logs
     ```

3. **部署 AWS WAF 规则**
   ```bash
   aws wafv2 create-web-acl \
     --name footballpred-waf \
     --scope REGIONAL \
     --default-action Block={} \
     --rules file://docs/security/waf-managed-rules.sample.json \
     --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=footballpred
   ```
   - 根据业务需求复制并调整 `docs/security/waf-managed-rules.sample.json` 定义自有托管/自定义规则集。
   - 推荐启用托管规则：AWSManagedRulesCommonRuleSet、KnownBadInputs、SQLi/XSS。
   - 添加自定义规则：
     - IP 黑白名单 (`aws wafv2 create-ip-set`)
     - 速率限制 (`RateBasedStatement`，如 200 req/5min)
   - 将 WebACL 关联至 ALB：
     ```bash
     aws wafv2 associate-web-acl --web-acl-arn $WAF_ARN --resource-arn $ALB_ARN
     ```

4. **安全组与网络分段**
   - ALB 安全组：仅开放 `80/443`，来源限定为公网或 CDN IP 段。
   - ECS/Fargate 安全组：只允许来自 ALB 安全组的 `8080`/健康检查端口，出站仅指向 RDS、Redis、MLflow。
   - RDS、Redis 安全组：拒绝公网访问，仅允许应用安全组入站。

5. **Nginx 反向代理 (容器内)**
   - 在 `nginx/production.conf` 中启用 `proxy_set_header X-Forwarded-Proto https` 并强制 `Strict-Transport-Security`：
     ```nginx
     add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
     ```
   - 开启 `proxy_buffering off` 与 `limit_req_zone` 基于 IP 的速率控制。

6. **Secrets 与凭证管理**
   - 使用 AWS Secrets Manager/SSM Parameter Store，而不是 `.env` 持久化敏感信息。
   - 在部署脚本中通过 `aws secretsmanager get-secret-value` 拉取并注入容器环境变量。

7. **持续监控与告警**
   - 订阅 WAF 日志到 CloudWatch Logs，配置异常模式告警（大量 Block、RateLimit 触发等）。
   - 在 CloudWatch 建立 HTTPS 端点探针，结合 `5xx` 指标触发 SNS 告警。
   - 每季度复审 TLS 证书有效期与 WAF 规则命中率。

## 🔒 GitHub配置

### 1. 分支保护规则

为 `main` 分支设置保护规则：

1. 进入 `Settings > Branches`
2. 添加规则：`main`
3. 配置选项：
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Require status checks: `test` (CI pipeline)
   - ✅ Restrict pushes that create files larger than 100MB
   - ✅ Allow force pushes: Admin only

### 2. Webhook配置 (可选)
如果需要部署通知：
1. 进入 `Settings > Webhooks`
2. 添加webhook URL (Slack/Discord/钉钉)
3. 选择事件：`Pushes`, `Pull requests`, `Deployments`

## 📊 监控和维护

### 1. 健康检查监控
```bash
# 本地检查
curl http://localhost:8000/health

# 生产环境检查
curl https://api.footballpred.com/health
```

### 2. 日志查看
```bash
# Docker Compose环境
docker-compose logs -f app

# 生产环境 (AWS ECS)
aws logs tail /ecs/football-prediction --follow
```

### 3. 数据库维护
```bash
# 本地数据库迁移
docker-compose exec app alembic upgrade head

# 生产环境迁移 (通过CI/CD自动执行)
# 或者手动执行：
aws ecs run-task --cluster production --task-definition migration-task
```

### 4. 性能监控
- **应用性能**: 通过 `/health` 端点监控响应时间
- **数据库性能**: 监控连接数和查询时间
- **资源使用**: 监控CPU和内存使用率

## 🚨 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 检查日志
docker-compose logs app

# 常见原因：
# - 环境变量配置错误
# - 数据库连接失败
# - 端口占用
```

#### 2. 数据库连接失败
```bash
# 检查数据库状态
docker-compose ps db

# 手动连接测试
docker-compose exec db psql -U football_user -d football_prediction_dev

# 检查网络连接
docker-compose exec app ping db
```

#### 3. API响应异常
```bash
# 检查健康状态
curl http://localhost:8000/health

# 检查日志详情
docker-compose logs -f app | grep ERROR

# 重启服务
docker-compose restart app
```

#### 4. CI/CD失败
1. 检查GitHub Actions日志
2. 验证Secrets配置
3. 检查Docker镜像构建
4. 验证AWS权限

### 回滚操作

#### 本地环境回滚
```bash
# 停止服务
docker-compose down

# 回滚到上一个提交
git reset --hard HEAD~1

# 重新部署
./scripts/deploy.sh development
```

#### 生产环境回滚
生产环境回滚会自动触发 (在deploy.yml中配置)，或手动执行：
```bash
# 通过GitHub Actions手动回滚
# 或通过AWS ECS控制台回滚到上一个任务定义版本
```

## 📞 获取帮助

### 文档资源
- **API文档**: `/docs` 端点
- **数据库Schema**: `architecture.md`
- **开发指南**: `README.md`

### 问题报告
- 创建GitHub Issue (使用模板)
- 提供详细的错误日志
- 包含环境信息和复现步骤

### 联系方式
- GitHub Issues: 功能请求和Bug报告
- 项目维护者: [@xupeng211](https://github.com/xupeng211)

---

**祝您部署顺利！** 🎉

如果遇到问题，请先查看[故障排除](#故障排除)部分，或创建GitHub Issue寻求帮助。
