# ============================================
# FootballPrediction V20.3 - Production Dockerfile
# ============================================
# 工业化部署镜像 - 优化体积和安全性
# 生成时间: 2025-12-24
# 状态: V20.3 Production Ready
# ============================================

FROM python:3.11-slim

# 元数据标签
LABEL org.opencontainers.image.version="V20.3"
LABEL org.opencontainers.image.title="FootballPrediction"
LABEL org.opencontainers.image.description="Professional football prediction system - V20.3"

# 环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app \
    TZ=UTC \
    LOG_DIR=/app/logs \
    DATA_DIR=/app/data

# 工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制应用代码（必须在安装依赖之前，因为 pyproject.toml 引用了 src）
COPY src/ ./src/
COPY pyproject.toml requirements.txt requirements-dev.txt ./
COPY main_production.py ./
COPY factory_run.py ./
COPY verify_ready.sh ./
COPY system_verify.sh ./

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .[all]

# 创建非 root 用户
RUN useradd -r -m -d /app -s /sbin/nologin appuser

# 创建目录并设置权限
RUN mkdir -p /app/logs /app/data /app/data/production /app/data/backups && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 默认命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
