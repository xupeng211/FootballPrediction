# # syntax=docker/dockerfile:1.4
# 统一Dockerfile - 支持多阶段构建
# 使用方式：
# - 开发：docker build -f docker/Dockerfile --target development ..
# - 生产：docker build -f docker/Dockerfile --target production ..
# - 测试：docker build -f docker/Dockerfile --target test ..

# 基础镜像
FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置工作目录
WORKDIR /app

# ===================
# 开发环境
# ===================
FROM base as development

# 安装开发依赖
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    telnet \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements/ ./requirements/

# 安装Python依赖（开发环境）
RUN pip install -r requirements/dev.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p logs coverage reports

# 设置权限
RUN chown -R 1001:1001 /app
USER 1001

# 暴露端口
EXPOSE 8000 5678

# 默认命令（开发环境）
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===================
# 测试环境
# ===================
FROM development as test

# 安装测试依赖
RUN pip install pytest-testinfra

# 复制测试配置
COPY docker/environments/.env.test .env.test

# 设置测试环境变量
ENV TESTING=true

# 运行测试
CMD ["pytest", "-v", "--cov=src", "--cov-report=html", "--cov-report=term"]

# ===================
# 构建阶段（生产）
# ===================
FROM base as builder

# 复制依赖文件
COPY requirements/ ./requirements/

# 安装依赖到用户目录（利用缓存）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user -r requirements/requirements.lock

# ===================
# 生产环境
# ===================
FROM python:3.11-slim as production

ARG APP_VERSION=dev
ARG BUILD_DATE
ARG GIT_COMMIT
ARG GIT_BRANCH

# 添加标签
LABEL maintainer="your-team@company.com" \
      version="${APP_VERSION}" \
      org.label-schema.build-date="${BUILD_DATE}" \
      org.label-schema.vcs-ref="${GIT_COMMIT}" \
      org.label-schema.vcs-branch="${GIT_BRANCH}" \
      org.label-schema.schema-version="1.0"

# 创建非root用户
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser appuser

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置工作目录
WORKDIR /app

# 从构建阶段复制Python包
COPY --from=builder /root/.local /home/appuser/.local

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p logs tmp && \
    chown -R appuser:appuser /app

# 设置用户
USER appuser

# 确保用户安装的包在PATH中
ENV PATH=/home/appuser/.local/bin:$PATH

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 使用启动脚本
COPY docker/entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# 默认命令（生产环境）
ENTRYPOINT ["entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ===================
# 运行时镜像（最小化）
# ===================
FROM production as runtime

# 移除构建时不需要的文件
RUN rm -rf /app/tests /app/docs /app/.git \
       /app/docker /app/scripts/cleanup /app/archive

# 仅保留运行时必需的文件
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
