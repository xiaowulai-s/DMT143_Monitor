# -*- coding: utf-8 -*-
"""
曲线图表组件 - 极简安全版，避免 pyqtgraph C++ 层崩溃
"""

import math
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg


class ChartWidget(QWidget):
    """实时曲线图表组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_points = 200
        self.dewpoint_data = []
        self.time_data = []
        self._point_count = 0

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#ffffff')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(-100, 50)

        # 延迟创建曲线对象，等 Widget 完全初始化后再用
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#3498db', width=2)
        )

        self.plot_widget.setLabel('left', '温度', units='°C')
        self.plot_widget.getAxis('bottom').setLabel('时间')

        self.plot_widget.setStyleSheet("""
            QWidget {
                border: 2px solid #4a90d9;
                border-radius: 8px;
                background-color: #ffffff;
            }
        """)

        layout.addWidget(self.plot_widget)

    def add_data(self, value: float):
        """添加数据点——只做 setData，避免频繁调 ticks/YRange 引发 C 层崩溃"""
        if value is None:
            return

        # NaN / Inf 过滤
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        if not math.isfinite(value):
            return

        # 限幅
        value = max(-120, min(70, value))

        self.dewpoint_data.append(value)
        self.time_data.append(datetime.now().strftime("%H:%M:%S"))

        # 保持数据点数量
        if len(self.dewpoint_data) > self.max_points:
            self.dewpoint_data.pop(0)
            self.time_data.pop(0)

        self._point_count += 1

        # 核心：更新曲线数据（最小渲染调用）
        try:
            self.curve.setData(self.dewpoint_data)
        except Exception:
            pass

        # 每 20 个数据点才更新一次轴标签和范围（降低渲染频率）
        if self._point_count % 20 != 0:
            return

        # X 轴标签
        try:
            if len(self.time_data) > 0:
                ticks = []
                step = max(1, len(self.time_data) // 5)
                for i in range(0, len(self.time_data), step):
                    ticks.append((i, self.time_data[i]))
                self.plot_widget.getAxis('bottom').setTicks([ticks])
        except Exception:
            pass

        # Y 轴范围
        try:
            if len(self.dewpoint_data) > 2:
                y_min = min(self.dewpoint_data) - 10
                y_max = max(self.dewpoint_data) + 10
                y_min = max(-100, y_min)
                y_max = min(50, y_max)
                if y_max - y_min < 1.0:
                    y_min -= 5
                    y_max += 5
                self.plot_widget.setYRange(y_min, y_max)
        except Exception:
            pass

    def clear(self):
        self.dewpoint_data.clear()
        self.time_data.clear()
        self._point_count = 0
        try:
            self.curve.setData([])
        except Exception:
            pass
