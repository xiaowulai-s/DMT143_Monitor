# -*- coding: utf-8 -*-
"""
DMT143 串口通信模块
"""

import serial
import serial.tools.list_ports
import time
import re
from typing import Optional, Callable


class DMT143Client:
    """DMT143 露点变送器客户端"""

    def __init__(self, port: str = None, baudrate: int = 19200):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.auto_mode = True
        self.reconnect_attempts = 0
        self.max_reconnect = 3
        self.log_callback: Optional[Callable] = None

    def set_log_callback(self, callback: Callable):
        """设置日志回调"""
        self.log_callback = callback

    def log(self, message: str):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
        print(message)

    @staticmethod
    def list_ports() -> list:
        """列出可用串口"""
        return [p.device for p in list(serial.tools.list_ports.comports())]

    def connect(self, auto_mode: bool = True) -> bool:
        """连接设备"""
        self.auto_mode = auto_mode

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )

            self.log(">>> 打开串口")

            # 清空缓冲区
            for _ in range(3):
                self.serial.reset_input_buffer()
                time.sleep(0.05)

            # 发送停止命令
            for _ in range(3):
                self.serial.write(b'S\r')
                time.sleep(0.2)
                self.serial.reset_input_buffer()

            time.sleep(0.3)

            if auto_mode:
                self.serial.write(b'R\r')
                time.sleep(0.2)
                self.log(">>> 已启动数据输出")

            self.connected = True
            self.reconnect_attempts = 0
            self.log(">>> 连接成功")
            return True

        except Exception as e:
            self.log(f">>> 错误: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.serial and self.serial.is_open:
            try:
                self.serial.write(b'S\r')
                time.sleep(0.1)
                self.serial.close()
            except:
                pass
        self.connected = False
        self.log(">>> 已断开")

    def reconnect(self) -> bool:
        """自动重连"""
        if self.reconnect_attempts >= self.max_reconnect:
            self.log(">>> 重连次数过多，停止重连")
            return False

        self.reconnect_attempts += 1
        self.log(f">>> 尝试重连 ({self.reconnect_attempts}/{self.max_reconnect})")

        self.disconnect()
        time.sleep(1)
        return self.connect(self.auto_mode)

    def read_data(self) -> Optional[dict]:
        """读取数据"""
        if not self.connected or not self.serial:
            return None

        try:
            if self.serial.in_waiting > 0:
                data = self.serial.read(self.serial.in_waiting)
                text = data.decode('ascii', errors='ignore')

                if text.strip():
                    self.log(f"<<< {text.strip()}")
                    return self.parse_data(text)
        except Exception as e:
            self.log(f">>> 错误: {e}")

        return None

    def parse_data(self, text: str) -> Optional[dict]:
        """解析数据"""
        result = {}

        # 解析露点温度 Tdf
        match = re.search(r'Tdf\s*=\s*([-+]?\d+\.?\d*)', text)
        if match:
            result['dewpoint'] = float(match.group(1))

        # 解析标准气压露点 Tdfatm
        match = re.search(r'Tdfatm\s*=\s*([-+]?\d+\.?\d*)', text)
        if match:
            result['dewpoint_atm'] = float(match.group(1))

        # 解析体积含水量 H2O
        match = re.search(r'H2O\s*=\s*(\d+)', text)
        if match:
            result['h2o_ppm'] = float(match.group(1))

        return result if result else None

    def send_command(self, command: str) -> Optional[str]:
        """发送命令"""
        if not self.connected or not self.serial:
            return None

        try:
            # 先停止输出
            for _ in range(2):
                self.serial.reset_input_buffer()
                self.serial.write(b'S\r')
                time.sleep(0.2)

            self.serial.reset_input_buffer()
            time.sleep(0.15)

            # 发送命令
            self.serial.write((command + '\r').encode('ascii'))
            self.log(f">>> {command}")
            time.sleep(0.8)

            # 读取响应
            received = b''
            while self.serial.in_waiting > 0:
                received += self.serial.read(self.serial.in_waiting)
                time.sleep(0.05)

            text = received.decode('ascii', errors='ignore').strip()

            if text:
                self.log(f"<<< {text}")
                return text
            else:
                self.log("<<< 无响应")
                return ""

        except Exception as e:
            self.log(f">>> 错误: {e}")
            return None
