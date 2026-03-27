"""
测试 9 月数据集流式推送 API

使用方法:
1. 确保后端服务已启动
2. 运行此脚本：python test_september_stream.py
"""

import requests
import json
from datetime import datetime


def test_streaming_api():
    """测试流式推送接口"""
    print("=" * 60)
    print("测试 9 月数据集流式推送接口")
    print("=" * 60)
    
    url = "http://localhost:3000/api/export/september/stream"
    params = {
        "year": 2016,
        "batch_size": 10
    }
    
    print(f"\n请求 URL: {url}")
    print(f"参数：{params}")
    print("\n开始接收数据...\n")
    
    try:
        response = requests.get(url, params=params, stream=True, timeout=30)
        response.raise_for_status()
        
        received_count = 0
        total_records = 0
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                # 解析 SSE 消息
                if line.startswith('data: '):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        msg_type = data.get('type')
                        
                        if msg_type == 'start':
                            print(f"✓ {data.get('message')}")
                            
                        elif msg_type == 'progress':
                            current = data.get('current', 0)
                            total = data.get('total', 0)
                            print(f"→ 进度：{current}/{total} ({current/total*100:.1f}%)")
                            
                        elif msg_type == 'data':
                            records = data.get('records', [])
                            received_count += len(records)
                            total_records = len(records)
                            print(f"  收到批次：{len(records)} 条记录")
                            
                            # 显示第一条记录的简要信息
                            if records:
                                first = records[0]
                                ts = first.get('timestamp', '')
                                elec = first.get('electricity', 0)
                                print(f"    示例：时间={ts}, 用电量={elec} kWh")
                            
                        elif msg_type == 'complete':
                            print(f"\n✓ {data.get('message')}")
                            print(f"  总发送记录数：{data.get('total_sent', 0)}")
                            
                        elif msg_type == 'error':
                            print(f"✗ 错误：{data.get('message')}")
                            
                    except json.JSONDecodeError as e:
                        print(f"解析 JSON 失败：{e}")
                        print(f"原始数据：{data_str}")
        
        print("\n" + "=" * 60)
        print(f"测试完成！共接收 {received_count} 条数据")
        print("=" * 60)
        
    except requests.exceptions.Timeout:
        print("✗ 请求超时")
    except requests.exceptions.ConnectionError as e:
        print(f"✗ 连接错误：{e}")
        print("  请确保后端服务已启动 (http://localhost:3000)")
    except Exception as e:
        print(f"✗ 测试失败：{e}")


def test_batch_api():
    """测试分页查询接口"""
    print("\n" + "=" * 60)
    print("测试 9 月数据集分页查询接口")
    print("=" * 60)
    
    url = "http://localhost:3000/api/export/september/batch"
    params = {
        "year": 2016,
        "page": 1,
        "page_size": 10  # 修改为 10，符合 API 要求 (最小 10)
    }
    
    print(f"\n请求 URL: {url}")
    print(f"参数：{params}\n")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('code') == 200:
            data = result.get('data', {})
            records = data.get('records', [])
            pagination = data.get('pagination', {})
            
            print(f"✓ 查询成功")
            print(f"  本页记录数：{len(records)}")
            print(f"  总记录数：{pagination.get('total', 0)}")
            print(f"  当前页码：{pagination.get('page', 0)}")
            print(f"  总页数：{pagination.get('total_pages', 0)}")
            print(f"  是否有更多：{pagination.get('has_more', False)}")
            
            if records:
                print(f"\n前 3 条记录详情:")
                for i, record in enumerate(records[:3], 1):
                    print(f"\n  [{i}] ID={record.get('id')}")
                    print(f"      建筑：{record.get('building_id')}")
                    print(f"      时间：{record.get('timestamp')}")
                    print(f"      用电量：{record.get('electricity')} kWh")
        else:
            print(f"✗ 查询失败：{result.get('message')}")
            
    except requests.exceptions.Timeout:
        print("✗ 请求超时")
    except requests.exceptions.ConnectionError as e:
        print(f"✗ 连接错误：{e}")
        print("  请确保后端服务已启动 (http://localhost:3000)")
    except Exception as e:
        print(f"✗ 测试失败：{e}")


if __name__ == "__main__":
    print("\n🚀 9 月数据集流式推送 API 测试脚本\n")
    print("请确保后端服务已启动在 http://localhost:3000\n")
    
    # 测试流式接口
    test_streaming_api()
    
    # 测试分页接口
    test_batch_api()
    
    print("\n✅ 所有测试完成!\n")
