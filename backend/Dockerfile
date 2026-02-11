# AutoGeo Backend Dockerfile
# 多阶段构建，最终镜像只包含运行时依赖
FROM python:3.12-slim AS builder

# 设置构建参数
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.3.0

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv - 更快的 Python 包管理器
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# 设置工作目录
WORKDIR /build

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到临时目录
RUN uv pip install --system -r requirements.txt --target /tmp/python

# =============================================
# 最终阶段 - 只包含运行时
# =============================================
FROM python:3.12-slim

# 设置标签
LABEL maintainer="AutoGeo Team" \
      org.opencontainers.image.title="AutoGeo Backend" \
      org.opencontainers.image.description="FastAPI backend for AutoGeo platform" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/Architecture-Matrix/auto_geo"

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app:${PATH}" \
    PYTHONPATH="/app"

# 创建非 root 用户
RUN useradd -m -u 1000 autogeo && \
    mkdir -p /app/data /app/logs /app/.cache && \
    chown -R autogeo:autogeo /app

# 从构建阶段复制 Python 依赖
COPY --from=builder /tmp/python /usr/local

# 复制应用代码
WORKDIR /app
COPY --chown=autogeo:autogeo . .

# 切换到非 root 用户
USER autogeo

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 暴露端口
EXPOSE 8001

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
