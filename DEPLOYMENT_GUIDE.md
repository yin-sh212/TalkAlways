# GitHub Actions 部署配置指南

本指南支持 **Linux** 和 **Windows** 两种服务器环境的自动化部署。请根据您的 ECS 操作系统选择对应的配置章节。

---

## 📋 通用 Secrets 配置

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中添加以下密钥。根据服务器类型，只需配置对应的一组连接信息。

### 1. 数据库配置（所有环境通用，可选）

| Secret 名称 | 说明 |
|------------|------|
| `DB_PASSWORD` | 数据库密码 |
| `REDIS_PASSWORD` | Redis 密码 |

---

## 🐧 方案 A: Linux ECS 部署配置

### 1. Linux 连接 Secrets

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `ECS_HOST` | ECS 服务器公网 IP | `47.xxx.xxx.xxx` |
| `ECS_USERNAME` | SSH 登录用户名 | `root` 或 `ecs-user` |
| `ECS_PORT` | SSH 端口（可选，默认22） | `22` |
| `ECS_SSH_KEY` | SSH 私钥内容 | 见下方生成方法 |

### 2. 🔑 生成 SSH 密钥对 (Linux)

#### 方法一：使用 ssh-keygen（推荐）

```bash
# 在本地生成密钥对
ssh-keygen -t rsa -b 4096 -C "github-actions@energy-system" -f ~/.ssh/ecs_deploy_key

# 将公钥上传到 ECS 服务器
ssh-copy-id -i ~/.ssh/ecs_deploy_key.pub root@YOUR_ECS_IP

# 查看私钥内容（复制到 GitHub Secrets）
cat ~/.ssh/ecs_deploy_key
```

#### 方法二：在 ECS 上生成

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

### 3. 🚀 Linux 首次部署步骤

#### 3.1 准备 ECS 服务器

```bash
# 登录 ECS
ssh root@YOUR_ECS_IP

# 安装必要软件 (CentOS/RHEL)
yum install -y python3 python3-pip git mysql-server nginx systemd

# 或使用 Ubuntu
# apt-get update && apt-get install -y python3 python3-pip git mysql-server nginx systemd

# 创建部署目录
mkdir -p /opt/energy-system
mkdir -p /opt/energy-system-backup
chmod 755 /opt/energy-system
```

#### 3.2 配置 MySQL 数据库

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

#### 3.3 配置环境变量

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

### 4. 📊 Linux 监控与维护

#### 查看服务器日志

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

#### 常见问题排查 (Linux)

*   **SSH 连接失败**:
    ```bash
    ssh -v root@YOUR_ECS_IP
    firewall-cmd --permanent --add-service=ssh && firewall-cmd --reload
    ```
*   **权限问题**:
    ```bash
    chmod +x deploy.sh rollback.sh
    chown -R root:root /opt/energy-system
    ```
*   **回滚操作**:
    ```bash
    bash /opt/energy-system/rollback.sh
    # 或指定版本
    bash /opt/energy-system/rollback.sh backup_20260406_120000
    ```

---

## 🪟 方案 B: Windows ECS 部署配置

### 1. Windows 连接 Secrets

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `ECS_HOST` | ECS 服务器公网 IP | `8.156.95.158` |
| `ECS_USERNAME` | Windows 登录用户名 | `Administrator` |
| `ECS_PASSWORD` | Windows 登录密码 | `YourStrongPassword!` |
| `ECS_PORT` | WinRM 端口（默认5986 HTTPS） | `5986` |

> **注意**: Windows 部署使用 **WinRM (Windows Remote Management)** 进行远程连接，而非 SSH。

### 2. 🔧 Windows Server 前置配置

请在 Windows ECS 服务器上以**管理员身份运行 PowerShell** 执行以下步骤：

#### Step 1: 启用 WinRM（远程管理）

```powershell
# 1. 启用 WinRM
Enable-PSRemoting -Force

# 2. 配置 WinRM 监听器（HTTPS）
winrm quickconfig -q

# 3. 允许基本身份验证（用于 GitHub Actions）
winrm set winrm/config/service/auth @{Basic="true"}
winrm set winrm/config/service @{AllowUnencrypted="false"}

# 4. 配置防火墙规则
New-NetFirewallRule -Name "WinRM_HTTPS" -DisplayName "WinRM HTTPS" -Protocol TCP -LocalPort 5986 -Action Allow -Direction Inbound

# 5. 验证 WinRM 服务
Test-WSMan -ComputerName localhost
```

#### Step 2: 安装必要软件

```powershell
# 1. 安装 Python 3.10+
# 从 https://www.python.org/downloads/ 下载并安装
# ⚠️ 务必勾选 "Add Python to PATH"

# 2. 验证 Python 安装
python --version
pip --version

# 3. 安装 Git
# 从 https://git-scm.com/download/win 下载并安装

# 4. 创建目录
New-Item -ItemType Directory -Path "D:\energy-system" -Force
New-Item -ItemType Directory -Path "D:\energy-system-backup" -Force
New-Item -ItemType Directory -Path "D:\energy-system\logs" -Force
```

