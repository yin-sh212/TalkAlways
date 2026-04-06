#!/bin/bash
# monitor.sh - 系统健康监控脚本

set -e

ECS_HOST=${1:-localhost}
CHECK_INTERVAL=${2:-60}  # 默认60秒检查一次

echo "=========================================="
echo "能源管理系统健康监控"
echo "服务器: $ECS_HOST"
echo "检查间隔: ${CHECK_INTERVAL}s"
echo "=========================================="
echo ""

# 健康检查函数
check_health() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # 检查 HTTP 服务
    if curl -sf http://$ECS_HOST:8000/api/health > /dev/null 2>&1; then
        echo "[$timestamp] ✓ 服务正常"
        return 0
    else
        echo "[$timestamp] ✗ 服务异常"
        return 1
    fi
}

# 检查系统资源
check_resources() {
    echo "--- 系统资源 ---"
    
    # CPU 使用率
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    echo "CPU 使用率: ${cpu_usage}%"
    
    # 内存使用率
    memory_info=$(free -m | grep Mem)
    total_mem=$(echo $memory_info | awk '{print $2}')
    used_mem=$(echo $memory_info | awk '{print $3}')
    mem_percent=$((used_mem * 100 / total_mem))
    echo "内存使用: ${used_mem}MB / ${total_mem}MB (${mem_percent}%)"
    
    # 磁盘使用率
    disk_usage=$(df -h / | tail -1 | awk '{print $5}')
    echo "磁盘使用: $disk_usage"
    
    echo ""
}

# 检查服务状态
check_service() {
    echo "--- 服务状态 ---"
    
    if systemctl is-active --quiet energy-system; then
        echo "✓ 服务运行中"
        
        # 获取进程信息
        pid=$(systemctl show energy-system -p MainPID --value)
        echo "  PID: $pid"
        
        # 运行时间
        uptime=$(systemctl show energy-system -p ActiveEnterTimestamp --value)
        echo "  启动时间: $uptime"
    else
        echo "✗ 服务未运行"
    fi
    
    echo ""
}

# 检查数据库连接
check_database() {
    echo "--- 数据库状态 ---"
    
    if mysql -u root -e "SELECT 1" &> /dev/null; then
        echo "✓ MySQL 连接正常"
        
        # 数据库大小
        db_size=$(mysql -u root -e "SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' FROM information_schema.tables WHERE table_schema='energy_system';" | tail -1)
        echo "  数据库大小: ${db_size} MB"
    else
        echo "✗ MySQL 连接失败"
    fi
    
    echo ""
}

# 查看最近日志
check_recent_logs() {
    echo "--- 最近日志 (最后10条) ---"
    
    if [ -f /opt/energy-system/logs/app.log ]; then
        tail -10 /opt/energy-system/logs/app.log
    else
        echo "日志文件不存在"
    fi
    
    echo ""
}

# 主监控循环
monitor_loop() {
    while true; do
        clear
        echo "=========================================="
        echo "实时监控 - $(date)"
        echo "=========================================="
        echo ""
        
        check_health
        echo ""
        check_resources
        check_service
        check_database
        
        echo "按 Ctrl+C 退出监控"
        sleep $CHECK_INTERVAL
    done
}

# 一次性检查
one_time_check() {
    check_health || exit 1
    check_resources
    check_service
    check_database
    check_recent_logs
}

# 根据参数选择模式
if [ "$1" = "--continuous" ] || [ "$1" = "-c" ]; then
    monitor_loop
else
    one_time_check
fi
