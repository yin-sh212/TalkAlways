# Windows Nginx 部署说明

## 目标

将 TalkAlways 前端静态资源交给 Windows Nginx 托管，同时把后端 API 和 MCP 请求反向代理到本机 `3000` 端口。

这套部署方案尽量不改前端功能，只做两类最小变更：

- 把前端里写死的 `http://localhost:3000` 改成同域相对地址
- 由 Nginx 统一代理 `/api` 和 `/mcp`

## 目录建议

建议服务器目录结构：

```text
C:\deploy\TalkAlways\
  client\
    dist\
  server\

C:\nginx\
  conf\
    nginx.conf
```

## 一、准备代码

在服务器上拉取目标分支代码：

```powershell
git fetch origin
git checkout <部署分支名>
git pull
```

## 二、直接使用脚本

### 1. 启动后端

如果服务器上有固定 Python 路径，直接传进去。  
不上传任何 CA 证书文件时，后端会自动回退到 `certifi` 的系统 CA 包连接 TiDB Cloud。

```powershell
cd C:\deploy\TalkAlways\ops\windows-nginx
.\start-backend.ps1 -RepoRoot C:\deploy\TalkAlways -PythonExe E:\Miniconda3\envs\chang\python.exe
```

### 2. 生成并安装 Nginx 配置

```powershell
cd C:\deploy\TalkAlways\ops\windows-nginx
.\deploy.ps1 -RepoRoot C:\deploy\TalkAlways -NginxRoot C:\nginx -InstallFrontendDeps -StartNginxIfStopped
```

### 3. 停止后端

```powershell
cd C:\deploy\TalkAlways\ops\windows-nginx
.\stop-backend.ps1 -RepoRoot C:\deploy\TalkAlways
```

## 三、手工步骤

如果不想直接用脚本，也可以按下面的手工方式执行。

## 四、构建前端

```powershell
cd C:\deploy\TalkAlways\client
npm install
npm run build
```

构建完成后确认目录存在：

```text
C:\deploy\TalkAlways\client\dist
```

## 五、启动后端

如果你们后端依赖 `conda` 环境，例如 `chang`：

```powershell
conda activate chang
cd C:\deploy\TalkAlways\server
pip install -r requirements.txt
python start_server.py
```

默认后端监听：

```text
http://127.0.0.1:3000
```

补充说明：

- `server/.env` 中如果配置了 `SSL_CA=./certs/ca-cert.pem` 但服务器上没有这个文件，当前代码会自动回退到 `certifi` 的 CA 包
- 因此这次部署不需要额外上传 CA 证书

## 六、配置 Nginx

把仓库中的配置文件复制到 Nginx：

```powershell
copy C:\deploy\TalkAlways\ops\windows-nginx\nginx.conf C:\nginx\conf\nginx.conf
```

如果你的部署目录不是 `C:/deploy/TalkAlways/client/dist`，先修改 `nginx.conf` 里的 `root`。

## 七、启动 Nginx

```powershell
cd C:\nginx
.\nginx.exe -t
.\nginx.exe
```

修改配置后重载：

```powershell
.\nginx.exe -s reload
```

停止：

```powershell
.\nginx.exe -s stop
```

## 八、Nginx 路由说明

当前配置的路由职责如下：

- `/`
  - 托管 Vue 前端静态页面
- `/api/`
  - 反向代理到 `http://127.0.0.1:3000`
- `/mcp/`
  - 反向代理到 `http://127.0.0.1:3000`
- `/docs`
  - 反向代理到后端 FastAPI 文档
- `/openapi.json`
  - 反向代理到后端 OpenAPI

## 九、为什么这样配

### 1. `try_files $uri $uri/ /index.html`

前端使用 Vue Router `createWebHistory()`。如果没有这条规则，用户直接刷新：

- `/Overview`
- `/analysis`
- `/alarm`
- `/building-map`

会被 Nginx 当成真实文件路径，直接返回 `404`。

### 2. `/api/` 单独反代

前端大部分接口都已经走 `/api`，Nginx 反代后浏览器始终访问当前域名，不需要额外处理跨域。

### 3. `/mcp/` 单独反代

后端 MCP 接口不是 `/api/...`，而是 `/mcp/...`，如果不单独代理，这部分功能会失效。

### 4. `proxy_buffering off`

项目里有 SSE 和流式响应：

- 实时回放流
- 图表 AI 流式分析

不开这一组配置，Nginx 会缓存响应，前端表现会像“卡住不出结果”。

## 十、部署后验证清单

至少验证以下功能：

1. 登录页能打开
2. `http://<服务器IP>/Overview` 正常
3. 直接刷新 `/analysis` 不 `404`
4. 总览页实时流正常
5. 图表 AI 分析流正常
6. `/building-map` 正常
7. `/mcp/...` 功能正常
8. `/docs` 能打开后端文档

## 十一、脚本参数说明

### `deploy.ps1`

| 参数 | 说明 |
|---|---|
| `-RepoRoot` | 代码仓库根目录 |
| `-NginxRoot` | Nginx 安装目录 |
| `-BackendHost` | 反代后端主机，默认 `127.0.0.1` |
| `-BackendPort` | 反代后端端口，默认 `3000` |
| `-InstallFrontendDeps` | 执行 `npm install` |
| `-SkipFrontendBuild` | 跳过前端构建 |
| `-SkipNginxControl` | 只生成配置，不执行 `nginx -t/reload` |
| `-StartNginxIfStopped` | 如果 Nginx 没启动则直接启动 |

### `start-backend.ps1`

| 参数 | 说明 |
|---|---|
| `-RepoRoot` | 代码仓库根目录 |
| `-PythonExe` | Python 可执行文件路径 |
| `-BindHost` | 后端监听地址，默认 `0.0.0.0` |
| `-Port` | 后端监听端口，默认 `3000` |
| `-StartupTimeoutSec` | 启动等待秒数 |

### `stop-backend.ps1`

| 参数 | 说明 |
|---|---|
| `-RepoRoot` | 代码仓库根目录 |
| `-Port` | 停止指定监听端口的后端进程，默认 `3000` |

## 十二、当前这次最小改动

为了兼容 Nginx 同域部署，这次只修了这些前端文件里的硬编码后端地址：

- `client/src/api/chart-analysis.ts`
- `client/src/views/Overview.vue`
- `client/src/components/overview/RealtimeMonitor.vue`

没有改页面逻辑、组件交互和业务接口结构。
