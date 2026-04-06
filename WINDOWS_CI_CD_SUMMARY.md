# Windows ECS CI/CD 配置完成总结

## ✅ 已完成配置

### 📦 创建的文件清单

#### 1. GitHub Actions 工作流（已更新为 Windows 支持）
- ✅ `.github/workflows/deploy.yml` - 使用 WinRM + 密码认证
  - 自动测试 → 构建 → 部署到 Windows ECS
  - 通过 `appleboy/winrm-action` 执行远程命令
  - 支持 HTTPS (端口 5986)

#### 2. Windows PowerShell 部署脚本
- ✅ `deploy_windows.ps1` - Windows 自动化部署
  - 备份旧版本
  - 停止服务
  - 部署新代码
  - 安装 Python 依赖
  - 配置 Windows 服务（NSSM）或任务计划程序
  - 启动并验证

- ✅ `rollback_windows.ps1` - Windows 一键回滚
  - 列出所有备份
  - 恢复到指定版本
  - 自动重启服务

#### 3. Windows 监控脚本
- ✅ `monitor_windows.ps1` - 实时监控
  - HTTP 健康检查
  - CPU/内存/磁盘监控
  - 服务状态检查
  - 数据库连接验证
  - 日志查看

#### 4. 初始化脚本
- ✅ `setup_windows_cicd.ps1` - Windows 服务器初始化
  - 启用 WinRM
  - 配置防火墙
  - 创建目录结构
  - 检查依赖
  - 生成 Secrets 配置信息

#### 5. 完整文档
- ✅ `WINDOWS_DEPLOY_GUIDE.md` - Windows 专用快速指南
- ✅ `DEPLOYMENT_GUIDE.md` - 已更新支持 Windows
- ✅ `QUICK_REFERENCE.md` - 快速参考卡片

---

## 🎯 你的环境配置

| 项目 | 值 |
|------|-----|
| **ECS IP** | `8.156.95.158` |
| **操作系统** | Windows Server |
| **用户名** | `Administrator` |
| **认证方式** | 密码登录 |
| **WinRM 端口** | `5986` (HTTPS) |
| **部署目录** | `D:\energy-system` |
| **备份目录** | `D:\energy-system-backup` |

---

## 🚀 立即开始（3步完成）

### Step 1: 在 Windows ECS 上运行初始化

**以管理员身份打开 PowerShell，执行：**

``powershell
# 方法1: 从 Git 克隆后执行
git clone https://github.com/YOUR_USERNAME/competitions.git
cd competitions
powershell -ExecutionPolicy Bypass -File setup_windows_cicd.ps1

# 方法2: 直接下载脚本
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/YOUR_USERNAME/competitions/main/setup_windows_cicd.ps1" -OutFile "setup.ps1"
powershell -ExecutionPolicy Bypass -File setup.ps1
```

该脚本会自动完成所有前置配置！

### Step 2: 配置 GitHub Secrets

访问: `https://github.com/YOUR_USERNAME/competitions/settings/secrets/actions`

添加以下 4 个 Secrets：

```
Name: ECS_HOST
Value: 8.156.95.158

---

Name: ECS_USERNAME
Value: Administrator

---

Name: ECS_PASSWORD
Value: 2026TtTt@xxx  （替换为你的实际密码）

---

Name: ECS_PORT
Value: 5986
```

### Step 3: 推送代码触发部署

```bash
git add .
git commit -m "feat: 添加 Windows CI/CD 配置"
git push origin main
```

**完成！** 等待 2-3 分钟，访问 `http://8.156.95.158:8000` 查看应用。

---

## 📊 部署流程说明

