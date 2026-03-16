# DMT143 Monitor - 露点变送器监控系统

## 项目结构

```
DMT143_Monitor/
├── main.py                 # 程序入口
├── requirements.txt        # 依赖列表
├── core/
│   ├── __init__.py
│   ├── serial_client.py    # 串口通信模块
│   └── data_parser.py      # 数据解析模块
├── ui/
│   ├── __init__.py
│   ├── main_window.py      # 主窗口
│   ├── gauge_widget.py     # 仪表盘组件
│   ├── chart_widget.py     # 曲线图表组件
│   └── settings_dialog.py # 设置对话框
└── resources/
    └── __init__.py
```

## 功能特性

- 仪表盘显示实时数据
- 历史数据曲线图表
- 报警功能
- 自动重连
- 数据导出CSV
- 刷新间隔设置
- 浅蓝色专业主题

## 运行方式

```bash
pip install -r requirements.txt
python main.py
```

## 快捷键

- Ctrl+S: 保存数据
- Ctrl+R: 刷新串口
- Ctrl+Q: 退出程序
