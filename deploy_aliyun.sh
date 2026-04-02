#!/bin/bash
# 阿里云服务器一键部署脚本

echo "=========================================="
echo "  建筑能源管理系统 - 一键部署脚本"
echo "=========================================="

# 更新系统
echo "[1/8] 更新系统..."
apt update && apt upgrade -y

# 安装 Python3 和 pip
echo "[2/8] 安装 Python3 和 pip..."
apt install -y python3 python3-pip python3-venv

# 安装 Git
echo "[3/8] 安装 Git..."
apt install -y git

# 安装 Nginx
echo "[4/8] 安装 Nginx..."
apt install -y nginx

# 创建项目目录
echo "[5/8] 创建项目目录..."
mkdir -p /var/www/competitions
cd /var/www/competitions

# 克隆代码
echo "[6/8] 克隆代码..."
git clone https://github.com/你的用户名/competitions.git .

# 创建虚拟环境
echo "[7/8] 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt

# 配置环境变量
echo "[8/8] 配置环境变量..."
cat > /var/www/competitions/server/.env << EOF
DB_HOST=gateway01.ap-northeast-1.prod.aws.tidbcloud.com
DB_PORT=4000
DB_NAME=energy_management
DB_USER=rLZxFGpCHUXzhD1.root
DB_PASSWORD=0xrt1Qt2lOxxL79k
SSL_CA=./certs/ca-cert.pem
SSL_MODE=VERIFY_IDENTITY
HOST=0.0.0.0
PORT=8000
EOF

# 配置 Nginx
echo "配置 Nginx..."
cat > /etc/nginx/sites-available/competitions << EOF
server {
    listen 80;
    server_name 你的域名或服务器 IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -s /etc/nginx/sites-available/competitions /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 配置 systemd 服务
echo "配置 systemd 服务..."
cat > /etc/systemd/system/competitions.service << EOF
[Unit]
Description=建筑能源管理系统后端
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/competitions/server
Environment="PATH=/var/www/competitions/venv/bin"
ExecStart=/var/www/competitions/venv/bin/python start_server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
echo "启动服务..."
systemctl daemon-reload
systemctl enable competitions
systemctl start competitions
systemctl restart nginx

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo "  访问地址：http://你的服务器 IP"
echo "  查看日志：journalctl -u competitions -f"
echo "  重启服务：systemctl restart competitions"
echo "=========================================="
