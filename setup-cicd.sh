#!/bin/bash
# setup-cicd.sh - CI/CD 环境初始化脚本

set -e

echo "=========================================="
echo "CI/CD 自动化部署环境配置"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查必要工具
check_requirements() {
    echo -e "${YELLOW}[检查] 验证必要工具...${NC}"
    
    if ! command -v git &> /dev/null; then
        echo -e "${RED}✗ Git 未安装${NC}"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python3 未安装${NC}"
        exit 1
    fi
    
    if ! command -v node &> /dev/null; then
        echo -e "${RED}✗ Node.js 未安装${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 所有必要工具已安装${NC}"
    echo ""
}

# 生成 SSH 密钥
generate_ssh_key() {
    echo -e "${YELLOW}[配置] 生成 SSH 密钥对...${NC}"
    
    SSH_KEY_PATH="$HOME/.ssh/ecs_deploy_key"
    
    if [ -f "$SSH_KEY_PATH" ]; then
        echo "SSH 密钥已存在"
        read -p "是否重新生成? (yes/no): " regenerate
        if [ "$regenerate" != "yes" ]; then
            echo "使用现有密钥"
            return
        fi
    fi
    
    ssh-keygen -t rsa -b 4096 -C "github-actions@energy-system" -f "$SSH_KEY_PATH" -N ""
    
    echo ""
    echo -e "${GREEN}✓ SSH 密钥生成完成${NC}"
    echo "公钥位置: ${SSH_KEY_PATH}.pub"
    echo ""
    echo "请将以下内容添加到 ECS 服务器的 ~/.ssh/authorized_keys:"
    echo "----------------------------------------"
    cat "${SSH_KEY_PATH}.pub"
    echo "----------------------------------------"
    echo ""
    echo "然后将私钥内容添加到 GitHub Secrets:"
    echo "cat $SSH_KEY_PATH"
    echo ""
    
    read -p "按回车继续..."
}

# 配置 GitHub Secrets
configure_github_secrets() {
    echo -e "${YELLOW}[配置] GitHub Secrets 设置指南${NC}"
    echo ""
    echo "请在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加:"
    echo ""
    echo "1. ECS_HOST - ECS 服务器公网 IP"
    echo "2. ECS_USERNAME - SSH 登录用户名 (通常是 root)"
    echo "3. ECS_SSH_KEY - SSH 私钥内容"
    echo "4. ECS_PORT - SSH 端口 (可选, 默认 22)"
    echo ""
    echo "获取私钥内容:"
    echo "cat $HOME/.ssh/ecs_deploy_key"
    echo ""
    
    read -p "已完成配置? (yes/no): " configured
    if [ "$configured" != "yes" ]; then
        echo "请先完成配置再继续"
        exit 1
    fi
}

# 推送代码触发部署
trigger_deployment() {
    echo -e "${YELLOW}[部署] 准备触发首次部署...${NC}"
    echo ""
    
    read -p "是否现在推送代码触发部署? (yes/no): " deploy_now
    
    if [ "$deploy_now" = "yes" ]; then
        git add .
        git commit -m "feat: 添加 CI/CD 自动化部署配置" || echo "没有需要提交的更改"
        git push origin main || git push origin master
        echo ""
        echo -e "${GREEN}✓ 代码已推送，GitHub Actions 将自动触发部署${NC}"
        echo ""
        echo "查看部署进度: https://github.com/YOUR_USERNAME/competitions/actions"
    else
        echo "稍后手动推送代码即可触发部署"
    fi
}

# 主流程
main() {
    check_requirements
    generate_ssh_key
    configure_github_secrets
    trigger_deployment
    
    echo ""
    echo -e "${GREEN}=========================================="
    echo "配置完成！"
    echo "==========================================${NC}"
    echo ""
    echo "后续操作:"
    echo "1. 在 ECS 服务器上运行: bash deploy.sh"
    echo "2. 访问: http://YOUR_ECS_IP:8000"
    echo "3. 查看详细文档: DEPLOYMENT_GUIDE.md"
    echo ""
}

main
