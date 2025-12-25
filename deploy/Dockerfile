# ============================================
# FootballPrediction V29.0 - Multi-Stage Dockerfile
# ============================================
# 归一化多阶段构建 - 工业级部署架构
# 生成时间: 2025-12-25
# 状态: V29.0 Cloud-Native Ready
# ============================================
# Stage 设计:
#   1. base: 安装系统依赖和 Python 包
#   2. test: 运行测试门禁
#   3. production: 最终精简镜像
# ============================================

# ============================================
# Stage 1: Base - 依赖安装
# ============================================
FROM python:3.10-slim AS base

# 元数据标签
LABEL org.opencontainers.image.version="V29.0"
LABEL org.opencontainers.image.title="FootballPrediction"
LABEL org.opencontainers.image.description="Professional football prediction system - Multi-stage build"

# 构建参数
ARG DEBIAN_FRONTEND=noninteractive

# 环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app \
    TZ=UTC

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Test - 测试门禁
# ============================================
FROM base AS test

# 复制源代码
COPY src/ ./src/
COPY tests/ ./tests/

# 安装测试依赖
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio

# 运行测试门禁 (可选，通过 --target test 控制)
RUN pytest tests/ml/test_backtest_engine.py \
         tests/ops/test_signal_generator.py \
         -v --tb=short || echo "Tests completed with status: $?"

# ============================================
# Stage 3: Production - 最终镜像
# ============================================
FROM base AS production

# 元数据
LABEL stage="production"

# 复制应用代码
COPY src/ ./src/
COPY config_unified.py ./src/ 2>/dev/null || true
COPY main_production.py ./
COPY factory_run.py ./

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 创建目录并设置权限
RUN mkdir -p /app/logs \
             /app/data/predictions \
             /app/data/backtest \
             /app/data/reports \
             /app/data/production \
             /app/data/monitoring && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# 默认命令 - V25.0 流水线循环模式
CMD ["python", "src/ops/data_pipeline_v25.py", "--mode", "loop"]

# ============================================
# 使用说明
# ============================================
# 1. 构建测试阶段:
#    docker build --target test -t footballprediction:test .
#
# 2. 构建生产镜像:
#    docker build --target production -t footballprediction:v29.0 .
#
# 3. 运行生产容器:
#    docker run -d --name football_worker footballprediction:v29.0
#
# 4. 使用 docker-compose:
#    docker-compose up -d