#### Step 3: 安装 NSSM（用于创建 Windows 服务）

推荐使用 [NSSM](https://nssm.cc/) 将 Python 应用注册为 Windows 服务，以实现开机自启和崩溃重启。

**选项 A：使用 Chocolatey 包管理器（推荐）**
```powershell
# 安装 Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装 NSSM
choco install nssm -y
```

**选项 B：手动安装**
1. 下载 NSSM: https://nssm.cc/download
2. 解压 `nssm.exe` 到 `C:\nssm\`
3. 确保 `C:\nssm\nssm.exe` 存在并在 PATH 中，或在脚本中使用绝对路径。

#### Step 4: 配置 MySQL 数据库

```powershell
# 1. 安装 MySQL（如果未安装）
# 从 https://dev.mysql.com/downloads/installer/ 下载并安装

# 2. 启动 MySQL 服务
Start-Service MySQL80  # 服务名可能因版本而异，如 MySQL57, MySQL

# 3. 创建数据库和用户
# 打开 MySQL Command Line Client 或使用终端
mysql -u root -p
```
*(在 MySQL 提示符下执行 SQL)*
```sql
CREATE DATABASE energy_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'energy_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON energy_system.* TO 'energy_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Step 5: 配置环境变量

在 `C:\energy-system\server\.env` 创建配置文件：

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=energy_user
DB_PASSWORD=your_password
DB_NAME=energy_system

SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

APP_NAME=Energy Management System
APP_VERSION=1.0.0
DEBUG=false
"@ | Out-File -FilePath "D:\energy-system\server\.env" -Encoding UTF8
```

### 3. 🚀 Windows 首次部署步骤

完成上述前置配置并设置好 GitHub Secrets 后，推送代码即可触发自动部署：

```bash
git add .
git commit -m "feat: 添加 Windows CI/CD 配置"
git push origin main
```

GitHub Actions 将会：
1. 运行测试
2. 构建项目
3. 通过 WinRM 传输文件到 Windows ECS
4. 使用 NSSM 重启 `EnergySystem` 服务

### 4. 📊 Windows 监控与维护

#### 查看服务状态与日志

```
# 查看服务状态
Get-Service -Name EnergySystem

# 查看日志
Get-Content D:\energy-system\logs\app.log -Tail 50

# 错误日志
Get-Content D:\energy-system\logs\error.log -Tail 50

# 查看 Windows 事件日志
Get-EventLog -LogName Application -Source "EnergySystem" -Newest 20
```

#### 常见问题排查 (Windows)

*   **WinRM 连接失败**:
    ```powershell
    Get-Service WinRM
    Restart-Service WinRM
    Test-WSMan -ComputerName YOUR_ECS_IP -UseSSL
    ```
*   **防火墙阻止**:
    ```powershell
    Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*WinRM*" }
    New-NetFirewallRule -Name "WinRM_HTTPS" -DisplayName "WinRM HTTPS" -Protocol TCP -LocalPort 5986 -Action Allow
    ```
*   **服务启动失败**:
    ```powershell
    # 检查端口占用
    netstat -ano | findstr :8000
    
    # 手动测试启动
    cd C:\energy-system\server
    python start_server.py
    ```
*   **回滚操作**:
    ```powershell
    # 列出备份
    Get-ChildItem D:\energy-system-backup\ -Directory

    # 回滚到指定版本
    powershell -ExecutionPolicy Bypass -File rollback_windows.ps1 -BackupVersion "backup_20260406_120000"
    ```

---

## 🔄 手动触发部署

如果需要手动触发部署（不通过代码推送）：

1. 访问 GitHub Actions 页面
2. 选择对应的部署工作流 (Linux 或 Windows)
3. 点击 "Run workflow"
4. 选择分支并运行

---

## 🎯 最佳实践

1. **定期备份**: 
   - Linux: 设置 cron 任务定期备份数据库和代码目录。
   - Windows: 设置 Task Scheduler 定期备份。
2. **监控告警**: 配置服务健康检查和异常通知。
3. **灰度发布**: 先在测试环境验证再部署生产。
4. **版本标签**: 每次发布打 Git Tag 便于追溯。
5. **安全加固**: 
   - 定期更换 SSH 密钥或 Administrator 密码。
   - 启用防火墙，仅开放必要端口 (80, 443, 5986/22)。

---

## 📞 技术支持

如遇问题，请检查：
- GitHub Actions 日志
- **Linux**: `/var/log/messages`, `/opt/energy-system/logs/`
- **Windows**: 事件查看器 (`eventvwr.msc`), `C:\energy-system\logs\`
- 数据库错误日志
