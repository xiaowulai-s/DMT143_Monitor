# -*- coding: utf-8 -*-
"""
曲线图表组件 - 使用PyQtGraph实现
"""

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
        
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 图表（不带标题，因为主窗口已经有了）
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#ffffff')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # 设置Y轴范围
        self.plot_widget.setYRange(-100, 50)
        
        # 曲线
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#3498db', width=2)
        )
        
        # 标签
        self.plot_widget.setLabel('left', '温度', units='°C')
        
        # 设置X轴显示时间
        self.plot_widget.getAxis('bottom').setLabel('时间')
        
        # 样式
        self.plot_widget.setStyleSheet("""
            QWidget {
                border: 2px solid #4a90d9;
                border-radius: 8px;
                background-color: #ffffff;
            }
        """)
        
        layout.addWidget(self.plot_widget)

    def add_data(self, value: float):
        """添加数据点"""
        if value is None:
            return
            
        current_time = datetime.now().strftime("%H:%M:%S")
        
        self.dewpoint_data.append(value)
        self.time_data.append(current_time)
        
        # 保持数据点数量
        if len(self.dewpoint_data) > self.max_points:
            self.dewpoint_data.pop(0)
            self.time_data.pop(0)
        
        # 更新曲线（使用x轴为索引）
        self.curve.setData(self.dewpoint_data)
        
        # 设置X轴标签为时间
        if len(self.time_data) > 0:
            # 每隔一定数量显示一个标签
            ticks = []
            step = max(1, len(self.time_data) // 5)
            for i in range(0, len(self.time_data), step):
                ticks.append((i, self.time_data[i]))
            self.plot_widget.getAxis('bottom').setTicks([ticks])
        
        # 自动调整Y轴范围
        if len(self.dewpoint_data) > 2:
            y_min = min(self.dewpoint_data) - 10
            y_max = max(self.dewpoint_data) + 10
            y_min = max(-100, y_min)
            y_max = min(50, y_max)
            self.plot_widget.setYRange(y_min, y_max)

    def clear(self):
        """清空数据"""
        self.dewpoint_data.clear()
        self.time_data.clear()
        self.curve.setData([])


class MiniChartWidget(QWidget):
    """迷你曲线图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_points = 50
        self.data = []
        
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#ffffff')
        self.plot_widget.showGrid(x=False, y=True, alpha=0.2)
        self.plot_widget.hideButtons()
        
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#3498db', width=1.5)
        )
        
        self.plot_widget.setYRange(-80, 20)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)

    def add_data(self, value: float):
        """添加数据"""
        if value is None:
            return
            
        self.data.append(value)
        
        if len(self.data) > self.max_points:
            self.data.pop(0)
        
        self.curve.setData(self.data)

    def clear(self):
        """清空"""
        self.data.clear()
        self.curve.setData([])
