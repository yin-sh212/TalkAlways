# SQL建表语句（供参考和执行）
CREATE_TABLES_SQL = """
-- 建筑信息表
CREATE TABLE IF NOT EXISTS buildings (
    id VARCHAR(50) PRIMARY KEY COMMENT '建筑编号',
    name VARCHAR(100) COMMENT '建筑名称',
    type VARCHAR(50) COMMENT '类型：办公楼/教学楼/医院等',
    area FLOAT COMMENT '建筑面积(㎡)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='建筑信息表';

-- 能耗监测点表
CREATE TABLE IF NOT EXISTS meters (
    id VARCHAR(50) PRIMARY KEY COMMENT '设备编号',
    building_id VARCHAR(50) COMMENT '所属建筑编号',
    type VARCHAR(30) COMMENT '类型：电/水/空调',
    status VARCHAR(20) DEFAULT 'normal' COMMENT '状态：normal/abnormal',
    installed_at DATE COMMENT '安装日期',
    FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='监测点表';

-- 能耗数据表（核心）
CREATE TABLE IF NOT EXISTS energy_consumption (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    building_id VARCHAR(50) COMMENT '建筑编号',
    meter_id VARCHAR(50) COMMENT '设备编号',
    timestamp DATETIME COMMENT '监测时间',
    electricity FLOAT COMMENT '用电量(kWh)',
    water FLOAT COMMENT '用水量(m³)',
    supply_temp FLOAT COMMENT '出水温度(℃)',
    return_temp FLOAT COMMENT '回水温度(℃)',
    ambient_temp FLOAT COMMENT '环境温度(℃)',
    humidity FLOAT COMMENT '湿度(%RH)',
    occupancy FLOAT COMMENT '人员密度(人/100㎡)',
    is_anomaly BOOLEAN DEFAULT FALSE COMMENT '是否异常',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_building_time (building_id, timestamp),
    INDEX idx_meter_time (meter_id, timestamp),
    FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE,
    FOREIGN KEY (meter_id) REFERENCES meters(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='能耗数据表';
"""