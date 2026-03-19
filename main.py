# -*- coding: utf-8 -*-
"""
DMT143 露点监控系统 - 启动入口
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui.main_window import MainWindow


def main():
    """主函数"""
    # 创建应用
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 设置应用信息
    app.setApplicationName("DMT143 Monitor")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("QianYiHui")
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
