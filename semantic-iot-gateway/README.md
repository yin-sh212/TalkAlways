# Semantic IoT Gateway

独立的 Python 边缘采集 Agent，部署在建筑现场网段内的电脑上。

如果你要按图形界面一步一步操作，先看：

- [操作手册.md](E:/ALtool/chuang4/TalkAlways/semantic-iot-gateway/操作手册.md)

当前版本只做在线运行段：

- 已知 IP 设备导入
- 手动单次扫网段
- `Modbus TCP` 采集
- `BACnet/IP` 采集
- 统一标准化
- 微批量推送到 ECS 的 HTTP 接口

不依赖现有 `TalkAlways/client` 或 `TalkAlways/server` 运行。

## 目录

- `configs/demo_gateway.json`
  - 样例设备配置
- `semantic_iot_gateway/models.py`
  - 统一配置模型和输出契约
- `semantic_iot_gateway/collectors/modbus_tcp.py`
  - Modbus TCP 采集器
- `semantic_iot_gateway/collectors/bacnet_ip.py`
  - BACnet/IP 采集器和 Who-Is 管理器
- `semantic_iot_gateway/probe.py`
  - 单次探测工具
- `semantic_iot_gateway/sinks.py`
  - 标准输出和 HTTP 推送

## 环境

```powershell
cd E:\ALtool\chuang4\TalkAlways\semantic-iot-gateway
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## 桌面界面

提供了一个本地 `Tkinter` 桌面 GUI，用来做：

- 加载和编辑 JSON 配置
- 配置校验和保存
- Modbus 单次探测
- BACnet 单次探测
- 启动/停止网关
- 查看运行日志

启动方式：

```powershell
.\.venv\Scripts\python -m semantic_iot_gateway gui --config .\configs\demo_gateway.json
```

## 已知 IP 导入

当前版本的主接入方式是编辑 JSON 配置文件，然后直接运行：

```powershell
.\.venv\Scripts\python -m semantic_iot_gateway validate --config .\configs\demo_gateway.json
```

把设备的 `host / port / protocol / points` 配好后，把对应设备的 `enabled` 改成 `true` 即可。

## 单次扫网段

### Modbus TCP

```powershell
.\.venv\Scripts\python -m semantic_iot_gateway probe-modbus --cidr 192.168.10.0/24
```

或者扫已知主机：

```powershell
.\.venv\Scripts\python -m semantic_iot_gateway probe-modbus --hosts 192.168.10.20,192.168.10.21
```

### BACnet/IP

```powershell
.\.venv\Scripts\python -m semantic_iot_gateway probe-bacnet --local-address 192.168.10.8/24
```

如果跨子网或需要定向探测，可以带 `--target-address`。

## 运行

```powershell
.\.venv\Scripts\python -m semantic_iot_gateway run --config .\configs\demo_gateway.json
```

调试时也可以限制运行时长：

```powershell
.\.venv\Scripts\python -m semantic_iot_gateway run --config .\configs\demo_gateway.json --duration 10
```

## 当前输出格式

Agent 内部实时采集，但对 ECS 的输出是微批量 HTTP，上报结构如下：

```json
{
  "schema": "talkalways.iot.ingest.batch.v1",
  "gateway_id": "building-edge-01",
  "site_id": "eagle-edu",
  "sent_at": "2026-04-08T12:00:00Z",
  "batch_id": "....",
  "sequence": 1,
  "readings": [
    {
      "timestamp": "2026-04-08T12:00:00Z",
      "building_id": "Eagle_education_Cassie",
      "device_id": "modbus-meter-01",
      "device_type": "power_meter",
      "point_id": "main_power_kw",
      "tag": "Eagle_Edu_MainPower",
      "standard_tag": "power",
      "protocol": "modbus_tcp",
      "raw_value": 1254.0,
      "value": 125.4,
      "unit": "kW",
      "quality": "good",
      "status": "online",
      "source_address": {
        "register_type": "holding",
        "address": 40001,
        "unit_id": 1,
        "register_count": 2
      }
    }
  ],
  "device_states": [
    {
      "observed_at": "2026-04-08T12:00:00Z",
      "building_id": "Eagle_education_Cassie",
      "device_id": "modbus-meter-01",
      "device_type": "power_meter",
      "protocol": "modbus_tcp",
      "status": "online",
      "quality": "good",
      "latency_ms": 45.3,
      "error": null
    }
  ]
}
```

## 说明

- 边缘端内部是实时异步轮询
- 云端上报采用微批量推送，不是逐点长连接
- Modbus 发现只做 TCP 连通性探测，不尝试自动推断点位表
- BACnet 支持 `Who-Is / I-Am` 单次发现

## 已知边界

- Modbus 当前按点逐个读取，后续可以优化成寄存器分组批读
- BACnet 当前按点 `read_property`，未实现 `read_property_multiple`
- 还没有接入 TalkAlways ECS 侧消费接口，只先约定了批量 JSON 契约

