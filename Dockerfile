# 足球预测系统 Docker 镜像
# 多阶段构建 - 分离构建环境和运行环境，优化镜像体积和安全性

# ===============================
# 构建阶段 (Build Stage)
# ===============================
FROM python:3.11-slim as builder

# 设置构建环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements-dev.txt ./

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级pip并安装依赖
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ===============================
# 运行阶段 (Runtime Stage)
# ===============================
FROM python:3.11-slim as runtime

# 设置运行时标签
LABEL maintainer="FootballPrediction Team" \
      version="1.0.0" \
      description="Football Prediction System with Async Database Pool" \
      org.opencontainers.image.source="https://github.com/football-prediction/football-prediction"

# 设置运行时环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    TZ="UTC"

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    curl \
    ca-certificates \
    tzdata \
    libpq5 \
    # 时区设置
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    # 清理apt缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 创建非root用户 (安全性要求)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 创建应用目录结构
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用代码 - v2.3-production 架构更新
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser docker/entrypoint_production.sh ./entrypoint.sh
COPY --chown=appuser:appuser docker/simple_entrypoint.sh ./docker/simple_entrypoint.sh

# 复制配置文件
COPY docker/.env.example ./.env.example

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/data /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod +x /app/entrypoint.sh /app/docker/simple_entrypoint.sh && \
    chmod +x /app/scripts/*.py

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /app/healthcheck.py

# 设置入口点
ENTRYPOINT ["/app/entrypoint.sh"]

# 默认命令
CMD ["python", "-m", "src.main"]

# ===============================
# 开发环境构建 (Development Build)
# ===============================
FROM runtime as development

# 开发环境额外依赖
USER root
RUN pip install -r requirements-dev.txt
USER appuser

# 开发环境挂载点
VOLUME ["/app/src", "/app/tests", "/app/scripts"]

# 开发环境入口点
CMD ["python", "-m", "pytest", "tests/", "-v"]
