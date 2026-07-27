# -*- coding: utf-8 -*-
"""
DMT143 Monitor - 启动入口
"""

import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow


def _resource_path(relative_path):
    """获取资源绝对路径（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


def main():
    """主函数"""
    # HighDPI 属性必须在 QApplication 创建之前设置
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 创建应用
    app = QApplication(sys.argv)

    # 设置应用信息
    app.setApplicationName("DMT143 Monitor")
    app.setApplicationVersion("2.6.3")
    app.setOrganizationName("QianYiHui")

    # 设置应用图标
    app.setWindowIcon(QIcon(_resource_path("icon.ico")))

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
