# -*- coding: utf-8 -*-
"""
仪表盘组件 - 优化版
"""

from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient, QConicalGradient


class GaugeWidget(QFrame):
    """优化版仪表盘组件"""

    def __init__(self, title: str, unit: str, min_val: float, max_val: float, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.current_value = None
        self._anim_value = 0

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 自适应：设置最小尺寸，允许拉伸
        self.setMinimumHeight(120)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #f0f8ff);
                border-radius: 12px;
                border: 1px solid #d0e0f0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(2)

        # 标题（带图标）
        self.title_label = QLabel(f"🔹 {self.title}")
        self.title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.title_label.setStyleSheet("color: #2c3e50; background: transparent;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # 值显示（带阴影效果）
        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Consolas", 22, QFont.Bold))
        self.value_label.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3498db, stop:1 #2980b9);
            background: transparent;
            padding: 3px;
        """)
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)

        # 单位和进度条
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # 单位
        self.unit_label = QLabel(self.unit)
        self.unit_label.setFont(QFont("Arial", 9))
        self.unit_label.setStyleSheet("color: #7f8c8d; background: transparent;")
        bottom_layout.addWidget(self.unit_label, 0, Qt.AlignLeft)

        # 进度条
        self.progress_bar = QWidget()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QWidget {
                background-color: #ecf0f1;
                border-radius: 4px;
            }
        """)
        progress_layout = QHBoxLayout(self.progress_bar)
        progress_layout.setContentsMargins(1, 1, 1, 1)

        self.progress_fill = QWidget()
        self.progress_fill.setFixedWidth(0)
        self.progress_fill.setFixedHeight(6)
        self.progress_fill.setStyleSheet("""
            QWidget {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_fill)
        bottom_layout.addWidget(self.progress_fill, 1)

        layout.addLayout(bottom_layout)

        # 报警标签
        self.alarm_label = QLabel("")
        self.alarm_label.setFont(QFont("Arial", 8))
        self.alarm_label.setStyleSheet("color: #e74c3c; background: transparent;")
        self.alarm_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.alarm_label)

    def update_value(self, value: float, alarm_low: float = None, alarm_high: float = None):
        """更新数值"""
        if value is None:
            return

        self.current_value = value
        self.value_label.setText(f"{value:.2f}")

        # 计算进度条
        ratio = (value - self.min_val) / (self.max_val - self.min_val)
        ratio = max(0, min(1, ratio))
        bar_width = int(180 * ratio)
        self.progress_fill.setFixedWidth(bar_width)

        # 检查报警
        if alarm_low is not None and alarm_high is not None:
            if value < alarm_low or value > alarm_high:
                self.value_label.setStyleSheet("""
                    color: #e74c3c;
                    background: transparent;
                    padding: 5px;
                """)
                self.progress_fill.setStyleSheet("""
                    QWidget {
                        background-color: #e74c3c;
                        border-radius: 3px;
                    }
                """)
                self.alarm_label.setText("⚠️ 超出范围")
            else:
                self.value_label.setStyleSheet("""
                    color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #27ae60, stop:1 #2ecc71);
                    background: transparent;
                    padding: 5px;
                """)
                self.progress_fill.setStyleSheet("""
                    QWidget {
                        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #3498db, stop:1 #2ecc71);
                        border-radius: 3px;
                    }
                """)
                self.alarm_label.setText("✅ 正常")
        else:
            self.value_label.setStyleSheet("""
                color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                background: transparent;
                padding: 5px;
            """)
            self.progress_fill.setStyleSheet("""
                QWidget {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3498db, stop:1 #2ecc71);
                    border-radius: 3px;
                }
            """)

    def clear(self):
        """清空显示"""
        self.value_label.setText("--")
        self.progress_fill.setFixedWidth(0)
        self.alarm_label.setText("")
        self.current_value = None


class CircularGauge(QWidget):
    """圆形仪表盘组件"""

    def __init__(self, title: str, unit: str, min_val: float, max_val: float, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.value = None
        self._percentage = 0
        self.setMinimumSize(160, 160)
        self.setMaximumSize(180, 180)

        # 动画
        self.anim = QPropertyAnimation(self, b"percentage")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def percentage(self):
        return self._percentage

    @percentage.setter
    def percentage(self, val):
        self._percentage = val
        self.update()

    def set_value(self, value: float, animate: bool = True):
        """设置值"""
        old_val = self.value
        self.value = value

        if value is not None:
            ratio = (value - self.min_val) / (self.max_val - self.min_val)
            ratio = max(0, min(1, ratio))
            target = ratio * 100

            if animate and old_val is not None:
                self.anim.setStartValue(self._percentage)
                self.anim.setEndValue(target)
                self.anim.start()
            else:
                self._percentage = target
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx, cy = w // 2, h // 2
        radius = min(w, h) // 2 - 8
        pen_width = 10

        # 背景圈
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#ecf0f1"), pen_width))
        painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, 0, 360 * 16)

        # 进度弧
        if self.value is not None and self._percentage > 0:
            # 渐变色
            gradient = QConicalGradient(cx, cy, 135)
            gradient.setColorAt(0, QColor("#3498db"))
            gradient.setColorAt(0.5, QColor("#2ecc71"))
            gradient.setColorAt(1, QColor("#3498db"))

            painter.setPen(QPen(gradient, pen_width, Qt.RoundCap))
            painter.setBrush(Qt.NoBrush)

            start_angle = 135
            span_angle = int(self._percentage * 3.6 * 16)

            painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2,
                          start_angle * 16, span_angle)

        # 中心圆
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor("#d0e0f0"), 2))
        center_radius = radius - pen_width - 5
        painter.drawEllipse(cx - center_radius, cy - center_radius, 
                           center_radius * 2, center_radius * 2)

        # 值文本
        painter.setPen(QColor("#2c3e50"))
        value_text = f"{self.value:.1f}" if self.value else "--"
        painter.setFont(QFont("Consolas", 16, QFont.Bold))
        painter.drawText(cx, cy - 5, Qt.AlignCenter, value_text)

        # 单位文本
        painter.setPen(QColor("#7f8c8d"))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(cx, cy + 15, Qt.AlignCenter, self.unit)

        # 标题
        painter.setPen(QColor("#2c3e50"))
        painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        painter.drawText(cx, cy - center_radius + 5, Qt.AlignCenter, self.title)

    def clear(self):
        """清空"""
        self.value = None
        self._percentage = 0
        self.update()
