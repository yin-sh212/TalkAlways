# CI/CD 自动化部署配置完成清单

## ✅ 已创建的文件

### 1. GitHub Actions 配置
- `.github/workflows/deploy.yml` - 完整的CI/CD工作流
  - 自动运行测试
  - 构建前后端
  - 部署到ECS
  - 健康检查验证

### 2. 阿里云云效 Flow 配置
- `.flow.yml` - 云效流水线配置
  - 四阶段部署流程
  - 钉钉通知集成
  - 支持回滚

### 3. 部署脚本
- `deploy.sh` - 自动化部署脚本
  - 备份旧版本
  - 停止服务
  - 部署新代码
  - 安装依赖
  - 启动服务
  - 验证部署

- `rollback.sh` - 一键回滚脚本
  - 列出可用备份
  - 恢复指定版本
  - 自动重启服务

### 4. 监控脚本
- `monitor.sh` - 系统健康监控
  - HTTP服务检查
  - 系统资源监控
  - 数据库连接验证
  - 日志查看

### 5. Docker 配置
- `Dockerfile` - 多阶段构建镜像
- `docker-compose.yml` - 完整容器编排
  - MySQL数据库
  - Redis缓存
  - 应用服务
  - Nginx反向代理

### 6. 文档
- `DEPLOYMENT_GUIDE.md` - 详细部署指南
- `README_CI_CD.md` - CI/CD使用说明
- `setup-cicd.sh` - 环境初始化脚本

---

## 🚀 使用步骤

### 方案一：GitHub Actions（推荐）

#### Step 1: 准备ECS服务器

```bash
# SSH登录ECS
ssh root@YOUR_ECS_IP

# 安装必要软件
yum install -y python3 python3-pip git mysql-server nginx systemd

# 创建目录
mkdir -p /opt/energy-system
mkdir -p /opt/energy-system-backup
```

#### Step 2: 配置MySQL

```bash
systemctl start mysqld
mysql -u root -p <<EOF
CREATE DATABASE energy_system CHARACTER SET utf8mb4;
CREATE USER 'energy_user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL ON energy_system.* TO 'energy_user'@'localhost';
FLUSH PRIVILEGES;
EOF
```

#### Step 3: 生成SSH密钥

```bash
# 在本地执行
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/ecs_key

# 上传公钥到ECS
ssh-copy-id -i ~/.ssh/ecs_key.pub root@YOUR_ECS_IP

# 查看私钥（复制到GitHub Secrets）
cat ~/.ssh/ecs_key
```

#### Step 4: 配置GitHub Secrets

访问: `https://github.com/YOUR_USERNAME/competitions/settings/secrets/actions`

添加以下Secrets:
- `ECS_HOST`: ECS公网IP
- `ECS_USERNAME`: root
- `ECS_SSH_KEY`: 私钥内容
- `ECS_PORT`: 22 (可选)

#### Step 5: 推送代码触发部署

```bash
git add .
git commit -m "feat: 添加CI/CD配置"
git push origin main
```

#### Step 6: 查看部署进度

访问: `https://github.com/YOUR_USERNAME/competitions/actions`

---

### 方案二：手动部署

```bash
# 1. 克隆代码
ssh root@YOUR_ECS_IP
cd /opt
git clone https://github.com/YOUR_USERNAME/competitions.git
cd competitions

# 2. 运行部署
chmod +x deploy.sh
bash deploy.sh

# 3. 验证
curl http://localhost:8000/api/health
```

---

### 方案三：Docker部署

```bash
# 1. 克隆代码
git clone https://github.com/YOUR_USERNAME/competitions.git
cd competitions

# 2. 配置环境变量
cp .env.example server/.env
# 编辑 .env 文件配置数据库密码等

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f app
```

---

## 🔄 日常操作

### 触发新部署

```bash
# 方式1: 推送代码
git push origin main

# 方式2: 手动触发
# 访问 GitHub Actions → Deploy to Alibaba Cloud ECS → Run workflow
```

### 回滚操作

```bash
# 自动回滚到最新版本
bash rollback.sh

# 回滚到指定版本
bash rollback.sh backup_20260406_120000
```

### 监控服务

```bash
# 一次性检查
bash monitor.sh

# 持续监控
bash monitor.sh --continuous 60
```

