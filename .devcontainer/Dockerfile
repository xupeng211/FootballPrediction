# =============================================================================
# FootballPrediction - 全程容器化开发环境
# =============================================================================
# 版本: V170.000-dev
# 基础镜像: Python 3.11 + Node.js 20 LTS
# 特性: 热更新、国内镜像源加速、完整开发工具链
# =============================================================================

FROM python:3.11-slim-bookworm

# -----------------------------------------------------------------------------
# 阶段 1: 系统依赖安装（使用阿里云镜像源）
# -----------------------------------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# 替换为阿里云 Debian 镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（编译环境、Git、vim、网络工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 编译工具链
    build-essential \
    gcc \
    g++ \
    make \
    # 数据库客户端库
    libpq-dev \
    libpq5 \
    # 网络工具
    curl \
    wget \
    netcat-openbsd \
    iputils-ping \
    # 版本控制
    git \
    git-lfs \
    # 编辑器
    vim \
    nano \
    # 进程管理
    htop \
    procps \
    # ============================================================
    # V172-L2-04: 浏览器环境补全（Turnstile 绕过）
    # ============================================================
    # 字体库（Canvas 指纹必需）
    fonts-liberation \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    fontconfig \
    # Playwright 完整依赖（避免渲染降级）
    libnss3 \
    libnss3-tools \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # 图形渲染支持
    libgl1 \
    libglx0 \
    libegl1 \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    # 刷新字体缓存
    && fc-cache -fv

# -----------------------------------------------------------------------------
# 阶段 2: Node.js 20 LTS 安装（使用 NodeSource 镜像）
# -----------------------------------------------------------------------------
ENV NODE_VERSION=20

# 安装 Node.js 20 LTS (使用 NodeSource，通过代理加速)
RUN set -eux; \
    if curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -; then \
        apt-get install -y nodejs; \
    else \
        apt-get update; \
        apt-get install -y nodejs npm; \
    fi; \
    if ! command -v npm >/dev/null 2>&1; then \
        apt-get update; \
        apt-get install -y npm; \
    fi; \
    rm -rf /var/lib/apt/lists/*

# 配置 npm 使用淘宝镜像
RUN npm config set registry https://registry.npmmirror.com

# 安装全局开发工具
RUN npm install -g \
    typescript \
    ts-node \
    eslint \
    prettier \
    nodemon \
    pnpm

# 验证 Node.js 安装
RUN node --version && npm --version

# -----------------------------------------------------------------------------
# 阶段 3: Python 环境配置（使用阿里云 pip 镜像）
# -----------------------------------------------------------------------------
WORKDIR /app

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制 Python 依赖清单，确保 docker-compose 开发容器也具备项目运行依赖
COPY requirements.txt pyproject.toml /tmp/python-deps/

# 配置 pip 使用阿里云镜像
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 安装项目依赖和额外开发工具
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    -r /tmp/python-deps/requirements.txt \
    ipython \
    ipdb \
    bandit \
    pre-commit

# -----------------------------------------------------------------------------
# 阶段 4: 环境变量配置
# -----------------------------------------------------------------------------
# Python 配置
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1

# Node.js 配置
ENV NODE_ENV=development \
    NODE_OPTIONS="--max-old-space-size=4096"

# Docker 环境标识
ENV DOCKER_ENV=true \
    DOCKER_DEV_CONTAINER=true

# 代理环境变量（预留接口，容器内使用）
ENV HTTP_PROXY=${HTTP_PROXY:-} \
    HTTPS_PROXY=${HTTPS_PROXY:-} \
    NO_PROXY=${NO_PROXY:-localhost,127.0.0.1} \
    http_proxy=${HTTP_PROXY:-} \
    https_proxy=${HTTPS_PROXY:-}

# 时区
ENV TZ=Asia/Shanghai

# -----------------------------------------------------------------------------
# 阶段 5: Playwright 浏览器（可选，用于数据采集）
# -----------------------------------------------------------------------------
# 注意：Playwright 浏览器较大，首次构建需要时间
# 如需禁用，设置环境变量: INSTALL_PLAYWRIGHT=false
ARG INSTALL_PLAYWRIGHT=true
RUN if [ "$INSTALL_PLAYWRIGHT" = "true" ]; then \
    pip install --no-cache-dir playwright && \
    playwright install chromium --with-deps; \
    fi

# -----------------------------------------------------------------------------
# 阶段 6: 工作目录和权限
# -----------------------------------------------------------------------------
WORKDIR /app

# 创建必要的目录
RUN mkdir -p /app/logs /app/data /app/model_zoo /app/.cache

# 设置 Git 配置（开发环境）
RUN git config --global core.autocrlf input && \
    git config --global core.eol lf && \
    git config --global init.defaultBranch main && \
    git config --global pull.rebase false

# -----------------------------------------------------------------------------
# 阶段 7: 健康检查
# -----------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# -----------------------------------------------------------------------------
# 阶段 8: Tini init 系统 (V175 僵尸进程治理)
# -----------------------------------------------------------------------------
# 安装 tini 作为 PID 1，自动回收孤儿进程
RUN apt-get update && apt-get install -y --no-install-recommends tini && \
    rm -rf /var/lib/apt/lists/*

# tini 作为 entrypoint，确保僵尸进程被正确回收
ENTRYPOINT ["/usr/bin/tini", "--"]

# -----------------------------------------------------------------------------
# 阶段 9: 默认命令
# -----------------------------------------------------------------------------
# 开发模式：保持容器运行
CMD ["sleep", "infinity"]
