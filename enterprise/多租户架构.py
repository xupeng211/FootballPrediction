# 多租户架构
# 阶段: 阶段5
# 生成时间: 2025-10-26 20:06:38
# 描述: 多租户架构 配置

多租户架构:
  enabled: true
  version: "1.0.0"

  # 服务配置
  service:
    name: "多租户架构"
    port: 8000
    replicas: 3

  # 资源限制
  resources:
    requests:
      memory: "256Mi"
      cpu: "250m"
    limits:
      memory: "512Mi"
      cpu: "500m"

  # 健康检查
  health:
    path: "/health"
    interval: 30
    timeout: 10

  # 环境变量
  environment:
    ENV: "production"
    LOG_LEVEL: "INFO"
