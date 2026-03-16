# -*- coding: utf-8 -*-
"""
数据解析和格式化模块
"""

from datetime import datetime
from typing import Optional, List, Dict


class DataParser:
    """数据解析器"""

    @staticmethod
    def parse_dewpoint(text: str) -> Optional[float]:
        """解析露点温度"""
        import re
        match = re.search(r'Tdf\s*=\s*([-+]?\d+\.?\d*)', text)
        return float(match.group(1)) if match else None

    @staticmethod
    def parse_dewpoint_atm(text: str) -> Optional[float]:
        """解析标准气压露点"""
        import re
        match = re.search(r'Tdfatm\s*=\s*([-+]?\d+\.?\d*)', text)
        return float(match.group(1)) if match else None

    @staticmethod
    def parse_h2o_ppm(text: str) -> Optional[float]:
        """解析体积含水量"""
        import re
        match = re.search(r'H2O\s*=\s*(\d+)', text)
        return float(match.group(1)) if match else None


class DataFormatter:
    """数据格式化器"""

    @staticmethod
    def format_dewpoint(value: float, unit: str = "°C") -> str:
        """格式化露点温度"""
        return f"{value:.2f} {unit}"

    @staticmethod
    def format_h2o(value: float, unit: str = "ppm") -> str:
        """格式化体积含水量"""
        return f"{value:.0f} {unit}"

    @staticmethod
    def format_timestamp(fmt: str = "%H:%M:%S") -> str:
        """格式化时间戳"""
        return datetime.now().strftime(fmt)


class DataRecord:
    """数据记录"""

    def __init__(self, dewpoint: float = None, dewpoint_atm: float = None,
                 h2o_ppm: float = None):
        self.timestamp = datetime.now()
        self.dewpoint = dewpoint
        self.dewpoint_atm = dewpoint_atm
        self.h2o_ppm = h2o_ppm

    def to_dict(self) -> dict:
        return {
            'time': self.timestamp.strftime("%H:%M:%S"),
            'dewpoint': self.dewpoint,
            'dewpoint_atm': self.dewpoint_atm,
            'h2o_ppm': self.h2o_ppm
        }

    def to_csv_row(self) -> list:
        return [
            self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            f"{self.dewpoint:.2f}" if self.dewpoint else "",
            f"{self.dewpoint_atm:.2f}" if self.dewpoint_atm else "",
            f"{self.h2o_ppm:.0f}" if self.h2o_ppm else ""
        ]


class DataHistory:
    """历史数据管理"""

    def __init__(self, max_points: int = 1000):
        self.max_points = max_points
        self.records: List[DataRecord] = []
        self.dewpoint_history: List[float] = []

    def add_record(self, data: dict):
        """添加数据记录"""
        record = DataRecord(
            dewpoint=data.get('dewpoint'),
            dewpoint_atm=data.get('dewpoint_atm'),
            h2o_ppm=data.get('h2o_ppm')
        )
        self.records.append(record)

        if record.dewpoint is not None:
            self.dewpoint_history.append(record.dewpoint)
            if len(self.dewpoint_history) > self.max_points:
                self.dewpoint_history.pop(0)

        if len(self.records) > self.max_points:
            self.records.pop(0)

    def clear(self):
        """清空历史数据"""
        self.records.clear()
        self.dewpoint_history.clear()

    def to_csv(self) -> str:
        """导出为CSV格式"""
        lines = ["时间,露点温度(°C),标准气压露点(°C),体积含水量(ppm)\n"]
        for record in self.records:
            lines.append(",".join(record.to_csv_row()) + "\n")
        return "".join(lines)

    def get_dewpoint_list(self) -> List[float]:
        """获取露点历史数据"""
        return self.dewpoint_history.copy()
