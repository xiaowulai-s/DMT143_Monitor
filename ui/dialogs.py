# -*- coding: utf-8 -*-
"""
设置对话框组件
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QSpinBox, QCheckBox, QPushButton,
    QGroupBox, QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.current_settings = current_settings
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumWidth(350)
        
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 报警设置
        alarm_group = QGroupBox("报警设置")
        alarm_layout = QFormLayout()
        
        self.alarm_enabled = QCheckBox("启用报警")
        self.alarm_enabled.setToolTip("当测量值超出范围时显示警告")
        alarm_layout.addRow("", self.alarm_enabled)
        
        self.alarm_low = QSpinBox()
        self.alarm_low.setRange(-100, 100)
        self.alarm_low.setSuffix(" °C")
        self.alarm_low.setToolTip("最低报警阈值")
        alarm_layout.addRow("下限:", self.alarm_low)
        
        self.alarm_high = QSpinBox()
        self.alarm_high.setRange(-100, 100)
        self.alarm_high.setSuffix(" °C")
        self.alarm_high.setToolTip("最高报警阈值")
        alarm_layout.addRow("上限:", self.alarm_high)
        
        alarm_group.setLayout(alarm_layout)
        layout.addWidget(alarm_group)

        # 刷新设置
        refresh_group = QGroupBox("刷新设置")
        refresh_layout = QFormLayout()
        
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(100, 5000)
        self.refresh_interval.setSingleStep(100)
        self.refresh_interval.setSuffix(" ms")
        self.refresh_interval.setToolTip("数据刷新间隔 (100-5000毫秒)")
        refresh_layout.addRow("刷新间隔:", self.refresh_interval)
        
        refresh_group.setLayout(refresh_layout)
        layout.addWidget(refresh_group)

        # 显示设置
        display_group = QGroupBox("显示设置")
        display_layout = QFormLayout()
        
        self.show_mini_chart = QCheckBox("显示迷你曲线")
        self.show_mini_chart.setToolTip("在数据面板显示迷你趋势图")
        display_layout.addRow("", self.show_mini_chart)
        
        self.max_history = QSpinBox()
        self.max_history.setRange(100, 10000)
        self.max_history.setSingleStep(100)
        self.max_history.setToolTip("历史数据保存最大条数")
        display_layout.addRow("历史记录:", self.max_history)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # 样式
        self.setStyleSheet("""
            QDialog {
                background-color: #e6f3ff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a90d9;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
            QLabel {
                color: #2c3e50;
            }
            QSpinBox, QLineEdit {
                padding: 5px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QSpinBox:focus, QLineEdit:focus {
                border: 2px solid #3498db;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QPushButton {
                padding: 8px 20px;
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2c6aa8;
            }
        """)

    def load_settings(self):
        """加载当前设置"""
        alarm = self.current_settings.get('alarm', {})
        self.alarm_enabled.setChecked(alarm.get('enabled', False))
        self.alarm_low.setValue(alarm.get('dewpoint_low', -80))
        self.alarm_high.setValue(alarm.get('dewpoint_high', 20))
        
        self.refresh_interval.setValue(self.current_settings.get('refresh_interval', 500))
        self.show_mini_chart.setChecked(self.current_settings.get('show_mini_chart', True))
        self.max_history.setValue(self.current_settings.get('max_history', 1000))

    def get_settings(self) -> dict:
        """获取设置"""
        return {
            'alarm': {
                'enabled': self.alarm_enabled.isChecked(),
                'dewpoint_low': self.alarm_low.value(),
                'dewpoint_high': self.alarm_high.value()
            },
            'refresh_interval': self.refresh_interval.value(),
            'show_mini_chart': self.show_mini_chart.isChecked(),
            'max_history': self.max_history.value()
        }


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setModal(True)
        self.setFixedSize(400, 250)
        
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 标题
        title = QLabel("DMT143 露点监控系统")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        # 版本
        version = QLabel("Version 2.0 (PyQt5)")
        version.setFont(QFont("Arial", 11))
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(version)

        # 说明
        info = QLabel(
            "基于 PyQt5 构建的现代化监控系统\n"
            "支持实时数据采集、曲线显示、报警提醒等功能\n\n"
            "硬件: DMT143 露点变送器\n"
            "通信: RS485 / 串口"
        )
        info.setFont(QFont("Arial", 10))
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("color: #34495e; line-height: 1.6;")
        layout.addWidget(info)

        # 版权
        copyright = QLabel("Power By QianYiHui")
        copyright.setFont(QFont("Arial", 9))
        copyright.setAlignment(Qt.AlignCenter)
        copyright.setStyleSheet("color: #95a5a6;")
        layout.addWidget(copyright)

        # 关闭按钮
        btn = QPushButton("关闭")
        btn.setFixedWidth(100)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        self.setStyleSheet("""
            QDialog {
                background-color: #e6f3ff;
            }
            QPushButton {
                padding: 8px 20px;
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
