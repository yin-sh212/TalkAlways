# 多阶段构建 Dockerfile
FROM python:3.10-slim as backend-builder

WORKDIR /app/server

# 安装依赖
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY server/ .

# 前端构建阶段
FROM node:16-alpine as frontend-builder

WORKDIR /app/client

COPY client/package*.json ./
RUN npm ci

COPY client/ .
RUN npm run build

# 最终镜像
FROM python:3.10-slim

LABEL maintainer="energy-system-team"
LABEL description="Energy Management System"

WORKDIR /opt/energy-system

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从builder阶段复制文件
COPY --from=backend-builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin
COPY --from=backend-builder /app/server /opt/energy-system/server
COPY --from=frontend-builder /app/client/dist /opt/energy-system/client-dist

# 创建工作目录
RUN mkdir -p /opt/energy-system/logs

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
WORKDIR /opt/energy-system/server
CMD ["python", "start_server.py"]
