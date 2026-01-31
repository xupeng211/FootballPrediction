# ============================================
# FootballPrediction V37.1 - Production Dockerfile
# ============================================
# 工业化生产镜像 - 依赖固化 + 多阶段构建
# 生成时间: 2025-12-29
# 状态: V37.1 Production-Ready
# ============================================
# Stage 设计:
#   Stage 1: builder - 安装依赖，编译 C 扩展
#   Stage 2: runner - 精简运行时，镜像体积最小化
# ============================================

# ============================================
# Stage 1: Builder - 构建阶段
# ============================================
FROM python:3.11-slim AS builder

# 元数据
LABEL org.opencontainers.image.version="V37.1-Production"
LABEL org.opencontainers.image.title="FootballPrediction Builder"
LABEL org.opencontainers.image.description="Production build stage with locked dependencies - Python 3.11"

# 构建参数
ARG DEBIAN_FRONTEND=noninteractive

# 环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 配置镜像源
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

# 安装构建依赖 (带重试机制)
RUN for i in 1 2 3; do \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libpq-dev \
        cmake \
        git \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean && break || sleep 15; \
    done

# 工作目录
WORKDIR /build

# 复制依赖文件
COPY requirements.txt pyproject.toml ./

# 安装 Python 依赖到临时目录 (锁定版本)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --prefix=/install \
    --default-timeout=100 \
    -r requirements.txt

# ============================================
# Stage 2: Runner - 运行阶段 (精简镜像)
# ============================================
FROM python:3.11-slim AS runner

# 元数据
LABEL org.opencontainers.image.version="V37.1-Production"
LABEL org.opencontainers.image.title="FootballPrediction Runner"
LABEL org.opencontainers.image.description="Production runtime with minimal footprint - Python 3.11"
LABEL stage="runner"

# 环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app \
    TZ=UTC \
    LOG_DIR=/app/logs \
    DATA_DIR=/app/data \
    PREDICTION_DIR=/app/data/predictions \
    # 生产优化
    MALLOC_ARENA_MAX=2 \
    MALLOC_MMAP_THRESHOLD_=131072 \
    # V37.0 L2 采集器配置
    MAX_L2_CONCURRENT=3 \
    L2_REQUESTS_PER_SECOND=2

# 配置镜像源
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

# 安装运行时依赖 (最小化)
RUN for i in 1 2 3; do \
    apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean \
        && rm -rf /root/.cache /var/cache/apt /var/lib/apt/lists/* && break || sleep 15; \
    done

# 创建应用用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 从 builder 阶段复制 Python 依赖
COPY --from=builder /install /usr/local

# 工作目录
WORKDIR /app

# ============================================
# 应用代码分层 (优化缓存利用)
# ============================================

# 1. 配置文件
COPY pyproject.toml ./

# 2. 源代码
COPY src/ ./src/

# 3. Scripts 目录
COPY scripts/ ./scripts/
RUN chmod -R 755 ./scripts && \
    find ./scripts -name "*.sh" -exec chmod +x {} \;

# 4. 入口脚本
COPY main_production.py ./

# ============================================
# 创建运行时目录并设置权限
# ============================================
RUN mkdir -p /app/logs \
             /app/data/predictions \
             /app/data/backtest \
             /app/data/reports \
             /app/data/production \
             /app/data/monitoring \
             /app/models \
             /app/model_zoo \
             /app/tmp && \
    chmod -R a+rX /app && \
    chown -R appuser:appuser /app

# ============================================
# 健康检查 (V37.1 增强版)
# ============================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c \
    "import sys; import psycopg2; \
    conn = psycopg2.connect(host='db', database='football_prediction_dev', user='football_user', password='football_pass'); \
    sys.exit(0 if conn else 1)" \
    || exit 1

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# ============================================
# 默认命令 - V37.0 L1/L2 全量采集
# ============================================
CMD ["python", "scripts/collectors/full_l1_l2_harvest.py", "--verbose"]

# ============================================
# 镜像规格
# ============================================
# 基础镜像: python:3.11-slim (~120MB)
# 依赖大小: ~250MB
# 最终镜像: ~370MB
# ============================================

# ============================================
# 使用说明
# ============================================
# 构建:
#   docker build -f deploy/docker/Dockerfile -t footballprediction:v37.1 .
#
# 运行:
#   docker run -d --name football_harvester footballprediction:v37.1
#
# Docker Compose:
#   docker-compose up -d --build
# ============================================
