# Dockerfile - V106.0 多阶段生产级构建
# ==========================================
# Build 阶段：构建依赖和字节码
# Runtime 阶段：最小化运行时镜像

# ============================================================================
# Stage 1: Builder - 构建依赖
# ============================================================================
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY pyproject.toml .
COPY ruff.toml .
COPY mypy.ini .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级 pip 并安装依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# 预编译 Python 字节码（减少运行时启动时间）
RUN python -m compileall -q /opt/venv/lib/python3.11/site-packages

# ============================================================================
# Stage 2: Runtime - 最小化运行时
# ============================================================================
FROM python:3.11-slim AS runtime

# 创建非特权用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 仅安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从 builder 阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    DOCKER_ENV=true

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要的目录
RUN mkdir -p /app/logs /app/model_zoo /app/data && \
    chown -R appuser:appuser /app

# 切换到非特权用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 默认命令
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
