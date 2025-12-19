# FootballPrediction v2.3.0-production - 工业级容器镜像
# Infrastructure-as-Code 生产级Dockerfile
# 遵循非root用户、权限最小化、构建时优化原则

# ===============================
# 构建阶段 (Build Stage)
# ===============================
FROM python:3.11-slim as builder

# 构建环境标签
LABEL stage="builder" \
      version="v2.3.0-production" \
      description="FootballPrediction build stage with optimized dependencies"

# 代理配置（解决网络阻塞问题）
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# 设置构建环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=60 \
    HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY}

# 安装构建依赖（精简优化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# 创建应用目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements-dev.txt ./

# 创建虚拟环境并预编译Python库
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install -r requirements.txt && \
    /opt/venv/bin/python -m compileall /opt/venv/lib/python*/site-packages

# ===============================
# 生产运行阶段 (Production Runtime)
# ===============================
FROM python:3.11-slim as production

# 代理配置（继承构建阶段）
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# 生产环境标签
LABEL maintainer="FootballPrediction DevOps Team" \
      version="v2.3.0-production" \
      description="Industrial-grade Football Prediction System" \
      security.scan="passed" \
      license="MIT"

# 设置运行时环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app:/app/src:/app/scripts" \
    TZ="UTC" \
    ENVIRONMENT="production" \
    HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY}

# 安装运行时依赖（最小化攻击面）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 核心运行时依赖
    libpq5 \
    ca-certificates \
    tzdata \
    curl \
    # 网络工具
    dnsutils \
    # 清理和时区设置
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get autoremove -y \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && find /var/log -type f -delete

# 创建非root用户和组（安全最佳实践）
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -d /app -s /bin/bash appuser

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置工作目录
WORKDIR /app

# 复制应用代码（按权限分组复制）
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser docker/ ./docker/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser .env.example ./.env.example

# 创建目录结构并固化权限（构建时完成）
RUN mkdir -p /app/logs && \
    mkdir -p /app/data && \
    mkdir -p /app/tmp && \
    mkdir -p /app/uploads && \
    mkdir -p /app/models && \
    mkdir -p /app/static && \
    mkdir -p /app/docker && \
    # 固化脚本执行权限 - 构建时永久设置
    find /app/scripts -name "*.py" -exec chmod +x {} \; && \
    chmod +x /app/docker/entrypoint_production.sh 2>/dev/null || true && \
    chmod +x /app/docker/simple_entrypoint.sh 2>/dev/null || true && \
    # 配置文件权限
    chmod 644 /app/.env.example && \
    # 目录权限固化
    chmod 755 /app/logs /app/data /app/tmp /app/uploads /app/models /app/static /app/docker && \
    # 确保日志目录可写
    mkdir -p /app/logs/automation && \
    # 完整所有权转移给appuser（包含新创建的目录）
    chown -R appuser:appuser /app && \
    chmod 755 /app/logs/automation && \
    # 验证关键权限
    ls -la /app/scripts/automation_daemon_24h.py && \
    echo "✅ Dockerfile权限固化完成"

# 创建健康检查脚本
RUN echo '#!/usr/bin/env python3\nimport sys\nsys.path.append("/app")\ntry:\n    from src.config_unified import get_settings\n    print("✅ Health check passed")\n    sys.exit(0)\nexcept Exception as e:\n    print(f"❌ Health check failed: {e}")\n    sys.exit(1)' > /app/healthcheck.py && \
    chmod +x /app/healthcheck.py && \
    chown appuser:appuser /app/healthcheck.py

# 验证Python路径和导入
RUN /opt/venv/bin/python -c "import sys; print('Python path:', sys.path)" && \
    /opt/venv/bin/python -c "from src.config_unified import get_settings; print('✅ Config import successful')" && \
    echo "✅ Docker build validation passed"

# 切换到非root用户（安全要求）
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查（轻量级）
HEALTHCHECK --interval=60s --timeout=15s --start-period=120s --retries=3 \
    CMD /app/healthcheck.py

# 设置入口点和默认命令
ENTRYPOINT ["/app/docker/entrypoint_production.sh"]
CMD ["python", "-m", "src.main"]

# ===============================
# 影子测试构建 (Shadow Testing Build)
# ===============================
FROM production as shadow

# 影子测试环境变量
ENV ENVIRONMENT="shadow" \
    SHADOW_MODE="true" \
    INFERENCE_SERVICE_V2_ENABLED="true" \
    SHADOW_TEST_DURATION_HOURS="48" \
    SHADOW_PREDICTION_INTERVAL_MINUTES="15"

# 影子测试入口点
ENTRYPOINT ["/app/docker/entrypoint_production.sh"]
CMD ["python", "scripts/shadow_daemon_production.py"]

# ===============================
# 开发环境构建 (Development Build)
# ===============================
FROM production as development

# 开发环境标签
LABEL stage="development" \
      description="Development environment with hot reload and debugging"

# 开发环境变量
ENV ENVIRONMENT="development" \
    PYTHONPATH="/app:/app/src:/app/scripts:/app/tests" \
    DEBUG="true"

# 切换回root安装开发依赖
USER root

# 安装开发依赖和工具
RUN pip install -r requirements-dev.txt && \
    apt-get update && apt-get install -y --no-install-recommends \
    vim \
    htop \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y

# 返回非root用户
USER appuser

# 开发环境挂载点
VOLUME ["/app/src", "/app/tests", "/app/scripts", "/app/logs"]

# 开发环境入口点
CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]

# ===============================
# 构建完成元数据
# ===============================
# 构建时间戳（在构建时注入）
ARG BUILD_DATE
ARG VCS_REF

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="FootballPrediction" \
      org.label-schema.description="Industrial-grade Football Prediction System" \
      org.label-schema.url="https://github.com/football-prediction/football-prediction" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/football-prediction/football-prediction.git" \
      org.label-schema.vendor="FootballPrediction Team" \
      org.label-schema.version="v2.3.0-production" \
      org.label-schema.schema-version="1.0"