# -*- coding: utf-8 -*-
"""
DMT143 露点监控系统 - 启动入口
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    """主函数"""
    # 创建应用
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 设置应用信息
    app.setApplicationName("DMT143 Monitor")
    app.setApplicationVersion("2.5")
    app.setOrganizationName("QianYiHui")
    
    # 设置应用图标
    app.setWindowIcon(QIcon("icon.ico"))
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
