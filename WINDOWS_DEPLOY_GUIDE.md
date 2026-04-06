# Windows ECS 自动化部署快速指南

## 🎯 概述

本指南专为 **Windows Server** 环境设计，使用 WinRM（Windows Remote Management）进行远程部署。

---

## 📋 前置要求

### 你的环境信息
- **ECS IP**: `8.156.95.158`
- **用户名**: `Administrator`
- **认证方式**: 密码登录（非 SSH 密钥）
- **WinRM 端口**: `5986` (HTTPS)

---

## 🚀 快速开始（3步完成）

### Step 1: 在 Windows ECS 上运行初始化脚本

**以管理员身份打开 PowerShell，执行：**

```powershell
# 下载并执行初始化脚本（或手动复制 setup_windows_cicd.ps1 到服务器）
# 方法1: 从 Git 仓库克隆
git clone https://github.com/YOUR_USERNAME/competitions.git
cd competitions
powershell -ExecutionPolicy Bypass -File setup_windows_cicd.ps1

# 方法2: 直接下载脚本执行
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/YOUR_USERNAME/competitions/main/setup_windows_cicd.ps1" -OutFile "setup_windows_cicd.ps1"
powershell -ExecutionPolicy Bypass -File setup_windows_cicd.ps1
```

该脚本会自动：
- ✅ 启用 WinRM 远程管理
- ✅ 配置防火墙规则
- ✅ 创建目录结构（`D:\energy-system` 和 `D:\energy-system-backup`）
- ✅ 检查 Python、Git 等依赖
- ✅ 生成 GitHub Secrets 配置信息

### Step 2: 配置 GitHub Secrets

访问: `https://github.com/YOUR_USERNAME/competitions/settings/secrets/actions`

添加以下 4 个 Secrets：

| Secret 名称 | 值 | 说明 |
|------------|-----|------|
| `ECS_HOST` | `8.156.95.158` | 你的 ECS 公网 IP |
| `ECS_USERNAME` | `Administrator` | Windows 用户名 |
| `ECS_PASSWORD` | `2026TtTt@xxx` | Windows 登录密码 |
| `ECS_PORT` | `5986` | WinRM HTTPS 端口 |

### Step 3: 推送代码触发自动部署

```bash
git add .
git commit -m "feat: 添加 Windows CI/CD 配置"
git push origin main
```

**完成！** GitHub Actions 会自动部署到你的 Windows ECS。

访问: `http://8.156.95.158:8000` 查看应用

---

## 🔧 手动部署（备选方案）

如果自动部署失败，可以手动部署：

### 1. 克隆代码到 Windows ECS

``powershell
# 在 Windows ECS 上执行
cd C:\
git clone https://github.com/YOUR_USERNAME/competitions.git
cd competitions
```

### 2. 安装依赖

```powershell
# 后端依赖
cd D:\competitions\server
pip install -r requirements.txt

# 前端依赖
cd ..\client
npm install
npm run build
```

### 3. 运行部署脚本

``powershell
cd D:\competitions
powershell -ExecutionPolicy Bypass -File deploy_windows.ps1
```

---

## 📊 日常运维命令

### 查看服务状态

```powershell
# 查看服务状态
Get-Service -Name EnergySystem

# 启动/停止/重启
Start-Service EnergySystem
Stop-Service EnergySystem
Restart-Service EnergySystem
```

### 查看日志

```powershell
# 应用日志
Get-Content D:\energy-system\logs\app.log -Tail 50

# 错误日志
Get-Content D:\energy-system\logs\error.log -Tail 50

# 实时跟踪日志
Get-Content D:\energy-system\logs\app.log -Wait -Tail 10
```

### 回滚操作

``powershell
# 列出可用备份
Get-ChildItem D:\energy-system-backup\ -Directory

# 一键回滚到最新版本
powershell -ExecutionPolicy Bypass -File rollback_windows.ps1

