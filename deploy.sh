#!/bin/bash
# deploy.sh - 自动化部署脚本
# 用法: bash deploy.sh <目标目录> <备份目录>

set -e  # 遇到错误立即退出

TARGET_DIR=${1:-/opt/energy-system}
BACKUP_DIR=${2:-/opt/energy-system-backup}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "开始部署能源管理系统"
echo "时间: $(date)"
echo "目标目录: $TARGET_DIR"
echo "备份目录: $BACKUP_DIR"
echo "=========================================="

# 1. 创建备份
echo "[1/6] 创建备份..."
if [ -d "$TARGET_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    cp -r "$TARGET_DIR" "$BACKUP_DIR/backup_$TIMESTAMP"
    echo "✓ 备份完成: $BACKUP_DIR/backup_$TIMESTAMP"
else
    echo "ℹ 首次部署，跳过备份"
fi

# 2. 停止旧服务
echo "[2/6] 停止旧服务..."
if systemctl is-active --quiet energy-system; then
    sudo systemctl stop energy-system
    echo "✓ 服务已停止"
else
    echo "ℹ 服务未运行"
fi

# 3. 部署新代码
echo "[3/6] 部署新代码..."
mkdir -p "$TARGET_DIR"
rm -rf "$TARGET_DIR/server" "$TARGET_DIR/client-dist"
cp -r server "$TARGET_DIR/"
cp -r client-dist "$TARGET_DIR/"
echo "✓ 代码部署完成"

# 4. 安装依赖
echo "[4/6] 安装Python依赖..."
cd "$TARGET_DIR/server"
python3 -m pip install --upgrade pip -q
python3 -m pip install -r requirements.txt -q
echo "✓ 依赖安装完成"

# 5. 配置systemd服务
echo "[5/6] 配置系统服务..."
cat > /tmp/energy-system.service <<EOF
[Unit]
Description=Energy Management System
After=network.target mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=$TARGET_DIR/server
Environment="PYTHONPATH=$TARGET_DIR/server"
ExecStart=/usr/bin/python3 start_server.py
Restart=always
RestartSec=10
StandardOutput=append:$TARGET_DIR/logs/app.log
StandardError=append:$TARGET_DIR/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/energy-system.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable energy-system
echo "✓ 服务配置完成"

# 6. 启动新服务
echo "[6/6] 启动新服务..."
mkdir -p "$TARGET_DIR/logs"
sudo systemctl start energy-system
sleep 3

# 验证服务状态
if systemctl is-active --quiet energy-system; then
    echo "✓ 服务启动成功"
    echo "=========================================="
    echo "部署完成！"
    echo "访问地址: http://$(hostname -I | awk '{print $1}'):8000"
    echo "=========================================="
else
    echo "✗ 服务启动失败，查看日志:"
    sudo journalctl -u energy-system -n 50 --no-pager
    exit 1
fi
