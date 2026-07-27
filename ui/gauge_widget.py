# -*- coding: utf-8 -*-
"""
仪表盘组件 — 含温度热力渐变条
"""

import math
from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient, QConicalGradient


# ── 预定义配色方案 ──────────────────────────────────────────────

# 露点温度渐变: 红 → 黄 → 青 → 蓝 (暖色在左，冷色在右)
DEWPOINT_STOPS = [
    (0.00, QColor("#e74c3c")),   # 红  — 暖色端 (-80°C)
    (0.33, QColor("#f1c40f")),   # 黄
    (0.66, QColor("#00bcd4")),   # 青
    (1.00, QColor("#3498db")),   # 蓝  — 冷色端 (+20°C)
]

# 含水量渐变: 浅蓝 → 深蓝 (低浓度 → 高浓度)
H2O_STOPS = [
    (0.00, QColor("#b3d9ff")),   # 极浅蓝
    (0.40, QColor("#5b9bd5")),   # 中蓝
    (1.00, QColor("#1a3a5c")),   # 深蓝
]

# ── 自定义渐变进度条 ──────────────────────────────────────────

class GradientBar(QWidget):
    """多色渐变进度条 — 用 QPainter 绘制，回避 stylesheet 局限"""

    def __init__(self, color_stops: list, full_width: int = 180, height: int = 6,
                 background: str = "#ecf0f1", parent=None):
        super().__init__(parent)
        self.color_stops = color_stops          # [(position, QColor), ...]
        self.full_width = full_width            # 满量程宽度 (px)
        self.background = QColor(background)    # 底色
        self._ratio = 0.0

        self.setFixedHeight(height + 2)
        self.setMinimumWidth(1)

    def set_ratio(self, ratio: float):
        """设置当前占比 0~1，触发重绘"""
        self._ratio = max(0.0, min(1.0, ratio))
        self.update()

    def set_color_stops(self, stops: list):
        """运行时更换颜色方案"""
        self.color_stops = stops
        self.update()

    def set_full_width(self, width: int):
        """运行时调整满量程宽度"""
        self.full_width = width
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bar_h = self.height() - 2   # 留 1px 上下边距
        bar_y = 1
        bar_w = self.width()

        # 背景轨道
        painter.setBrush(QBrush(self.background))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, bar_y, bar_w, bar_h, bar_h // 2, bar_h // 2)

        if self._ratio <= 0:
            return

        fill_w = int(bar_w * self._ratio)
        if fill_w < 2:
            return

        # 渐变填充 — 坐标固定在全宽上
        gradient = QLinearGradient(0, 0, self.full_width, 0)
        for pos, color in self.color_stops:
            gradient.setColorAt(pos, color)

        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, bar_y, fill_w, bar_h, bar_h // 2, bar_h // 2)
        painter.end()


# ── 仪表盘主组件 ────────────────────────────────────────────────