# 回滚到指定版本
powershell -ExecutionPolicy Bypass -File rollback_windows.ps1 -BackupVersion "backup_20260406_120000"
```

### 监控服务

```powershell
# 一次性检查
powershell -ExecutionPolicy Bypass -File monitor_windows.ps1

# 持续监控（每60秒）
powershell -ExecutionPolicy Bypass -File monitor_windows.ps1 -Continuous -Interval 60
```

---

## ⚙️ 配置说明

### Windows 服务 vs 任务计划程序

部署脚本会优先尝试创建 **Windows 服务**（需要 NSSM），如果 NSSM 未安装则使用 **任务计划程序** 作为备选方案。

**推荐安装 NSSM：**
```powershell
# 使用 Chocolatey 安装
choco install nssm -y

# 或手动下载安装
# 1. 下载: https://nssm.cc/download
# 2. 解压到 C:\nssm\
# 3. 确保 C:\nssm\nssm.exe 存在
```

### 目录结构

```
D:\energy-system\
├── server\              # 后端代码
│   ├── app\
│   ├── requirements.txt
│   ├── start_server.py
│   └── .env            # 环境变量
├── client-dist\         # 前端构建产物
└── logs\               # 日志目录
    ├── app.log
    └── error.log

D:\energy-system-backup\
├── backup_20260406_120000\
├── backup_20260406_130000\
└── pre_rollback_20260406_140000\
```

### 环境变量配置

在 `D:\energy-system\server\.env` 文件中配置：

``env
DB_HOST=localhost
DB_PORT=3306
DB_USER=energy_user
DB_PASSWORD=your_password
DB_NAME=energy_system

SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

DEBUG=false
HOST=0.0.0.0
PORT=8000
```

---

## ❓ 常见问题

### Q1: WinRM 连接失败？

```powershell
# 检查 WinRM 服务
Get-Service WinRM

# 重启 WinRM
Restart-Service WinRM

# 测试本地连接
Test-WSMan -ComputerName localhost

# 检查防火墙
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*WinRM*" }
```

### Q2: 部署时提示权限不足？

确保：
1. 以**管理员身份**运行 PowerShell
2. 执行策略允许脚本运行：
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
   ```

### Q3: 服务启动后立即停止？

``powershell
# 查看详细错误
Get-EventLog -LogName Application -Newest 20 | Where-Object { $_.Source -like "*Energy*" }

# 检查端口占用
netstat -ano | findstr :8000

# 手动测试启动
cd D:\energy-system\server
python start_server.py
```

### Q4: Python 找不到模块？

``powershell
# 检查 Python 路径
where python

# 重新安装依赖
cd D:\energy-system\server
pip install -r requirements.txt

# 验证安装
pip list | findstr fastapi
```

### Q5: 如何更改部署目录？

修改 `.github/workflows/deploy.yml`：

```
env:
  SERVER_DIR: D:\your-custom-path
  BACKUP_DIR: D:\your-backup-path
```

同时修改 `deploy_windows.ps1` 和 `rollback_windows.ps1` 中的默认路径。

---

## 🔒 安全建议

1. **定期更改密码**: 至少每 90 天更改一次 Administrator 密码
2. **更新 GitHub Secrets**: 密码更改后同步更新 GitHub Secrets
3. **启用 Windows 防火墙**: 仅开放必要端口（8000, 5986）
4. **安装防病毒软件**: Windows Defender 或第三方杀毒软件
5. **定期更新系统**: Windows Update
6. **限制远程访问**: 仅在需要时启用 WinRM

---

## 📞 获取帮助

- 📖 详细文档: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- 🐛 问题反馈: GitHub Issues
- 💬 讨论交流: GitHub Discussions

---

## 🎉 总结

你现在拥有：
- ✅ 基于 WinRM 的 Windows 自动化部署
- ✅ 密码认证（无需 SSH 密钥）
- ✅ 一键回滚机制
- ✅ 实时监控工具
- ✅ 完整的文档支持

**从此告别手动 RDP 登录服务器部署的烦恼！** 🚀
