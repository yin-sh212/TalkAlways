# GitHub Actions 部署配置指南

## 📋 需要配置的 Secrets

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中添加以下密钥：

### 1. ECS 服务器连接信息

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `ECS_HOST` | ECS 服务器公网 IP | `47.xxx.xxx.xxx` |
| `ECS_USERNAME` | SSH 登录用户名 | `root` 或 `ecs-user` |
| `ECS_PORT` | SSH 端口（可选，默认22） | `22` |
| `ECS_SSH_KEY` | SSH 私钥内容 | 见下方生成方法 |

### 2. 数据库配置（可选）

| Secret 名称 | 说明 |
|------------|------|
| `DB_PASSWORD` | 数据库密码 |
| `REDIS_PASSWORD` | Redis 密码 |

---

## 🔑 生成 SSH 密钥对

### 方法一：使用 ssh-keygen（推荐）

```bash
# 在本地生成密钥对
ssh-keygen -t rsa -b 4096 -C "github-actions@energy-system" -f ~/.ssh/ecs_deploy_key

# 将公钥上传到 ECS 服务器
ssh-copy-id -i ~/.ssh/ecs_deploy_key.pub root@YOUR_ECS_IP

# 查看私钥内容（复制到 GitHub Secrets）
cat ~/.ssh/ecs_deploy_key
```

### 方法二：在 ECS 上生成

```bash
# 登录 ECS 服务器
ssh root@YOUR_ECS_IP

# 生成密钥对
ssh-keygen -t rsa -b 4096 -f /root/.ssh/github_actions_key

# 将公钥添加到 authorized_keys
cat /root/.ssh/github_actions_key.pub >> /root/.ssh/authorized_keys

# 查看私钥
cat /root/.ssh/github_actions_key
```

然后将私钥内容复制到 GitHub Secret `ECS_SSH_KEY`。

---

## 🚀 首次部署步骤

### 1. 准备 ECS 服务器

```bash
# 登录 ECS
ssh root@YOUR_ECS_IP

# 安装必要软件
yum install -y python3 python3-pip git mysql-server nginx systemd

# 或使用 Ubuntu
apt-get update && apt-get install -y python3 python3-pip git mysql-server nginx systemd

# 创建部署目录
mkdir -p /opt/energy-system
mkdir -p /opt/energy-system-backup
chmod 755 /opt/energy-system
```

### 2. 配置 MySQL 数据库

```bash
# 启动 MySQL
systemctl start mysqld
systemctl enable mysqld

# 创建数据库和用户
mysql -u root -p <<EOF
CREATE DATABASE energy_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'energy_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON energy_system.* TO 'energy_user'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### 3. 配置环境变量

在 ECS 服务器上创建 `.env` 文件：

```bash
cat > /opt/energy-system/server/.env <<EOF
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=energy_user
DB_PASSWORD=your_password
DB_NAME=energy_system

# JWT 配置
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用配置
APP_NAME=Energy Management System
APP_VERSION=1.0.0
DEBUG=false
EOF
```

### 4. 触发首次部署

推送代码到 main/master 分支：

```bash
git add .
git commit -m "Initial commit with CI/CD configuration"
git push origin main
```

GitHub Actions 会自动触发部署流程！

---

## 📊 监控部署状态

### 查看 GitHub Actions 日志

访问: `https://github.com/YOUR_USERNAME/competitions/actions`

### 查看服务器日志

```bash
# 应用日志
tail -f /opt/energy-system/logs/app.log

# 错误日志
tail -f /opt/energy-system/logs/error.log

# 系统服务状态
systemctl status energy-system

# 实时日志
journalctl -u energy-system -f
```

---

## 🔄 手动触发部署

如果需要手动触发部署（不通过代码推送）：

1. 访问 GitHub Actions 页面
2. 选择 "Deploy to Alibaba Cloud ECS" 工作流
3. 点击 "Run workflow"
4. 选择分支并运行

---

## ⚠️ 常见问题

### 1. SSH 连接失败

```bash
# 检查 SSH 配置
ssh -v root@YOUR_ECS_IP

# 确保防火墙允许 SSH
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload
```

### 2. 权限问题

```bash
# 确保部署脚本有执行权限
chmod +x deploy.sh rollback.sh

# 检查目录权限
chown -R root:root /opt/energy-system
chmod -R 755 /opt/energy-system
```

### 3. 服务启动失败

```bash
# 查看详细错误
journalctl -u energy-system -n 100 --no-pager

# 检查端口占用
netstat -tlnp | grep 8000

# 检查 Python 依赖
cd /opt/energy-system/server
pip3 list
```

### 4. 回滚操作

```bash
# 自动回滚到最新版本
bash /opt/energy-system/rollback.sh

# 回滚到指定版本
bash /opt/energy-system/rollback.sh backup_20260406_120000
```

---

## 🎯 最佳实践

1. **定期备份**: 设置 cron 任务定期备份数据库
2. **监控告警**: 配置服务健康检查和告警
3. **灰度发布**: 先在测试环境验证再部署生产
4. **版本标签**: 每次发布打 Git Tag 便于追溯
5. **文档更新**: 保持部署文档与实际配置同步

---

## 📞 技术支持

如遇问题，请检查：
- GitHub Actions 日志
- 服务器系统日志 (`/var/log/messages`)
- 应用日志 (`/opt/energy-system/logs/`)
- MySQL 错误日志
