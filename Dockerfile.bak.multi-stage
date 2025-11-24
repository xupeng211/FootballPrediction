#
# --- 1. Base Stage ---
# 基础镜像，包含所有构建时和运行时共享的系统依赖
#
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 跳过系统包安装，直接使用 Python 基础镜像

WORKDIR /app

#
# --- 2. Builder-Prod Stage ---
# 此阶段用于为 *生产* 环境安装依赖
#
FROM base AS builder-prod
# 配置pip使用清华镜像源并安装pip-tools
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pip-tools

# 复制生产依赖 *锁定* 文件
COPY requirements/prod.txt .

# 创建虚拟环境并安装生产依赖（使用清华镜像源加速）
RUN python -m venv /venv && \
    . /venv/bin/activate && \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r prod.txt

#
# --- 3. Builder-Dev Stage ---
# 此阶段用于为 *开发和测试* 环境安装依赖
#
FROM base AS builder-dev
# 配置pip使用清华镜像源并安装pip-tools
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pip-tools

# 复制开发依赖 *锁定* 文件 (包含所有 prod, dev, test 依赖)
COPY requirements/dev.txt .

# 创建虚拟环境并安装开发依赖（使用清华镜像源加速）
RUN python -m venv /venv && \
    . /venv/bin/activate && \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r dev.txt

#
# --- 4. Final (Production) Stage ---
# 最终的生产镜像，非常精简
#
FROM base AS final
# 复制已安装 *生产* 依赖的虚拟环境
COPY --from=builder-prod /venv /venv

# 复制项目源代码
# (.dockerignore 将确保 .git, .venv, requirements/dev.txt 等被排除)
COPY . .

# 设置非 root 用户
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /venv
USER appuser

# 激活 venv
ENV PATH="/venv/bin:$PATH"

# 健康检查（使用 wget 替代 curl）
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8000/health || exit 1

# 暴露端口和运行
EXPOSE 8000
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "src.main:app", "-w", "4", "-b", "0.0.0.0:8000"]

#
# --- 5. Development Stage ---
# 用于本地开发的镜像，带实时重载
#
FROM base AS development
# 复制已安装 *开发* 依赖的虚拟环境
COPY --from=builder-dev /venv /venv

# 设置非 root 用户
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /venv
USER appuser

# 激活 venv
ENV PATH="/venv/bin:$PATH"

# 暴露端口
EXPOSE 8000

# 默认命令 (带实时重载)
# 注意：代码将通过 docker-compose volume 挂载到 /app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

#
# --- 6. Test Stage ---
# 用于运行集成测试的镜像
#
FROM base AS test
# 复制已安装 *开发* 依赖的虚拟环境
COPY --from=builder-dev /venv /venv

# 复制源代码
COPY . .

# 设置非 root 用户
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /venv
USER appuser

# 激活 venv
ENV PATH="/venv/bin:$PATH"

# 默认命令 (运行我们统一的 make test.all 命令)
CMD ["make", "test.all"]