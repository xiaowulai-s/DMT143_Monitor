# -*- coding: utf-8 -*-
"""
主窗口界面 - 优化版
"""

import os
import json
import time
from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QTextEdit,
    QMenuBar, QMenu, QAction, QStatusBar,
    QFrame, QSplitter, QMessageBox, QFileDialog,
    QScrollArea, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

from core.serial_client import DMT143Client
from core.data_parser import DataHistory
from ui.gauge_widget import GaugeWidget
from ui.chart_widget import ChartWidget, MiniChartWidget
from ui.dialogs import SettingsDialog, AboutDialog


CONFIG_FILE = "dmt143_config.json"


class ReadThread(QThread):
    """读取数据线程"""
    data_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    device_disconnected = pyqtSignal()

    def __init__(self, client: DMT143Client, main_window):
        super().__init__()
        self.client = client
        self.main_window = main_window
        self.running = True
        self.no_data_count = 0
        self.max_no_data = 10  # 连续10次无数据则尝试重连

    def run(self):
        while self.running:
            if self.client.connected:
                data = self.client.read_data()
                if data:
                    self.no_data_count = 0
                    self.data_received.emit(data)
                else:
                    self.no_data_count += 1
                    # 连续多次无数据，可能是硬件断开
                    if self.no_data_count >= self.max_no_data:
                        self.handle_reconnect()
            time.sleep(0.1)

    def handle_reconnect(self):
        """检测到设备断开，通知主窗口处理"""
        self.no_data_count = 0
        self.status_changed.emit("设备已断开，等待重新连接...")
        self.device_disconnected.emit()

    def stop(self):
        self.running = False
        self.wait()


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        
        # 客户端和数据
        self.client = DMT143Client()
        self.data_history = DataHistory(max_points=1000)
        
        # 设置
        self.settings = {
            'alarm': {
                'enabled': False,
                'dewpoint_low': -80,
                'dewpoint_high': 20
            },
            'refresh_interval': 500,
            'show_mini_chart': True,
            'max_history': 1000,
            'rs485_mode': True  # RS485模式
        }
        
        # 线程
        self.read_thread: Optional[ReadThread] = None
        
        # 初始化UI
        self.init_ui()
        self.load_config()
        self.create_menu()
        
        # 定时器
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_display)
        self.refresh_timer.start(self.settings['refresh_interval'])

        # 自动重连检测定时器
        self.auto_reconnect_timer = QTimer()
        self.auto_reconnect_timer.timeout.connect(self.check_auto_reconnect)
        self.auto_reconnect_enabled = False
        self.last_known_port = ""

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("DMT143 露点监控系统 v2.1")
        self.setMinimumSize(1200, 850)
        
        # 设置应用样式
        self.set_style()
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # 标题栏
        self.create_title_bar(main_layout)

        # 连接控制
        self.create_connection_panel(main_layout)

        # 主内容区
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)
        
        # 左侧 - 仪表盘
        left_panel = self.create_gauge_panel()
        content_layout.addWidget(left_panel, 1)
        
        # 右侧 - 图表和日志
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel, 2)
        
        main_layout.addLayout(content_layout)

        # 状态栏
        self.create_status_bar()

    def set_style(self):
        """设置整体样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e8f4fc, stop:1 #d6e9f8);
            }
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 2px solid #4a90d9;
                padding: 5px;
            }
            QMenuBar::item {
                padding: 8px 15px;
                border-radius: 5px;
            }
            QMenuBar::item:selected {
                background-color: #4a90d9;
                color: white;
            }
            QMenu {
                background-color: white;
                border: 1px solid #d0e0f0;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4a90d9;
                color: white;
            }
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #d0e0f0;
                color: #555;
            }
        """)

    def create_title_bar(self, parent_layout):
        """创建标题栏"""
        title_frame = QFrame()
        title_frame.setFixedHeight(60)
        title_frame.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90d9, stop:1 #357abd);
                border-radius: 12px;
            }
        """)
        
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(20, 0, 20, 0)
        
        # 左侧：Logo和标题
        left_info = QVBoxLayout()
        left_info.setSpacing(0)
        
        title_label = QLabel("📊 DMT143 露点监控系统")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setStyleSheet("color: white; background: transparent;")
        left_info.addWidget(title_label)
        
        subtitle = QLabel("Dewpoint Monitoring System")
        subtitle.setFont(QFont("Arial", 9))
        subtitle.setStyleSheet("color: rgba(255,255,255,0.7); background: transparent;")
        left_info.addWidget(subtitle)
        
        title_layout.addLayout(left_info)
        
        title_layout.addStretch()
        
        # 右侧：版本和状态
        right_info = QVBoxLayout()
        right_info.setSpacing(0)
        right_info.setAlignment(Qt.AlignRight)
        
        version = QLabel("Version 1.0")
        version.setFont(QFont("Arial", 9))
        version.setStyleSheet("color: rgba(255,255,255,0.8); background: transparent;")
        right_info.addWidget(version, 0, Qt.AlignRight)
        
        self.status_text = QLabel("🟢 就绪")
        self.status_text.setFont(QFont("Microsoft YaHei", 10))
        self.status_text.setStyleSheet("color: white; background: transparent;")
        right_info.addWidget(self.status_text, 0, Qt.AlignRight)
        
        title_layout.addLayout(right_info)
        
        parent_layout.addWidget(title_frame)

    def create_connection_panel(self, parent_layout):
        """创建连接控制面板"""
        conn_frame = QFrame()
        conn_frame.setFixedHeight(75)
        conn_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #d0e0f0;
            }
        """)
        
        conn_layout = QHBoxLayout(conn_frame)
        conn_layout.setContentsMargins(20, 10, 20, 10)
        conn_layout.setSpacing(15)
        
        # 串口选择
        port_label = QLabel("串口:")
        port_label.setFont(QFont("Microsoft YaHei", 10))
        port_label.setStyleSheet("background: transparent; color: #2c3e50;")
        conn_layout.addWidget(port_label)
        
        self.port_combo = QComboBox()
        self.port_combo.setFixedWidth(130)
        self.port_combo.setFont(QFont("Arial", 9))
        self.port_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
            QComboBox:hover {
                border-color: #4a90d9;
            }
            QComboBox:focus {
                border-color: #4a90d9;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #7f8c8d;
                margin-right: 10px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #4a90d9;
            }
        """)
        self.port_combo.addItems(self.client.list_ports())
        conn_layout.addWidget(self.port_combo)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedWidth(70)
        refresh_btn.setFont(QFont("Microsoft YaHei", 9))
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 10px;
                background-color: #ecf0f1;
                color: #2c3e50;
                border: 1px solid #d0e0f0;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #dfe6e9;
                border-color: #4a90d9;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_ports)
        conn_layout.addWidget(refresh_btn)
        
        conn_layout.addSpacing(20)
        
        # 连接按钮
        self.connect_btn = QPushButton("▶ 连接")
        self.connect_btn.setFixedWidth(90)
        self.connect_btn.setFixedHeight(36)
        self.connect_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.connect_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:1 #2ecc71);
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #219a52, stop:1 #27ae60);
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #ccc;
            }
        """)
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn)
        
        # 断开按钮
        self.disconnect_btn = QPushButton("⏹ 断开")
        self.disconnect_btn.setFixedWidth(90)
        self.disconnect_btn.setFixedHeight(36)
        self.disconnect_btn.setFont(QFont("Microsoft YaHei", 9))
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e74c3c, stop:1 #c0392b);
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #c0392b, stop:1 #a93226);
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #ccc;
            }
        """)
        self.disconnect_btn.clicked.connect(self.disconnect_device)
        conn_layout.addWidget(self.disconnect_btn)
        
        conn_layout.addStretch()
        
        # 设备信息显示
        self.device_info_label = QLabel("📱 设备: --")
        self.device_info_label.setFont(QFont("Microsoft YaHei", 9))
        self.device_info_label.setStyleSheet("""
            color: #7f8c8d; 
            background: transparent;
            padding: 5px 10px;
            border-radius: 6px;
            border: 1px solid #e8e8e8;
        """)
        conn_layout.addWidget(self.device_info_label)
        
        conn_layout.addSpacing(10)
        
        # 当前值显示
        value_frame = QFrame()
        value_frame.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8f9fa, stop:1 #e8f4fc);
                border-radius: 10px;
                border: 1px solid #d0e0f0;
            }
        """)
        value_layout = QHBoxLayout(value_frame)
        value_layout.setContentsMargins(15, 8, 15, 8)
        
        value_title = QLabel("📈 当前露点:")
        value_title.setFont(QFont("Microsoft YaHei", 10))
        value_title.setStyleSheet("color: #7f8c8d; background: transparent;")
        value_layout.addWidget(value_title)
        
        self.current_value_label = QLabel("-- °C")
        self.current_value_label.setFont(QFont("Consolas", 14, QFont.Bold))
        self.current_value_label.setStyleSheet("color: #3498db; background: transparent;")
        value_layout.addWidget(self.current_value_label)
        
        conn_layout.addWidget(value_frame)
        
        parent_layout.addWidget(conn_frame)

    def create_gauge_panel(self) -> QFrame:
        """创建仪表盘面板"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #d0e0f0;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 设备信息区域
        device_info_frame = QFrame()
        device_info_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f7ff;
                border-radius: 8px;
                border: 1px solid #d0e0f0;
            }
        """)
        device_info_layout = QVBoxLayout(device_info_frame)
        device_info_layout.setContentsMargins(12, 10, 12, 10)
        device_info_layout.setSpacing(6)

        device_info_title = QLabel("📱 设备信息")
        device_info_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        device_info_title.setStyleSheet("color: #2c3e50; background: transparent;")
        device_info_layout.addWidget(device_info_title)

        # 设备信息标签
        info_layout = QGridLayout()
        info_layout.setSpacing(8)

        # 型号
        model_label = QLabel("型号:")
        model_label.setFont(QFont("Microsoft YaHei", 9))
        model_label.setStyleSheet("color: #7f8c8d; background: transparent;")
        self.device_model_value = QLabel("--")
        self.device_model_value.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.device_model_value.setStyleSheet("color: #2c3e50; background: transparent;")
        info_layout.addWidget(model_label, 0, 0)
        info_layout.addWidget(self.device_model_value, 0, 1)

        # 序列号
        serial_label = QLabel("序列号:")
        serial_label.setFont(QFont("Microsoft YaHei", 9))
        serial_label.setStyleSheet("color: #7f8c8d; background: transparent;")
        self.device_serial_value = QLabel("--")
        self.device_serial_value.setFont(QFont("Consolas", 9))
        self.device_serial_value.setStyleSheet("color: #2c3e50; background: transparent;")
        info_layout.addWidget(serial_label, 1, 0)
        info_layout.addWidget(self.device_serial_value, 1, 1)

        # 波特率
        baud_label = QLabel("波特率:")
        baud_label.setFont(QFont("Microsoft YaHei", 9))
        baud_label.setStyleSheet("color: #7f8c8d; background: transparent;")
        self.device_baud_value = QLabel("--")
        self.device_baud_value.setFont(QFont("Consolas", 9))
        self.device_baud_value.setStyleSheet("color: #2c3e50; background: transparent;")
        info_layout.addWidget(baud_label, 2, 0)
        info_layout.addWidget(self.device_baud_value, 2, 1)

        # 串口模式
        mode_label = QLabel("模式:")
        mode_label.setFont(QFont("Microsoft YaHei", 9))
        mode_label.setStyleSheet("color: #7f8c8d; background: transparent;")
        self.device_mode_value = QLabel("--")
        self.device_mode_value.setFont(QFont("Consolas", 9))
        self.device_mode_value.setStyleSheet("color: #2c3e50; background: transparent;")
        info_layout.addWidget(mode_label, 3, 0)
        info_layout.addWidget(self.device_mode_value, 3, 1)

        # 地址
        addr_label = QLabel("地址:")
        addr_label.setFont(QFont("Microsoft YaHei", 9))
        addr_label.setStyleSheet("color: #7f8c8d; background: transparent;")
        self.device_addr_value = QLabel("--")
        self.device_addr_value.setFont(QFont("Consolas", 9))
        self.device_addr_value.setStyleSheet("color: #2c3e50; background: transparent;")
        info_layout.addWidget(addr_label, 4, 0)
        info_layout.addWidget(self.device_addr_value, 4, 1)

        # 输出间隔
        interval_label = QLabel("输出间隔:")
        interval_label.setFont(QFont("Microsoft YaHei", 9))
        interval_label.setStyleSheet("color: #7f8c8d; background: transparent;")
        self.device_interval_value = QLabel("--")
        self.device_interval_value.setFont(QFont("Consolas", 9))
        self.device_interval_value.setStyleSheet("color: #2c3e50; background: transparent;")
        info_layout.addWidget(interval_label, 5, 0)
        info_layout.addWidget(self.device_interval_value, 5, 1)

        device_info_layout.addLayout(info_layout)
        layout.addWidget(device_info_frame)

        # 实时数据标题
        panel_title = QLabel("📊 实时数据")
        panel_title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        panel_title.setStyleSheet("color: #2c3e50; background: transparent; padding: 3px;")
        layout.addWidget(panel_title)

        # 仪表盘
        self.dewpoint_gauge = GaugeWidget(
            "露点温度 Tdf", "°C", -100, 20
        )
        layout.addWidget(self.dewpoint_gauge)

        self.dewpoint_atm_gauge = GaugeWidget(
            "标准气压露点 Tdfatm", "°C", -100, 20
        )
        layout.addWidget(self.dewpoint_atm_gauge)

        self.h2o_gauge = GaugeWidget(
            "体积含水量 H2O", "ppm", 0, 1000
        )
        layout.addWidget(self.h2o_gauge)

        return frame

    def create_right_panel(self) -> QFrame:
        """创建右侧面板"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #d0e0f0;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 实时曲线标题
        chart_title = QLabel("📊 实时曲线")
        chart_title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        chart_title.setStyleSheet("color: #2c3e50; background: transparent; padding: 3px;")
        layout.addWidget(chart_title)
        
        # 实时曲线
        self.chart = ChartWidget()
        layout.addWidget(self.chart, 1)
        
        # 日志
        log_frame = QFrame()
        log_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 1px solid #d0e0f0;
            }
        """)
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(10, 10, 10, 10)
        
        log_title = QLabel("📝 系统日志")
        log_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        log_title.setStyleSheet("color: #2c3e50; background: transparent;")
        log_layout.addWidget(log_title)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #ecf0f1;
                border-radius: 8px;
                padding: 8px;
                color: #2c3e50;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_frame)
        
        return frame

    def create_status_bar(self):
        """创建状态栏"""
        # 创建时间标签
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 9))
        self.time_label.setStyleSheet("color: #555; padding-right: 10px;")
        
        # 添加到状态栏（时间在右边）
        self.statusBar().addPermanentWidget(self.time_label)
        self.statusBar().showMessage("💡 就绪，请连接设备开始监控")
        self.statusBar().setFont(QFont("Arial", 9))
        
        # 启动时间更新定时器
        self.update_time()
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
    
    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)

    def create_menu(self):
        """创建菜单"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("📁 文件")
        
        export_action = QAction("📊 导出数据 (CSV)", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("⚙️ 设置")
        
        alarm_action = QAction("🔔 报警设置", self)
        alarm_action.triggered.connect(self.show_settings)
        settings_menu.addAction(alarm_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("❓ 帮助")
        
        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def refresh_ports(self):
        """刷新端口列表"""
        self.port_combo.clear()
        self.port_combo.addItems(self.client.list_ports())
        self.log("已刷新串口列表")

    def toggle_connection(self):
        """切换连接状态"""
        if not self.client.connected:
            self.connect_device()
        else:
            self.disconnect_device()

    def connect_device(self):
        """连接设备"""
        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "⚠️ 提示", "请选择串口")
            return
        
        self.client.port = port
        self.client.set_log_callback(self.log)
        
        # 设置RS485模式
        self.client.rs485_mode = self.settings.get('rs485_mode', True)
        
        if self.client.connect():
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.port_combo.setEnabled(False)

            # 更新状态
            mode_text = "RS485" if self.client.rs485_mode else "RS232"
            self.status_text.setText(f"🟢 已连接 ({mode_text})")
            self.statusBar().showMessage(f"✅ 已连接到: {port} ({mode_text}模式)")

            # 重置设备状态，确保可以重新开始
            self.client.reset_device()
            self.log("设备状态已重置")

            # 获取并显示设备信息
            self.update_device_info()

            # 设置输出格式
            self.client.set_output_format()
            self.log("已设置输出格式: Tdf Tdfa H2O")

            # 启动连续读取
            self.client.start_continuous_reading()
            self.log("已启动连续数据输出")

            # 启动读取线程
            self.read_thread = ReadThread(self.client, self)
            self.read_thread.data_received.connect(self.on_data_received)
            self.read_thread.status_changed.connect(self.on_connection_status)
            self.read_thread.error_occurred.connect(self.on_error)
            self.read_thread.device_disconnected.connect(self.on_device_disconnected)
            self.read_thread.start()

            self.log(f"✅ 已成功连接到 {port} ({mode_text}模式)")
        else:
            QMessageBox.critical(self, "❌ 错误", "连接失败，请检查设备是否正确连接")

    def disconnect_device(self):
        """断开连接"""
        # 先停止数据输出
        self.client.stop_continuous_reading()

        if self.read_thread:
            self.read_thread.stop()
            self.read_thread = None

        self.client.disconnect()

        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.port_combo.setEnabled(True)

        self.status_text.setText("🔴 未连接")
        self.statusBar().showMessage("已断开连接")
        self.device_info_label.setText("📱 设备: --")
        self.device_model_value.setText("--")
        self.device_serial_value.setText("--")
        self.device_baud_value.setText("--")
        self.device_mode_value.setText("--")
        self.device_addr_value.setText("--")
        self.device_interval_value.setText("--")

        self.log("已断开连接")

        # 停止自动重连检测
        self.auto_reconnect_timer.stop()
        self.auto_reconnect_enabled = False

    def check_auto_reconnect(self):
        """检测是否有新设备连接"""
        if not self.auto_reconnect_enabled:
            return

        current_ports = self.client.list_ports()

        # 检查之前监听的端口是否有新设备
        if self.last_known_port and self.last_known_port in current_ports:
            # 端口上有设备，尝试自动连接
            self.auto_reconnect_timer.stop()
            self.auto_reconnect_enabled = False
            self.log(f"检测到设备在 {self.last_known_port}，正在自动连接...")
            self.connect_device()

    def on_device_disconnected(self):
        """设备断开连接处理"""
        # 停止读取线程
        if self.read_thread:
            self.read_thread.stop()
            self.read_thread = None

        # 断开串口连接
        if self.client.connected:
            self.client.disconnect()

        # 更新UI状态
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.status_text.setText("🔴 已断开")
        self.device_info_label.setText("📱 设备: --")
        self.device_model_value.setText("--")
        self.device_serial_value.setText("--")
        self.device_baud_value.setText("--")
        self.device_mode_value.setText("--")
        self.device_addr_value.setText("--")
        self.device_interval_value.setText("--")

        # 启动自动重连检测
        self.start_auto_reconnect()

    def start_auto_reconnect(self):
        """启动自动重连检测"""
        self.last_known_port = self.port_combo.currentText()
        if self.last_known_port:
            self.auto_reconnect_enabled = True
            self.auto_reconnect_timer.start(1000)  # 每秒检测一次
            self.log(f"已开启自动重连检测，监控 {self.last_known_port}")

    def on_data_received(self, data: dict):
        """数据接收"""
        # 解析数据值
        dewpoint = data.get('dewpoint')
        dewpoint_atm = data.get('dewpoint_atm')
        h2o_ppm = data.get('h2o_ppm')

        # 显示解析后的数据（带单位）
        if dewpoint is not None and h2o_ppm is not None:
            dp_str = f"Tdf={dewpoint:.2f} °C" if dewpoint is not None else "Tdf=--"
            dp_atm_str = f"Tdfatm={dewpoint_atm:.2f} °C" if dewpoint_atm is not None else "Tdfatm=--"
            h2o_str = f"H2O={h2o_ppm:.1f} ppm" if h2o_ppm is not None else "H2O=--"
            self.log(f"[解析] {dp_str} | {dp_atm_str} | {h2o_str}")

        self.data_history.add_record(data)
        self.current_data = data
        self.refresh_timer.singleShot(0, self.refresh_display)

    def refresh_display(self):
        """刷新显示"""
        if hasattr(self, 'current_data') and self.current_data:
            data = self.current_data

            # 解析数据值
            dewpoint = data.get('dewpoint')
            dewpoint_atm = data.get('dewpoint_atm')
            h2o_ppm = data.get('h2o_ppm')

            alarm = self.settings.get('alarm', {})
            if alarm.get('enabled'):
                self.dewpoint_gauge.update_value(
                    dewpoint,
                    alarm.get('dewpoint_low'),
                    alarm.get('dewpoint_high')
                )
            else:
                self.dewpoint_gauge.update_value(dewpoint)
            
            self.dewpoint_atm_gauge.update_value(dewpoint_atm)
            self.h2o_gauge.update_value(h2o_ppm)
            
            if dewpoint is not None:
                self.chart.add_data(dewpoint)
                self.current_value_label.setText(f"{dewpoint:.2f} °C")

    def on_connection_status(self, message: str):
        """连接状态变化（用于显示重连状态）"""
        self.statusBar().showMessage(message)
        self.log(message)

    def on_error(self, error: str):
        """错误处理"""
        self.log(f"❌ 错误: {error}")

    def update_device_info(self):
        """更新设备信息（重连后或设备更换时调用）"""
        device_info = self.client.get_device_info()
        if device_info:
            model = device_info.get('model', 'Unknown')
            serial = device_info.get('serial', 'Unknown')
            sci = device_info.get('sci', 'Unknown')
            mode = device_info.get('mode', 'Unknown')
            addr = device_info.get('address', '--')
            interval = device_info.get('interval', 'Unknown')

            # 更新顶部栏设备信息
            self.device_info_label.setText(f"📱 {model} ({serial})")

            # 更新左侧面板设备信息
            self.device_model_value.setText(model)
            self.device_serial_value.setText(serial)
            self.device_baud_value.setText(sci)
            self.device_mode_value.setText(mode)
            self.device_addr_value.setText(str(addr))
            self.device_interval_value.setText(interval)

            self.log(f"📱 设备: {model}, SN: {serial}, {sci}, {mode}, ADDR: {addr}")
        else:
            self.log("⚠️ 无法获取设备信息")

    def log(self, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            self.save_config()
            self.refresh_timer.setInterval(self.settings['refresh_interval'])
            self.data_history.max_points = self.settings['max_history']
            self.log("⚙️ 设置已保存")

    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec_()

    def export_data(self):
        """导出数据"""
        if not self.data_history.records:
            QMessageBox.information(self, "ℹ️ 提示", "没有可导出的数据")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出数据", 
            f"dmt143_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV文件 (*.csv)"
        )
        
        if filename:
            try:
                csv_content = self.data_history.to_csv()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(csv_content)
                QMessageBox.information(self, "✅ 成功", f"数据已导出到:\n{filename}")
                self.log(f"📊 数据已导出: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "❌ 错误", f"导出失败: {e}")

    def load_config(self):
        """加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                self.log("⚙️ 配置已加载")
            except Exception as e:
                self.log(f"加载配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.log(f"保存配置失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        # 停止定时器
        if hasattr(self, 'time_timer'):
            self.time_timer.stop()
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        
        if self.read_thread:
            self.read_thread.stop()
        
        if self.client.connected:
            self.client.disconnect()
        
        self.save_config()
        event.accept()
