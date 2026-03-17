# app/services/nl2sql_service.py
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import calendar


class NL2SQLService:
    """自然语言转SQL服务（适配真实数据）"""

    def __init__(self):
        # 建筑ID模式（你的数据中的格式）
        self.building_pattern = r'(Eagle_education_Wesley|Eagle_education_Cassie|Eagle_office_Nereida|Eagle_office_Henriette|Eagle_office_Francis|Fox_lodging_Wallace|Fox_lodging_Helen|Fox_education_Jacqueline|Fox_assembly_Renna|Fox_assembly_Adrianne)'

        # 时间关键词映射
        self.time_keywords = {
            '今天': 'CURDATE()',
            '昨天': 'CURDATE() - INTERVAL 1 DAY',
            '前天': 'CURDATE() - INTERVAL 2 DAY',
            '本周': 'YEARWEEK(timestamp) = YEARWEEK(CURDATE())',
            '上周': 'YEARWEEK(timestamp) = YEARWEEK(CURDATE() - INTERVAL 7 DAY)',
            '本月': 'MONTH(timestamp) = MONTH(CURDATE()) AND YEAR(timestamp) = YEAR(CURDATE())',
            '上月': 'MONTH(timestamp) = MONTH(CURDATE() - INTERVAL 1 MONTH) AND YEAR(timestamp) = YEAR(CURDATE())',
        }

        # 月份映射
        self.month_map = {
            '1月': 1, '一月': 1, 'january': 1,
            '2月': 2, '二月': 2, 'february': 2,
            '3月': 3, '三月': 3, 'march': 3,
            '4月': 4, '四月': 4, 'april': 4,
            '5月': 5, '五月': 5, 'may': 5,
            '6月': 6, '六月': 6, 'june': 6,
            '7月': 7, '七月': 7, 'july': 7,
            '8月': 8, '八月': 8, 'august': 8,
        }

    def parse(self, query: str) -> Dict[str, Any]:
        """解析自然语言，返回SQL参数"""
        query = query.lower().strip()

        # 1. 识别查询类型
        if any(k in query for k in ['用电量', '耗电量', '电力消耗', 'electricity']):
            return self._parse_energy_query(query)
        elif any(k in query for k in ['冷冻水', '冷量', 'cooling']):
            return self._parse_cooling_query(query)
        elif any(k in query for k in ['供热', 'heating']):
            return self._parse_heating_query(query)
        elif any(k in query for k in ['气温', '温度', 'temperature']):
            return self._parse_temperature_query(query)
        elif any(k in query for k in ['统计', '汇总', '总计']):
            return self._parse_statistics_query(query)
        elif any(k in query for k in ['异常', '故障', '异常点']):
            return self._parse_anomaly_query(query)
        elif any(k in query for k in ['比较', '对比', '哪个建筑', '最高', '最低']):
            return self._parse_comparison_query(query)
        else:
            return {
                "type": "unknown",
                "sql": None,
                "params": [],
                "message": "无法理解您的查询"
            }

    def _parse_building(self, query: str) -> tuple:
        """解析建筑ID"""
        match = re.search(self.building_pattern, query, re.IGNORECASE)
        if match:
            return "building_id = %s", [match.group(1)]
        return "", []

    def _parse_time(self, query: str) -> tuple:
        """解析时间表达式"""
        params = []

        # 1. 处理今天/昨天等关键词
        for keyword, condition in self.time_keywords.items():
            if keyword in query:
                return condition, []

        # 2. 处理具体日期 (如 2016年7月1日)
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', query)
        if date_match:
            year, month, day = date_match.groups()
            date_str = f"{year}-{int(month):02d}-{int(day):02d}"
            return "DATE(timestamp) = %s", [date_str]

        # 3. 处理带日的短语 (如 "7月1日")
        date_match2 = re.search(r'(\d{1,2})月(\d{1,2})日', query)
        if date_match2:
            month, day = date_match2.groups()
            # 假设是2016年（你的数据年份）
            date_str = f"2016-{int(month):02d}-{int(day):02d}"
            return "DATE(timestamp) = %s", [date_str]

        # 4. 处理月份 (如 7月)
        for month_name, month_num in self.month_map.items():
            if month_name in query:
                # 检查是否包含"日"字，如果有说明是具体日期
                if '日' not in query:
                    return "MONTH(timestamp) = %s AND YEAR(timestamp) = %s", [month_num, 2016]

        return "", []

    def _parse_aggregation(self, query: str) -> str:
        """解析聚合函数，智能判断时间粒度"""
        # 判断是否是日查询
        is_daily = any(k in query for k in ['今天', '昨天', '前天', '日', '每天'])

        if any(k in query for k in ['平均', '均值', 'avg']):
            return 'AVG'
        elif any(k in query for k in ['最大', '最高', 'max']):
            return 'MAX'
        elif any(k in query for k in ['最小', '最低', 'min']):
            return 'MIN'
        else:
            # 如果是日查询，用SUM（因为一天有24小时）
            if is_daily:
                return 'SUM'
            else:
                return 'SUM'  # 默认还是SUM，但在返回时说明

    def _parse_energy_query(self, query: str) -> Dict[str, Any]:
        """解析用电量查询 - 智能判断"""
        agg_func = self._parse_aggregation(query)

        # 如果是"昨天"这种短时间，用SUM
        if '昨天' in query or '今天' in query:
            agg_func = 'SUM'
        # 如果是"7月"这种长时间，也用SUM（但应该提示）
        elif any(m in query for m in ['月', '月份']):
            agg_func = 'SUM'
        # 如果是"平均"，保持AVG

        sql = f"SELECT {agg_func}(electricity) as value FROM energy_consumption WHERE 1=1"
        # ... 其余代码
        params = []

        # 建筑条件
        building_cond, building_params = self._parse_building(query)
        if building_cond:
            sql += f" AND {building_cond}"
            params.extend(building_params)

        # 时间条件
        time_cond, time_params = self._parse_time(query)
        if time_cond:
            sql += f" AND {time_cond}"
            params.extend(time_params)

        return {
            "type": "energy",
            "sql": sql,
            "params": params,
            "aggregation": agg_func
        }

    def _parse_cooling_query(self, query: str) -> Dict[str, Any]:
        """解析冷冻水冷量查询"""
        agg_func = self._parse_aggregation(query)

        sql = f"SELECT {agg_func}(cooling_load) as value FROM energy_consumption WHERE 1=1"
        params = []

        building_cond, building_params = self._parse_building(query)
        if building_cond:
            sql += f" AND {building_cond}"
            params.extend(building_params)

        time_cond, time_params = self._parse_time(query)
        if time_cond:
            sql += f" AND {time_cond}"
            params.extend(time_params)

        return {
            "type": "cooling",
            "sql": sql,
            "params": params
        }

    def _parse_heating_query(self, query: str) -> Dict[str, Any]:
        """解析供热能耗查询"""
        agg_func = self._parse_aggregation(query)

        sql = f"SELECT {agg_func}(heating_load) as value FROM energy_consumption WHERE 1=1"
        params = []

        building_cond, building_params = self._parse_building(query)
        if building_cond:
            sql += f" AND {building_cond}"
            params.extend(building_params)

        time_cond, time_params = self._parse_time(query)
        if time_cond:
            sql += f" AND {time_cond}"
            params.extend(time_params)

        return {
            "type": "heating",
            "sql": sql,
            "params": params
        }

    def _parse_temperature_query(self, query: str) -> Dict[str, Any]:
        """解析气温查询"""
        agg_func = self._parse_aggregation(query)

        sql = f"SELECT {agg_func}(ambient_temp) as value FROM energy_consumption WHERE 1=1"
        params = []

        building_cond, building_params = self._parse_building(query)
        if building_cond:
            sql += f" AND {building_cond}"
            params.extend(building_params)

        time_cond, time_params = self._parse_time(query)
        if time_cond:
            sql += f" AND {time_cond}"
            params.extend(time_params)

        return {
            "type": "temperature",
            "sql": sql,
            "params": params
        }

    def _parse_statistics_query(self, query: str) -> Dict[str, Any]:
        """解析统计查询"""
        sql = """
            SELECT 
                DATE(timestamp) as date,
                SUM(electricity) as total_elec,
                AVG(electricity) as avg_elec,
                MAX(electricity) as max_elec,
                SUM(cooling_load) as total_cooling,
                AVG(ambient_temp) as avg_temp
            FROM energy_consumption
            WHERE 1=1
        """
        params = []

        # 建筑条件
        building_cond, building_params = self._parse_building(query)
        if building_cond:
            sql += f" AND {building_cond}"
            params.extend(building_params)

        # 时间条件
        time_cond, time_params = self._parse_time(query)
        if time_cond:
            sql += f" AND {time_cond}"
            params.extend(time_params)

        sql += " GROUP BY DATE(timestamp) ORDER BY date"

        return {
            "type": "statistics",
            "sql": sql,
            "params": params
        }

    def _parse_anomaly_query(self, query: str) -> Dict[str, Any]:
        """解析异常查询 - 修复版"""
        sql = """
            SELECT timestamp, building_id, electricity, ambient_temp
            FROM energy_consumption
            WHERE is_anomaly = 1
        """
        params = []

        # 建筑条件
        building_cond, building_params = self._parse_building(query)
        if building_cond:
            sql += f" AND {building_cond}"
            params.extend(building_params)

        # 时间条件
        time_cond, time_params = self._parse_time(query)
        if time_cond:
            sql += f" AND {time_cond}"
            params.extend(time_params)

        sql += " ORDER BY timestamp DESC LIMIT 20"

        return {
            "type": "anomaly",
            "sql": sql,
            "params": params
        }

    def _parse_comparison_query(self, query: str) -> Dict[str, Any]:
        """解析对比查询"""
        sql = """
            SELECT 
                building_id,
                SUM(electricity) as total_elec,
                AVG(electricity) as avg_elec
            FROM energy_consumption
            WHERE 1=1
        """
        params = []

        # 时间条件
        time_cond, time_params = self._parse_time(query)
        if time_cond:
            sql += f" AND {time_cond}"
            params.extend(time_params)

        # 排序方向
        if any(k in query for k in ['最高', '最大']):
            sql += " GROUP BY building_id ORDER BY total_elec DESC"
        elif any(k in query for k in ['最低', '最小']):
            sql += " GROUP BY building_id ORDER BY total_elec ASC"
        else:
            sql += " GROUP BY building_id ORDER BY total_elec DESC"

        sql += " LIMIT 10"

        return {
            "type": "comparison",
            "sql": sql,
            "params": params
        }


# 全局实例
nl2sql = NL2SQLService()