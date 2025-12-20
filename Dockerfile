# FootballPrediction - 极简全栈容器化基座
# 云原生架构师设计 - 开箱即用数据帝国

FROM python:3.11-slim

# 环境标签
LABEL maintainer="CloudNative Architect" \
      version="v1.0-minimal" \
      description="Football Prediction System - Cloud Native Stack"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    TZ=UTC

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 核心依赖
    libpq-dev \
    gcc \
    curl \
    postgresql-client \
    # 清理
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# 设置工作目录
WORKDIR /app

# 复制并安装Python依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install -r requirements.txt && \
    pip install aiohttp

# 创建非root用户 (使用UID/GID 1000以避免权限冲突)
RUN groupadd -r -g 1000 appuser && \
    useradd -r -g appuser -u 1000 -d /app -s /bin/bash appuser

# 创建必要目录并设置正确权限
RUN mkdir -p /app/logs /app/data /app/models /app/src /app/scripts && \
    chmod -R 755 /app && \
    chown -R appuser:appuser /app

# 先复制所有应用代码
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY requirements.txt ./

# 修复权限 - 确保所有文件属于appuser
RUN chown -R 1000:1000 /app && \
    find /app -type f -name "*.py" -exec chmod +x {} \;

# 创建健康检查脚本
RUN echo '#!/usr/bin/env python3\nimport sys\nsys.path.append("/app")\ntry:\n    from src.config_unified import get_settings\n    print("✅ Container health check passed")\n    sys.exit(0)\nexcept Exception as e:\n    print(f"❌ Container health check failed: {e}")\n    sys.exit(1)' > /app/healthcheck.py && \
    chmod +x /app/healthcheck.py

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /app/healthcheck.py

# 默认命令（可被docker-compose覆盖）
CMD ["python", "main_engine_v5.py", "--mode", "test"]