class GaugeWidget(QFrame):
    """实时数据仪表盘（量程占比 + 渐变热力条）"""

    def __init__(self, title: str, unit: str, min_val: float, max_val: float,
                 color_stops: list = None, full_bar_width: int = 180,
                 alt_max_val: float = None, alt_stops: list = None,
                 switch_up: float = None, switch_down: float = None,
                 parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.full_bar_width = full_bar_width
        self.current_value = None

        # 自动量程切换
        self.alt_max_val = alt_max_val      # 备用量程上限（宽量程）
        self.alt_stops = alt_stops          # 备用量程配色
        self.switch_up = switch_up          # 超过此值切宽量程
        self.switch_down = switch_down      # 低于此值切回精密量程
        self._using_alt = False             # 当前是否在使用宽量程
        self._primary_max = max_val         # 记住精密量程上限
        self._primary_stops = list(color_stops or DEWPOINT_STOPS)

        self.setup_ui(color_stops or DEWPOINT_STOPS)

    # ── 解析值专用的便捷方法 ──
    @classmethod
    def _sanitize_value(cls, value):
        """安全转换为有限浮点数，否则返回 None"""
        if value is None:
            return None
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        return v if math.isfinite(v) else None

    # ── UI 构建 ──

    def setup_ui(self, stops: list):
        self.setMinimumHeight(75)  # 弹性高度，窗口缩放时自适应
        self.setMinimumWidth(200)
        self.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #f0f8ff);
                border-radius: 12px;
                border: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(1)

        # 标题
        self.title_label = QLabel(f"🔹 {self.title}")
        self.title_label.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        self.title_label.setStyleSheet("color: #2c3e50; background: transparent;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # 数值
        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Consolas", 16, QFont.Bold))
        self.value_label.setStyleSheet("""
            color: #2c3e50; background: transparent; padding: 3px;
        """)
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)

        # 底部：渐变条
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(0)

        # 单位已合并到数值同一行，此处仅保留占位以防自动量程使用
        self.unit_label = QLabel("")
        self.unit_label.hide()

        # 轨道容器
        track = QWidget()
        track.setFixedHeight(8)
        track.setStyleSheet("background-color: #ecf0f1; border-radius: 4px;")

        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(1, 1, 1, 1)

        self.gradient_bar = GradientBar(stops, full_width=self.full_bar_width, parent=track)
        track_layout.addWidget(self.gradient_bar)

        bottom_layout.addWidget(track, 1)
        layout.addLayout(bottom_layout)

        # 报警标签
        self.alarm_label = QLabel("")
        self.alarm_label.setFont(QFont("Arial", 7))
        self.alarm_label.setStyleSheet("color: #e74c3c; background: transparent;")
        self.alarm_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.alarm_label)

    # ── 数据更新 ──

    def update_value(self, value: float, alarm_low: float = None, alarm_high: float = None):
        value = self._sanitize_value(value)
        if value is None:
            return

        self.current_value = value
        self.value_label.setText(f"{value:.2f} {self.unit}")

        # ── 自动量程切换 ──
        if self.alt_max_val is not None:
            if not self._using_alt and value > (self.switch_up or self.max_val):
                self._switch_to_alt()
            elif self._using_alt and value < (self.switch_down or self.alt_max_val * 0.5):
                self._switch_to_primary()
            # 切量程后重新计算 ratio

        # 计算占比较
        if self.max_val == self.min_val:
            ratio = 0
        else:
            ratio = (value - self.min_val) / (self.max_val - self.min_val)
        ratio = max(0.0, min(1.0, ratio))

        self.gradient_bar.set_ratio(ratio)

        # 报警状态
        if alarm_low is not None and alarm_high is not None:
            if value < alarm_low or value > alarm_high:
                self.value_label.setStyleSheet("color: #e74c3c; background: transparent; padding: 5px;")
                self.alarm_label.setText("⚠️ 超出范围")
            else:
                self.value_label.setStyleSheet("color: #27ae60; background: transparent; padding: 5px;")
                self.alarm_label.setText("✅ 正常")
        else:
            self.value_label.setStyleSheet("color: #2c3e50; background: transparent; padding: 5px;")

    # ── 量程切换 ──

    def _switch_to_alt(self):
        """切换到宽量程"""
        if self._using_alt:
            return
        self._using_alt = True
        self._primary_max = self.max_val
        self.max_val = self.alt_max_val
        self.gradient_bar.set_color_stops(self.alt_stops)
        self.unit_label.setText(f"{self.unit} 宽")

    def _switch_to_primary(self):
        """切回精密量程"""
        if not self._using_alt:
            return
        self._using_alt = False
        self.max_val = self._primary_max
        self.gradient_bar.set_color_stops(self._primary_stops)
        self.unit_label.setText(self.unit)

    # ── 运行时调整 ──

    def set_range(self, min_val: float, max_val: float):
        """动态更新量程"""
        self.min_val = min_val
        self.max_val = max_val

    def set_color_stops(self, stops: list):
        """动态更换渐变方案"""
        self.gradient_bar.set_color_stops(stops)

    def set_bar_width(self, width: int):
        """动态调整满条宽度"""
        self.full_bar_width = width
        self.gradient_bar.set_full_width(width)

    def clear(self):
        self.value_label.setText("--")
        self.gradient_bar.set_ratio(0)
        self.alarm_label.setText("")
        self.current_value = None


# ── 圆形仪表盘（保留，未改动） ──────────────────────────────────

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

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#ecf0f1"), pen_width))
        painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, 0, 360 * 16)

        if self.value is not None and self._percentage > 0:
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

        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor("#d0e0f0"), 2))
        center_radius = radius - pen_width - 5
        painter.drawEllipse(cx - center_radius, cy - center_radius,
                           center_radius * 2, center_radius * 2)

        painter.setPen(QColor("#2c3e50"))
        value_text = f"{self.value:.1f}" if self.value else "--"
        painter.setFont(QFont("Consolas", 16, QFont.Bold))
        painter.drawText(cx, cy - 5, Qt.AlignCenter, value_text)

        painter.setPen(QColor("#7f8c8d"))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(cx, cy + 15, Qt.AlignCenter, self.unit)

        painter.setPen(QColor("#2c3e50"))
        painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        painter.drawText(cx, cy - center_radius + 5, Qt.AlignCenter, self.title)

    def clear(self):
        self.value = None
        self._percentage = 0
        self.update()
