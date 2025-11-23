# 后端 Dockerfile - 足球预测系统 (轻量级快速版)
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# 更新包源并安装最小依赖和编译工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    cron \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装完整的 Python 依赖 (基于 pyproject.toml dependencies)
RUN pip install --no-cache-dir --prefer-binary \
    fastapi==0.121.2 \
    uvicorn[standard]==0.38.0 \
    sqlalchemy==2.0.44 \
    pydantic==2.12.4 \
    email-validator==2.0.0 \
    aiosqlite==0.17.0 \
    redis==7.0.1 \
    psycopg2-binary==2.9.11 \
    python-multipart==0.0.20 \
    passlib[bcrypt]==1.7.4 \
    python-dotenv==1.2.1 \
    httpx==0.25.0 \
    aiohttp==3.10.5 \
    backoff==2.2.0 \
    tenacity==8.2.0 \
    pandas==2.3.3 \
    numpy==2.3.4 \
    scikit-learn==1.7.2 \
    xgboost==2.0.3 \
    requests==2.31.0 \
    psutil==5.9.8 \
    PyJWT==2.10.1 \
    prometheus-client==0.14.0 \
    mlflow==2.22.2 \
    alembic==1.12.0 \
    asyncpg==0.29.0

# 复制启动脚本和cron配置 (需要在切换用户之前)
COPY scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY scripts/crontab /etc/cron.d/football-cron
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chmod 0644 /etc/cron.d/football-cron

# 复制应用代码
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY pyproject.toml ./

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8000

# 健康检查 (使用wget替代curl)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 设置entrypoint为默认命令
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]