```
你推送代码 (git push)
    ↓
GitHub Actions 触发
    ↓
┌──────────────────┐
│  运行 57 个测试   │ ← 测试失败则终止
└──────────────────┘
    ↓ 通过
┌──────────────────┐
│  构建前端+后端    │
└──────────────────┘
    ↓
┌──────────────────┐
│  打包成 tar.gz    │
└──────────────────┘
    ↓
┌──────────────────┐
│ WinRM 传输到ECS  │ ← 使用密码认证
└──────────────────┘
    ↓
┌──────────────────┐
│  PowerShell 解压  │
└──────────────────┘
    ↓
┌──────────────────┐
│  备份旧版本       │ ← C:\energy-system-backup
└──────────────────┘
    ↓
┌──────────────────┐
│  停止旧服务       │
└──────────────────┘
    ↓
┌──────────────────┐
│  部署新代码       │
└──────────────────┘
    ↓
┌──────────────────┐
│  pip install      │
└──────────────────┘
    ↓
┌──────────────────┐
│  启动Windows服务  │ ← NSSM 或任务计划
└──────────────────┘
    ↓
┌──────────────────┐
│  健康检查验证     │
└──────────────────┘
    ↓ 成功
✅ 部署完成！
```

---

## 🔄 日常操作速查

### 触发新部署
```bash
git push origin main  # 自动触发
```

### 查看部署进度
```
访问: https://github.com/YOUR_USERNAME/competitions/actions
```

### 查看日志

```powershell
# 应用日志
Get-Content D:\energy-system\logs\app.log -Tail 50

# 实时跟踪
Get-Content D:\energy-system\logs\app.log -Wait -Tail 10
```

### 回滚操作

```powershell
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

### 服务管理
``powershell
# 查看状态
Get-Service -Name EnergySystem

# 重启服务
Restart-Service EnergySystem
```

---

## ⚙️ 技术细节

### WinRM 配置要求

在 Windows ECS 上必须启用：
```powershell
Enable-PSRemoting -Force
winrm set winrm/config/service/auth @{Basic="true"}
New-NetFirewallRule -Name "WinRM_HTTPS" -Protocol TCP -LocalPort 5986 -Action Allow
```

### Windows 服务方案

**方案 A: NSSM（推荐）**
- 下载: https://nssm.cc/download
- 解压到 `C:\nssm\`
- 优势: 真正的 Windows 服务，支持自动重启

**方案 B: 任务计划程序（备选）**
- 无需额外软件
- 劣势: 功能相对简单

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

---

## ❓ 常见问题

### Q1: WinRM 连接超时？

```powershell
# 检查 WinRM 服务
Get-Service WinRM

# 测试连接
Test-WSMan -ComputerName localhost

# 检查防火墙
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*WinRM*" }

# 重启 WinRM
Restart-Service WinRM
```

### Q2: 部署失败，提示权限错误？

确保：
1. 以**管理员身份**运行 PowerShell
2. 执行策略允许：
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
   ```

### Q3: 如何修改部署目录？

编辑 `.github/workflows/deploy.yml`:
```
env:
  SERVER_DIR: D:\custom-path
  BACKUP_DIR: D:\custom-backup
```

同时修改 PowerShell 脚本中的默认路径。

### Q4: 服务启动后立即停止？

```
# 查看详细错误
Get-EventLog -LogName Application -Newest 20

# 检查端口占用
netstat -ano | findstr :8000

# 手动测试
cd D:\energy-system\server
python start_server.py
```

---

## 🔒 安全建议

1. ✅ **定期更改密码**: 至少每 90 天
2. ✅ **更新 GitHub Secrets**: 密码更改后立即同步
3. ✅ **启用 Windows 防火墙**: 仅开放 8000 和 5986 端口
4. ✅ **安装防病毒软件**: Windows Defender 或第三方
5. ✅ **定期系统更新**: Windows Update
6. ✅ **限制远程访问 IP**: 在阿里云安全组中配置

---

## 📞 获取帮助

- 📖 [Windows 专用指南](WINDOWS_DEPLOY_GUIDE.md)
- 📖 [详细部署文档](DEPLOYMENT_GUIDE.md)
- 📖 [快速参考卡片](QUICK_REFERENCE.md)
- 🐛 GitHub Issues
- 💬 GitHub Discussions

---

## 🎉 恭喜！

你现在拥有：
- ✅ **完全自动化**的 Windows ECS 部署
- ✅ **密码认证**（无需 SSH 密钥）
- ✅ **一键回滚**机制
- ✅ **实时监控**工具
- ✅ **完整的文档**支持

**从此告别手动 RDP 登录服务器部署！** 🚀

每次推送代码到 `main` 分支，都会自动部署到 `8.156.95.158`，全程无需任何手动操作！