### 查看日志

```bash
# 应用日志
tail -f /opt/energy-system/logs/app.log

# 系统日志
journalctl -u energy-system -f
```

---

## 📊 部署流程图

```
代码提交 (push to main)
    ↓
GitHub Actions 触发
    ↓
┌─────────────┐
│  运行测试    │ ← 如果失败，终止流程
└─────────────┘
    ↓ 通过
┌─────────────┐
│  构建应用    │ ← 前端+后端打包
└─────────────┘
    ↓
┌─────────────┐
│  上传到ECS   │ ← SCP传输
└─────────────┘
    ↓
┌─────────────┐
│  备份旧版本  │ ← 自动备份
└─────────────┘
    ↓
┌─────────────┐
│  停止旧服务  │ ← systemctl stop
└─────────────┘
    ↓
┌─────────────┐
│  部署新代码  │ ← 解压并替换
└─────────────┘
    ↓
┌─────────────┐
│  安装依赖    │ ← pip install
└─────────────┘
    ↓
┌─────────────┐
│  启动新服务  │ ← systemctl start
└─────────────┘
    ↓
┌─────────────┐
│  健康检查    │ ← curl /api/health
└─────────────┘
    ↓ 通过
✅ 部署成功！
    ↓
发送通知 (钉钉/邮件)
```

---

## ⚙️ 自定义配置

### 修改部署路径

编辑 `.github/workflows/deploy.yml`:

```yaml
env:
  SERVER_DIR: /your/custom/path
  BACKUP_DIR: /your/backup/path
```

### 添加更多通知渠道

在 `.flow.yml` 中配置:

```yaml
notifications:
  success:
    - type: dingtalk
      webhook: ${{ secrets.DINGTALK_WEBHOOK }}
    - type: email
      recipients: team@example.com
```

### 配置多环境部署

创建不同分支的部署策略:

```yaml
on:
  push:
    branches:
      - main      # 生产环境
      - staging   # 测试环境
      - develop   # 开发环境
```

---

## 🔒 安全建议

1. **使用SSH密钥而非密码**: 更安全且支持自动化
2. **限制Secrets权限**: 仅授予必要的仓库权限
3. **定期轮换密钥**: 每3-6个月更新一次SSH密钥
4. **启用双因素认证**: GitHub账户开启2FA
5. **审计日志**: 定期检查GitHub Actions运行记录

---

## 📞 故障排查

### 问题1: SSH连接失败

```bash
# 测试SSH连接
ssh -v root@YOUR_ECS_IP

# 检查防火墙
firewall-cmd --list-all

# 确保SSH服务运行
systemctl status sshd
```

### 问题2: 部署脚本报错

```bash
# 查看详细错误
bash -x deploy.sh

# 检查权限
ls -la deploy.sh
chmod +x deploy.sh
```

### 问题3: 服务启动失败

```bash
# 查看系统日志
journalctl -u energy-system -n 100

# 检查端口占用
netstat -tlnp | grep 8000

# 检查Python环境
python3 --version
pip3 list
```

### 问题4: 数据库连接失败

```bash
# 测试数据库连接
mysql -u energy_user -p -h localhost energy_system

# 检查MySQL状态
systemctl status mysqld

# 查看MySQL日志
tail -f /var/log/mysqld.log
```

---

## 🎯 下一步优化建议

1. **灰度发布**: 先部署到部分实例，验证后再全量
2. **蓝绿部署**: 同时运行两个版本，快速切换
3. **自动扩容**: 根据负载自动增加ECS实例
4. **CDN加速**: 静态资源使用阿里云CDN
5. **负载均衡**: 使用SLB分发流量
6. **容器化**: 迁移到阿里云ACK/Kubernetes
7. **Serverless**: 考虑使用函数计算FC

---

## 📚 相关文档

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - 详细部署指南
- [README_CI_CD.md](README_CI_CD.md) - CI/CD使用说明
- [GitHub Actions文档](https://docs.github.com/en/actions)
- [阿里云云效文档](https://help.aliyun.com/product/153005.html)

---

**🎉 恭喜！CI/CD 自动化部署配置已完成！**

现在每次推送代码到 main 分支，都会自动部署到生产环境，无需手动操作服务器！
