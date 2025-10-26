# 缓存架构升级
# 阶段: 阶段2
# 生成时间: 2025-10-26 20:06:38
# 描述: 缓存架构升级 配置

缓存架构升级:
  enabled: true
  version: "1.0.0"

  # 服务配置
  service:
    name: "缓存架构升级"
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
