# Windows Nginx 部署说明

这套配置只针对原项目 `TalkAlways`，不包含 `csv-ai-engine`。

## 目标拓扑

- 前端静态文件：`C:/deploy/TalkAlways/client/dist`
- 后端服务：`http://127.0.0.1:3000`
- Nginx 入口：`http://8.156.95.158`
- 反向代理规则：
  - `/` -> 前端静态页面
  - `/api/` -> FastAPI 后端

## 预备条件

1. ECS 已开放入站 `80` 端口。
2. 后端服务已经能在 ECS 本机 `3000` 端口启动。
3. 已下载 Windows 版 `nginx` 并解压，例如 `C:\nginx`.

## 前端构建

在本地项目执行：

```powershell
cd client
npm install
npm run build
```

构建产物目录：

```text
client/dist
```

把整个 `dist` 上传到 ECS：

```text
C:/deploy/TalkAlways/client/dist
```

## Nginx 配置

仓库内配置文件：

```text
ops/windows-nginx/nginx.conf
```

复制到 ECS：

```text
C:/nginx/conf/nginx.conf
```

如果前端发布目录不是 `C:/deploy/TalkAlways/client/dist`，只改 `root` 这一行。

## 启动顺序

1. 启动后端

```powershell
cd C:\deploy\TalkAlways\server
python start_server.py
```

2. 启动或重载 Nginx

首次启动：

```powershell
cd C:\nginx
.\nginx.exe
```

重载配置：

```powershell
cd C:\nginx
.\nginx.exe -s reload
```

停止：

```powershell
cd C:\nginx
.\nginx.exe -s quit
```

## 验证

在 ECS 本机执行：

```powershell
Invoke-WebRequest http://127.0.0.1/api/health
Invoke-WebRequest http://127.0.0.1/
```

在浏览器访问：

```text
http://8.156.95.158
```

## 已处理的前端问题

这次已经把前端里几个生产环境硬编码的 `http://localhost:3000` 改成走相对 `/api`：

- 流式问答
- 图表 AI 流式分析
- 知识库接口
- SSE 实时回放
- Overview 页实时流

所以只要 `nginx` 代理 `/api` 到后端，前端就能直接走同域访问。
