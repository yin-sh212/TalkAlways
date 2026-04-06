# 能源管理系统 - CI/CD 自动化部署

## 🚀 快速开始

### 方式一：GitHub Actions（推荐）

#### 1. 配置 GitHub Secrets

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中添加：

```
ECS_HOST=你的ECS公网IP
ECS_USERNAME=root
ECS_SSH_KEY=-----BEGIN RSA PRIVATE KEY-----...
ECS_PORT=22
```

#### 2. 推送代码触发自动部署

```bash
git add .
git commit -m "feat: update feature"
git push origin main
```

GitHub Actions 会自动：
- ✅ 运行所有测试
- ✅ 构建前端和后端
- ✅ 上传到 ECS 服务器
- ✅ 停止旧服务并启动新服务
- ✅ 健康检查验证

#### 3. 查看部署状态

访问: `https://github.com/YOUR_USERNAME/competitions/actions`

---

### 方式二：手动部署

```bash
# 1. 克隆代码到 ECS
ssh root@YOUR_ECS_IP
cd /opt
git clone https://github.com/YOUR_USERNAME/competitions.git

# 2. 运行部署脚本
cd competitions
chmod +x deploy.sh
bash deploy.sh

# 3. 验证部署
curl http://localhost:8000/api/health
```

---

### 方式三：Docker 部署

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f app
```

---

## 🔄 回滚操作

### 一键回滚到上一版本

```bash
bash rollback.sh
```

### 回滚到指定版本

```bash
# 查看可用备份
ls -lt /opt/energy-system-backup/

# 回滚到指定版本
bash rollback.sh backup_20260406_120000
```

---

## 📊 监控与运维

### 健康检查

```bash
# 快速检查
bash monitor.sh

# 持续监控（每60秒检查一次）
bash monitor.sh --continuous 60
```

### 查看日志

```bash
# 应用日志
tail -f /opt/energy-system/logs/app.log

# 错误日志
tail -f /opt/energy-system/logs/error.log

# 系统服务日志
journalctl -u energy-system -f
```

### 服务管理

```bash
# 启动服务
systemctl start energy-system

# 停止服务
systemctl stop energy-system

# 重启服务
systemctl restart energy-system

# 查看状态
systemctl status energy-system
```

---

## 🛠️ 环境初始化

首次使用 CI/CD，运行初始化脚本：

```bash
chmod +x setup-cicd.sh
bash setup-cicd.sh
```

该脚本会：
1. ✅ 检查必要工具（Git, Python, Node.js）
2. ✅ 生成 SSH 密钥对
3. ✅ 指导配置 GitHub Secrets
4. ✅ 触发首次部署

---

## 📋 部署流程说明

```mermaid
graph LR
    A[代码提交] --> B[GitHub Actions]
    B --> C[运行测试]
    C --> D{测试通过?}
    D -->|是| E[构建应用]
    D -->|否| F[通知失败]
    E --> G[上传到ECS]
    G --> H[停止旧服务]
    H --> I[启动新服务]
    I --> J[健康检查]
    J --> K{检查通过?}
    K -->|是| L[部署成功]
    K -->|否| M[自动回滚]
    L --> N[发送通知]
    M --> N
```

---

## 🔧 配置文件说明

| 文件 | 说明 |
|------|------|
| `.github/workflows/deploy.yml` | GitHub Actions 工作流配置 |
| `.flow.yml` | 阿里云云效 Flow 配置 |
| `deploy.sh` | 自动化部署脚本 |
| `rollback.sh` | 一键回滚脚本 |
| `monitor.sh` | 健康监控脚本 |
| `setup-cicd.sh` | CI/CD 环境初始化 |
| `Dockerfile` | Docker 镜像构建 |
| `docker-compose.yml` | Docker Compose 配置 |
| `DEPLOYMENT_GUIDE.md` | 详细部署文档 |

---

## ⚙️ 自定义配置

### 修改部署目录

编辑 `.github/workflows/deploy.yml`:

```yaml
env:
  SERVER_DIR: /your/custom/path
  BACKUP_DIR: /your/backup/path
```

### 添加钉钉通知

在 GitHub Secrets 中添加 `DINGTALK_WEBHOOK`，然后在 `.flow.yml` 中配置通知。

### 自定义健康检查

编辑 `deploy.sh` 中的健康检查逻辑：

```bash
curl -f http://localhost:8000/api/health || exit 1
```

---

## ❓ 常见问题

### Q: 部署失败怎么办？

A: 
1. 查看 GitHub Actions 日志
2. 检查服务器日志: `journalctl -u energy-system -n 50`
3. 使用 `rollback.sh` 回滚到上一版本

### Q: 如何跳过测试直接部署？

A: 在 commit message 中添加 `[skip ci]` 或手动触发 workflow。

### Q: 支持多环境部署吗？

A: 可以创建多个 workflow 文件，如 `deploy-staging.yml` 和 `deploy-prod.yml`。

### Q: 如何限制部署权限？

A: 在 GitHub Settings 中配置 Environment Protection Rules。

---

## 📞 技术支持

- 📖 详细文档: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- 🐛 问题反馈: GitHub Issues
- 💬 讨论交流: GitHub Discussions

---

## 🎯 最佳实践

1. **分支策略**: main/master 分支自动部署生产环境
2. **测试先行**: 确保所有测试通过才允许合并
3. **灰度发布**: 先在测试环境验证再部署生产
4. **定期备份**: 设置定时任务备份数据库
5. **监控告警**: 配置服务异常自动通知
6. **文档同步**: 每次变更更新相关文档
