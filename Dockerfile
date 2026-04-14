# =============================================================================
# FootballPrediction - 生产同构镜像
# =============================================================================
# 目标:
# 1. 保持 Python API 运行时
# 2. 补齐 Node.js / Playwright / Chromium 运行时
# 3. 让 CI、开发容器与生产收割环境具备更高一致性
# =============================================================================

FROM node:20-bookworm-slim AS node-builder

WORKDIR /build

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY package.json package-lock.json ./

RUN npm ci --omit=dev --ignore-scripts \
    && npx playwright install chromium \
    && npm cache clean --force


FROM python:3.11-slim-bookworm AS python-builder

WORKDIR /build

RUN apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update \
    && apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY mcp_servers/requirements.txt ./mcp_servers-requirements.txt

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt -r mcp_servers-requirements.txt \
    && python -m compileall -q /opt/venv/lib/python3.11/site-packages


FROM python:3.11-slim-bookworm AS runtime

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    NODE_ENV=production \
    DOCKER_ENV=true \
    TZ=Asia/Shanghai

RUN apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update \
    && apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 install -y --no-install-recommends \
    libpq5 \
    curl \
    tini \
    ca-certificates \
    fonts-liberation \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    fontconfig \
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
    libgl1 \
    libglx0 \
    libegl1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && fc-cache -fv

COPY --from=python-builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=node-builder /usr/local/bin/npm /usr/local/bin/npm
COPY --from=node-builder /usr/local/bin/npx /usr/local/bin/npx
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-builder --chown=appuser:appuser /build/node_modules /app/node_modules
COPY --from=node-builder --chown=appuser:appuser /ms-playwright /ms-playwright

COPY --chown=appuser:appuser . .

RUN install -d -o appuser -g appuser /app/logs /app/model_zoo /app/data

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
