#!/bin/bash
# rollback.sh - 一键回滚脚本
# 用法: bash rollback.sh [备份版本号]

set -e

BACKUP_DIR=${1:-/opt/energy-system-backup}
TARGET_DIR=/opt/energy-system

echo "=========================================="
echo "能源管理系统回滚工具"
echo "=========================================="

# 列出可用备份
echo "可用的备份版本:"
ls -lt "$BACKUP_DIR" | grep "^d" | awk '{print $9}' | head -10
echo ""

# 如果没有指定版本，使用最新的备份
if [ -z "$2" ]; then
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR" | head -1)
    echo "使用最新备份: $LATEST_BACKUP"
    BACKUP_PATH="$BACKUP_DIR/$LATEST_BACKUP"
else
    BACKUP_PATH="$BACKUP_DIR/$2"
fi

# 验证备份存在
if [ ! -d "$BACKUP_PATH" ]; then
    echo "✗ 错误: 备份不存在: $BACKUP_PATH"
    exit 1
fi

echo ""
echo "准备回滚到: $BACKUP_PATH"
read -p "确认回滚? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "取消回滚"
    exit 0
fi

# 1. 停止当前服务
echo "[1/4] 停止当前服务..."
sudo systemctl stop energy-system
echo "✓ 服务已停止"

# 2. 备份当前版本（以防需要再次回滚）
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "[2/4] 备份当前版本..."
mkdir -p "$BACKUP_DIR"
cp -r "$TARGET_DIR" "$BACKUP_DIR/pre_rollback_$TIMESTAMP"
echo "✓ 当前版本已备份"

# 3. 恢复备份
echo "[3/4] 恢复备份..."
rm -rf "$TARGET_DIR/server" "$TARGET_DIR/client-dist"
cp -r "$BACKUP_PATH/server" "$TARGET_DIR/"
cp -r "$BACKUP_PATH/client-dist" "$TARGET_DIR/"
echo "✓ 备份恢复完成"

# 4. 启动服务
echo "[4/4] 启动服务..."
sudo systemctl start energy-system
sleep 3

if systemctl is-active --quiet energy-system; then
    echo "✓ 回滚成功！服务已恢复"
    echo "=========================================="
    echo "回滚完成"
    echo "回滚版本: $BACKUP_PATH"
    echo "访问地址: http://$(hostname -I | awk '{print $1}'):8000"
    echo "=========================================="
else
    echo "✗ 服务启动失败"
    sudo journalctl -u energy-system -n 50 --no-pager
    exit 1
fi
