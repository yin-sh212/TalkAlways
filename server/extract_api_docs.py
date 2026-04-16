#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 接口提取脚本 - 改进版
从后端代码中提取所有 API 接口信息并生成文档
"""

import re
import os
from pathlib import Path

def extract_api_info(file_path):
    """从 Python 文件中提取 API 路由信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取 router 定义
    router_match = re.search(r'router = APIRouter\(prefix="([^"]+)",\s*tags=\["([^"]+)"\]\)', content)
    if not router_match:
        return None
    
    prefix = router_match.group(1)
    tag = router_match.group(2)
    
    # 提取所有路由装饰器
    routes = []
    route_pattern = r'@router\.(get|post|put|delete|patch)\("([^"]*)"\)'
    for match in re.finditer(route_pattern, content):
        method = match.group(1).upper()
        path_suffix = match.group(2)
        full_path = prefix + path_suffix
        
        # 查找函数名和描述（在装饰器后500字符内）
        func_start = match.end()
        func_section = content[func_start:func_start+800]
        
        # 提取函数定义
        func_match = re.search(r'async def (\w+)\(', func_section)
        func_name = func_match.group(1) if func_match else "unknown"
        
        # 提取文档字符串
        doc_match = re.search(r'"""([^"]+)"""', func_section, re.DOTALL)
        description = doc_match.group(1).strip().replace('\n', ' ') if doc_match else ""
        
        routes.append({
            'method': method,
            'path': full_path,
            'function': func_name,
            'description': description[:100]  # 限制描述长度
        })
    
    return {
        'tag': tag,
        'routes': routes
    }

def main():
    api_dir = Path('app/api')
    all_apis = []
    
    # 遍历所有 API 文件
    for file_path in sorted(api_dir.glob('*.py')):
        if file_path.name.startswith('__'):
            continue
        
        info = extract_api_info(file_path)
        if info and info['routes']:
            all_apis.append(info)
    
    # 输出结果到文件
    output_lines = []
    output_lines.append("=" * 100)
    output_lines.append("建筑能源管理系统 - 前后端接口清单")
    output_lines.append("=" * 100)
    output_lines.append(f"\n共发现 {len(all_apis)} 个 API 模块\n")
    
    total_routes = 0
    for api_info in all_apis:
        output_lines.append(f"\n{'='*100}")
        output_lines.append(f"【{api_info['tag']}】")
        output_lines.append(f"{'='*100}")
        
        for route in api_info['routes']:
            total_routes += 1
            output_lines.append(f"\n  {route['method']:6} {route['path']}")
            output_lines.append(f"         函数: {route['function']}")
            if route['description']:
                output_lines.append(f"         说明: {route['description']}")
    
    output_lines.append(f"\n{'='*100}")
    output_lines.append(f"总计: {total_routes} 个接口")
    output_lines.append(f"{'='*100}")
    
    # 写入文件
    output_text = '\n'.join(output_lines)
    with open('api_list.txt', 'w', encoding='utf-8') as f:
        f.write(output_text)
    
    # 同时打印到控制台
    print(output_text)
    print(f"\n✅ 接口清单已保存到 api_list.txt")

if __name__ == '__main__':
    main()
