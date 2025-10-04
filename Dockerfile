# 多阶段构建 - 构建阶段
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements/ ./requirements/

# 安装Python依赖
RUN pip install --no-cache-dir --user -r requirements/requirements.lock

# 生产阶段
FROM python:3.11-slim as production

ARG APP_VERSION=dev

# 创建非root用户
RUN groupadd -g 1001 appuser && \
    useradd -r -u 1001 -g appuser appuser

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置工作目录
WORKDIR /app

# 从构建阶段复制Python包
COPY --from=builder /root/.local /home/appuser/.local

# 复制应用代码
COPY . .

# 复制入口脚本
COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 设置Python路径
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV APP_VERSION=${APP_VERSION}

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
