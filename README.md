# DMT143 Monitor

Vaisala DRYCAP 露点变送器 DMT143 专用监控软件。

## 项目结构

```
DMT143_Monitor/
├── main.py                         # 程序入口
├── requirements.txt                # 依赖列表
├── dmt143_config.json              # 配置文件
├── icon.ico                        # 应用图标
├── DMT143_Monitor_v2.6.3.spec      # PyInstaller 打包配置
├── DMT143 User's Guide in Chinese M211435ZH.pdf  # DMT143 用户手册
├── commands.md                     # 设备命令参考
├── core/                           # 核心模块
│   ├── serial_client.py            # 串口通信客户端
│   └── data_parser.py              # 数据解析模块
├── ui/                             # UI 模块
│   ├── main_window.py              # 主窗口
│   ├── gauge_widget.py             # 仪表盘 + 渐变进度条
│   ├── chart_widget.py             # 实时曲线图
│   └── dialogs.py                  # 关于 / 日志查看对话框
├── dist/                           # 打包发布
│   └── DMT143_Monitor_v2.6.3.exe
├── logs/                           # 运行日志
└── archive/                        # 历史版本归档
```

## 功能特性

| 功能 | 说明 |
|------|------|
| 实时数据 | Tdf（露点温度）、Tdfatm（标准气压露点）、H2O（体积含水量） |
| 渐变进度条 | 露点温度：红→黄→青→蓝（暖→冷）；H2O：浅蓝→深蓝 |
| 弹性仪表盘 | 窗口缩放自适应，支持 1366×768 ~ 1920×1080+ |
| 实时曲线 | 三参数趋势曲线 |
| RS485 / RS232 | 自动适配工业级半双工通信 |
| 自动重连 | 设备断开后 ~10 秒自动检测重连 |
| 连接验证 | 严格验证设备信息 + FORM 命令后显示连接状态 |
| 传感器状态 | STAT 字段监测校准中/清除中/正常 |
| 系统日志 | 实时日志 + 断开自动保存 |
| 历史日志 | Ctrl+L 查看器，多选删除 |

## 运行方式

### 直接运行
```
双击 dist/DMT143_Monitor_v2.6.3.exe
```

### 源码运行
```bash
pip install -r requirements.txt
python main.py
```

## 快捷操作

| 操作 | 快捷键 |
|------|--------|
| 查看历史日志 | Ctrl + L |
| 刷新串口 | Ctrl + R |
| 退出程序 | Ctrl + Q |

## 版本历史

### v2.6.3 (2026-07-24)
- 露点量程修正：-80 ~ +20 °C（DRYCAP 180D 规格留余量）
- H2O 量程：0 ~ 30000 ppm
- 渐变热力条：露点红→黄→青→蓝，H2O 浅蓝→深蓝
- 连接严格验证：设备信息 + FORM 失败时显示异常
- 恢复 STAT 传感器状态监测
- 单位与数值同行显示，去除面板多余外框
- 全局字体缩小 1-2pt，界面更紧凑
- 弹性仪表盘：`setFixedHeight` → `setMinimumHeight`，随窗口缩放
- 断线检测 30s → 8s，重连冷却已移除
- 设备信息面板紧凑化：6 行竖排 → 2 行横排
- 最小窗口 1024×620，适配 1366×768 笔记本
- 修复 HighDPI 属性顺序（`QApplication.setAttribute` 在实例化前）

### v2.6.1 (2026-07-24)
- Qt 布局双重 parent 闪退修复
- 工作线程 GUI 操作安全修复
- H2O 低 ppm 值（≤1000）解析修复
- 图表批量渲染、NaN/Inf 过滤
- ReadThread / refresh_display 异常保护

### v2.5 (2026-03-20)
- 移除报警设置，简化界面
- 历史日志多选/删除
- 品牌标识，自定义图标

### v2.0 ~ v2.4 (2026-03)
- 设备信息显示、自动重连、历史日志查看器
- RS485 稳定性优化，数据解析方式改进

---

**Power By QianYiHui**
