# 🚀 CI/CD 快速参考卡

## 一键命令速查

### 🔑 首次配置（仅需一次）

```bash
# 1. 生成SSH密钥
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/ecs_key

# 2. 上传公钥到ECS
ssh-copy-id -i ~/.ssh/ecs_key.pub root@YOUR_ECS_IP

# 3. 查看私钥（复制到GitHub Secrets）
cat ~/.ssh/ecs_key
```

### 📦 触发部署

```bash
# 推送代码自动部署
git push origin main

# 或手动运行初始化脚本
bash setup-cicd.sh
```

### 🔄 回滚操作

```bash
# 一键回滚
bash rollback.sh

# 查看备份列表
ls -lt /opt/energy-system-backup/
```

### 📊 监控检查

```bash
# 快速健康检查
bash monitor.sh

# 持续监控
bash monitor.sh --continuous 60

# 查看日志
tail -f /opt/energy-system/logs/app.log
```

### 🛠️ 服务管理

```bash
# 启动/停止/重启
systemctl start energy-system
systemctl stop energy-system
systemctl restart energy-system

# 查看状态
systemctl status energy-system

# 查看实时日志
journalctl -u energy-system -f
```

---

## GitHub Secrets 配置清单

| Secret | 说明 | 获取方式 |
|--------|------|----------|
| `ECS_HOST` | ECS公网IP | 阿里云控制台 |
| `ECS_USERNAME` | SSH用户名 | 通常为 `root` |
| `ECS_SSH_KEY` | SSH私钥 | `cat ~/.ssh/ecs_key` |
| `ECS_PORT` | SSH端口 | 默认 `22` |

配置位置: GitHub → Settings → Secrets and variables → Actions

---

## 常用文件路径

```
/opt/energy-system/          # 应用目录
/opt/energy-system/server/   # 后端代码
/opt/energy-system/client-dist/ # 前端构建
/opt/energy-system/logs/     # 日志目录
/opt/energy-system-backup/   # 备份目录

/etc/systemd/system/energy-system.service  # 服务配置
```

---

## 故障排查速查

### 部署失败？
```bash
# 1. 查看GitHub Actions日志
# 访问: https://github.com/USER/REPO/actions

# 2. 查看服务器日志
journalctl -u energy-system -n 50

# 3. 回滚
bash rollback.sh
```

### 服务无法启动？
```bash
# 查看详细错误
journalctl -u energy-system -xe

# 检查端口占用
netstat -tlnp | grep 8000

# 检查依赖
cd /opt/energy-system/server
pip3 list | grep fastapi
```

### 数据库连接失败？
```bash
# 测试连接
mysql -u energy_user -p -h localhost energy_system

# 检查MySQL状态
systemctl status mysqld

# 重启MySQL
systemctl restart mysqld
```

---

## Docker 快速命令

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 重启服务
docker-compose restart app

# 停止所有服务
docker-compose down

# 重新构建
docker-compose build --no-cache
```

---

## 性能优化建议

```bash
# 1. 清理旧备份（保留最近7天）
find /opt/energy-system-backup/ -type d -mtime +7 -exec rm -rf {} \;

# 2. 清理Docker镜像
docker system prune -a

# 3. 清理日志（保留最近100MB）
find /opt/energy-system/logs/ -name "*.log" -size +100M -exec truncate -s 0 {} \;

# 4. 优化MySQL
mysqlcheck -o energy_system -u root -p
```

---

## 安全加固

```bash
# 1. 更新系统
yum update -y  # CentOS
apt-get update && apt-get upgrade -y  # Ubuntu

# 2. 配置防火墙
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload

# 3. 禁用root密码登录（仅允许密钥）
# 编辑 /etc/ssh/sshd_config
# PasswordAuthentication no

# 4. 定期轮换SSH密钥
ssh-keygen -t rsa -b 4096 -f ~/.ssh/ecs_key_new
# 替换后删除旧密钥
```

---

## 监控告警配置

### 钉钉机器人通知

```bash
# 创建钉钉群机器人，获取Webhook URL
# 添加到 GitHub Secrets: DINGTALK_WEBHOOK

# 测试通知
curl -X POST "YOUR_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{"msgtype":"text","text":{"content":"部署成功！"}}'
```

### 简单监控脚本（cron定时任务）

```bash
# 编辑crontab
crontab -e

# 每5分钟检查一次
*/5 * * * * /opt/energy-system/monitor.sh >> /var/log/monitor.log 2>&1
```

---

## 环境变量示例 (.env)

```env
# 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=energy_user
DB_PASSWORD=your_password
DB_NAME=energy_system

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# JWT
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用
APP_NAME=Energy Management System
APP_VERSION=1.0.0
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

---

## Git 工作流建议

```bash
# 开发分支
git checkout -b feature/new-feature
git commit -m "feat: add new feature"
git push origin feature/new-feature

# 合并到主分支（触发部署）
git checkout main
git merge feature/new-feature
git push origin main  # ← 自动触发部署

# 打标签（版本发布）
git tag v1.0.0
git push origin v1.0.0
```

---

## 联系与支持

- 📖 详细文档: `DEPLOYMENT_GUIDE.md`
- 🐛 问题反馈: GitHub Issues
- 💬 讨论交流: GitHub Discussions
- 📧 技术支持: your-email@example.com

---

**💡 提示**: 将此文件保存为书签，方便随时查阅！
