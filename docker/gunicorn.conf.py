# =================================================================
# Gunicorn生产环境配置
# Production Gunicorn Configuration
# =================================================================

import multiprocessing
import os

# 服务器套接字
bind = "0.0.0.0:8000"
backlog = 2048

# 工作进程
workers = int(os.environ.get("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 30
keepalive = 2

# 重启
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 日志
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "football-prediction"

# 安全
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL（如果需要）
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# 监控
statsd_host = os.environ.get("STATSD_HOST", None)
statsd_prefix = "football-prediction"

# 优雅关闭
graceful_timeout = 30
timeout = 30

# 调试（仅开发环境）
if os.environ.get("ENV") == "development":
    reload = True
    accesslog = "-"
    loglevel = "debug"
else:
    reload = False