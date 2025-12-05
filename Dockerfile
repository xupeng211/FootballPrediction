# 多阶段构建 Dockerfile - 足球预测系统
# 支持开发环境和生产环境的不同需求

# ================== Base 阶段 ==================
FROM mcr.microsoft.com/playwright/python:latest as base

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/home/app/.local/bin:$PATH"

# 更新包源并安装基础系统依赖 (包含Playwright浏览器依赖)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright浏览器必需依赖 (使用标准Ubuntu包名)
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libcairo2 \
    libpango-1.0-0 \
    libasound2 \
    # 基础开发工具
    curl \
    cron \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    python3-dev \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY requirements.txt .
COPY pyproject.toml ./

# 安装生产依赖 (基于 pyproject.toml dependencies)
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
    pandas==2.2.3 \
    numpy==1.26.4 \
    scikit-learn==1.5.2 \
    xgboost==2.0.3 \
    requests==2.31.0 \
    psutil==5.9.8 \
    PyJWT==2.10.1 \
    prometheus-client==0.14.0 \
    mlflow==2.22.2 \
    alembic==1.12.0 \
    asyncpg==0.29.0 \
    celery==5.4.0 \
    playwright==1.56.0 \
    curl_cffi==0.13.0 \
    beautifulsoup4==4.12.3

# 安装Playwright浏览器
RUN playwright install chromium \
    && playwright install-deps \
    && echo "Playwright installation completed successfully"

# ================== Development 阶段 ==================
FROM base as development

# 使用清华镜像源和超时设置批量安装开发工具，提高构建稳定性
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --default-timeout=100 \
    --no-cache-dir \
    --prefer-binary \
    pytest==8.4.0 \
    pytest-asyncio==1.2.0 \
    pytest-cov==7.0.0 \
    pytest-mock==3.14.0 \
    pytest-xdist==3.6.0 \
    factory-boy==3.3.1 \
    ruff==0.14.0 \
    mypy==1.18.2 \
    bandit==1.8.6 \
    black==24.10.0 \
    isort==5.13.2 \
    pre-commit==4.0.1 \
    pip-audit==2.6.0 \
    ipython==8.31.0

# 验证开发工具安装成功
RUN pytest --version && ruff --version && mypy --version

# 设置开发环境特定的环境变量
ENV ENV=development
ENV TESTING=false

# 复制启动脚本和cron配置
COPY scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY scripts/crontab /etc/cron.d/football-cron
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chmod 0644 /etc/cron.d/football-cron

# 复制应用代码
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY models/ ./models/

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 开发环境默认命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ================== Production 阶段 ==================
FROM base as production

# 只复制必要文件
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY models/ ./models/

# 复制启动脚本
COPY scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY scripts/crontab /etc/cron.d/football-cron
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chmod 0644 /etc/cron.d/football-cron

# 设置生产环境特定的环境变量
ENV ENV=production

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8000

# 健康检查 (轻量级)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 设置entrypoint为默认命令 (生产环境使用启动脚本)
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]