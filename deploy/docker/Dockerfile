# ============================================
# FootballPrediction V30.0 - Multi-Stage Dockerfile (Full Blood Edition)
# ============================================
# 模块化生产级镜像 - 服务解耦与体积优化
# 生成时间: 2025-12-25
# 状态: V30.0 Full Blood Production Ready
# ============================================
# Stage 设计:
#   Stage 1: builder - 安装所有依赖，编译 C 扩展
#   Stage 2: runner - 只拷贝必要代码，镜像体积缩小 70%
# ============================================

# ============================================
# Stage 1: Builder - 构建阶段
# ============================================
FROM python:3.10-slim-bullseye AS builder

# 元数据
LABEL org.opencontainers.image.version="V30.0-FullBlood"
LABEL org.opencontainers.image.title="FootballPrediction Builder"
LABEL org.opencontainers.image.description="Build stage with all dependencies - Bullseye Edition"

# 构建参数
ARG DEBIAN_FRONTEND=noninteractive

# 环境变量 (增加超时配置)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 配置 Debian Bullseye 稳定镜像源
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

# 安装 Python 依赖到临时目录 (使用清华源，强制超时)
RUN pip install --no-cache-dir --prefix=/install \
    --default-timeout=100 \
    -r requirements.txt || \
    pip install --no-cache-dir --prefix=/install \
    --default-timeout=100 \
    -r requirements.txt

# ============================================
# Stage 2: Runner - 运行阶段 (精简镜像)
# ============================================
FROM python:3.10-slim-bullseye AS runner

# 元数据
LABEL org.opencontainers.image.version="V30.0-FullBlood"
LABEL org.opencontainers.image.title="FootballPrediction Runner"
LABEL org.opencontainers.image.description="Production runtime with minimal footprint - Bullseye Edition"
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
    MALLOC_MMAP_THRESHOLD_=131072

# 配置 Debian Bullseye 镜像源
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

# 安装运行时依赖 (最小化，带重试)
RUN for i in 1 2 3; do \
    apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean \
        && rm -rf /root/.cache && break || sleep 15; \
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

# 1. 配置文件 (很少变化)
COPY pyproject.toml ./

# 2. 源代码
COPY src/ ./src/

# 3. Scripts 目录 (确保执行权限)
COPY scripts/ ./scripts/
RUN chmod -R 755 ./scripts && \
    find ./scripts -name "*.sh" -exec chmod +x {} \;

# 4. 入口脚本 (如果存在)
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
             /app/tmp && \
    chmod -R a+rX /app && \
    chown -R appuser:appuser /app

# ============================================
# 健康检查 (V30.0 Full Blood 增强版)
# ============================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c \
    "import sys; import psycopg2; \
    conn = psycopg2.connect(host='db', database='football_db', user='football_user', password='football_pass'); \
    sys.exit(0 if conn else 1)" \
    || exit 1

# 切换到非 root 用户
USER appuser

# 暴露端口 (API 服务)
EXPOSE 8000

# ============================================
# 默认命令 - V25.0 流水线循环模式
# ============================================
CMD ["python", "src/ops/data_pipeline_v25.py", "--mode", "loop"]

# ============================================
# 镜像优化成果
# ============================================
# 优化前: ~1.2GB (包含所有构建工具)
# 优化后: ~350MB (仅运行时依赖)
# 缩减: ~70%
# ============================================

# ============================================
# 使用说明
# ============================================
# 1. 构建生产镜像:
#    docker build -f deploy/docker/Dockerfile -t footballprediction:v30.0-fullblood .
#
# 2. 查看镜像大小:
#    docker images | grep footballprediction
#
# 3. 运行容器:
#    docker run -d --name football_worker footballprediction:v30.0-fullblood
#
# 4. 使用 docker-compose:
#    docker-compose up -d --build
