# -*- coding: utf-8 -*-
"""
DMT143 串口通信模块 - 修复版
修复了send_command会停止连续输出的问题
"""

import serial
import serial.tools.list_ports
import time
import re
from typing import Optional, Callable, Dict, Any


class DMT143ClientFixed:
    """DMT143 露点变送器客户端 - 修复版"""

    def __init__(self, port: str = None, baudrate: int = 19200):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.auto_mode = True
        self.reconnect_attempts = 0
        self.max_reconnect = 3
        self.log_callback: Optional[Callable] = None
        
        # 设备信息缓存
        self.device_info: Dict[str, Any] = {}
        self.output_format: str = ""
        
        # 数据缓冲区 - 处理分包问题
        self._data_buffer: str = ""
        
        # ⭐ 新增: 标记是否在连续输出模式
        self._continuous_output_mode = False

    def set_log_callback(self, callback: Callable):
        """设置日志回调"""
        self.log_callback = callback

    def log(self, message: str):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
        print(f"[DMT143] {message}")

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
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )

            self.log(">>> 打开串口成功")

            # 清空缓冲区
            self._clear_buffer()

            # 停止当前输出
            self._send_stop()
            
            # ⭐ 增加等待时间
            time.sleep(0.5)

            # 查询设备信息
            self._query_device_info()
            time.sleep(0.3)

            # 配置输出格式
            self._configure_output_format()
            time.sleep(0.3)

            if auto_mode:
                # 开始连续输出
                self._start_continuous_output()
                self.log(">>> 已启动数据输出")
            else:
                # 轮询模式
                self._set_poll_mode()

            self.connected = True
            self.reconnect_attempts = 0
            self.log(">>> 连接成功")
            return True

        except Exception as e:
            self.log(f">>> 连接错误: {e}")
            return False

    def _clear_buffer(self):
        """清空串口缓冲区"""
        if self.serial and self.serial.is_open:
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            time.sleep(0.1)

    def _send_stop(self):
        """发送停止命令"""
        self._continuous_output_mode = False  # ⭐ 标记停止
        for _ in range(3):
            self.serial.write(b'S\r')
            time.sleep(0.1)
        self._clear_buffer()

    def _query_device_info(self):
        """查询设备信息"""
        self._clear_buffer()
        
        # 查询序列号和型号 - ⭐ 使用 stop_output=True 因为还在初始化阶段
        response = self.send_command('I', wait_response=True, stop_output=True)
        if response:
            self.log(f"<<< 设备信息: {response}")
            # 解析设备信息
            self._parse_device_info(response)
        
        time.sleep(0.2)

    def _parse_device_info(self, text: str):
        """解析设备信息"""
        # 尝试匹配序列号
        match = re.search(r'Serial[\s:]+(\w+)', text, re.IGNORECASE)
        if match:
            self.device_info['serial'] = match.group(1)
        
        # 尝试匹配型号
        match = re.search(r'Model[\s:]+(\w+)', text, re.IGNORECASE)
        if match:
            self.device_info['model'] = match.group(1)

    def _configure_output_format(self):
        """配置输出格式 - 确保输出 Tdf Tdfatm H2O"""
        # ⭐ 使用 stop_output=True 因为还在初始化阶段
        # 查询当前格式
        response = self.send_command('FORM', wait_response=True, stop_output=True)
        self.log(f"<<< 当前格式: {response}")
        
        # 设置需要的格式: Tdf Tdfatm H2O
        response = self.send_command('FORM TDF TDFA H2O', wait_response=True, stop_output=True)
        self.log(f"<<< 格式设置: {response}")
        
        time.sleep(0.2)

    def _start_continuous_output(self):
        """开始连续输出"""
        # 设置为运行模式 - ⭐ 初始化阶段使用 stop_output=True
        self.send_command('SMODE RUN', wait_response=True, stop_output=True)
        
        # 设置输出间隔为1秒
        self.send_command('INTV 1S', wait_response=True, stop_output=True)
        
        # 发送R命令开始输出 - ⭐ 不需要停止输出,直接发送
        self.serial.write(b'R\r')
        self._continuous_output_mode = True  # ⭐ 标记开始连续输出
        time.sleep(0.2)

    def _set_poll_mode(self):
        """设置为轮询模式"""
        self.send_command('SMODE POLL', wait_response=True, stop_output=True)

    def disconnect(self):
        """断开连接"""
        if self.serial and self.serial.is_open:
            try:
                self._send_stop()
                self.serial.close()
            except:
                pass
        self.connected = False
        self._continuous_output_mode = False
        self.log(">>> 已断开连接")

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
        if not self.connected or self.serial is None:
            return None

        try:
            if self.serial.in_waiting > 0:
                data = self.serial.read(self.serial.in_waiting)
                text = data.decode('ascii', errors='ignore')
                
                # ⭐ 添加原始数据日志
                self.log(f"<<< 原始数据({len(text)}字节): {repr(text[:50])}")  # 只显示前50字符
                
                # 添加到缓冲区
                self._data_buffer += text
                
                # ⭐ 支持多种换行符: \r, \n, \r\n
                lines = re.split(r'[\r\n]+', self._data_buffer)
                
                # 保留最后一行（可能是未完成的）
                self._data_buffer = lines[-1] if lines else ""
                
                # 处理已完成的行
                for line in lines[:-1]:
                    line = line.strip()
                    if line and len(line) > 2:
                        self.log(f"<<< 数据行: {line}")
                        result = self.parse_data(line)
                        if result:
                            return result
                        
                # 如果缓冲区有未完成的完整数据，尝试处理
                if self._data_buffer.strip() and len(self._data_buffer.strip()) > 5:
                    stripped = self._data_buffer.strip()
                    numbers = re.findall(r'\b\d+\.?\d*\b', stripped)
                    if len(numbers) >= 3:
                        self.log(f"<<< 缓冲区完整数据: {stripped}")
                        result = self.parse_data(stripped)
                        if result:
                            self._data_buffer = ""
                            return result
                            
        except Exception as e:
            self.log(f">>> 读取错误: {e}")

        return None

    def send_command(self, command: str, wait_response: bool = True, stop_output: bool = True) -> Optional[str]:
        """
        发送命令
        
        ⭐ 修复: 添加 stop_output 参数
        Args:
            command: 命令字符串
            wait_response: 是否等待响应
            stop_output: 是否先停止输出 (默认True,连接后查询时设为False)
        """
        if not self.connected or not self.serial:
            return None

        try:
            # ⭐ 只在需要时停止输出
            if stop_output:
                self._send_stop()
                time.sleep(0.15)

            # 发送命令
            cmd_bytes = (command + '\r').encode('ascii')
            self.serial.write(cmd_bytes)
            self.log(f">>> 发送命令: {command}")
            
            if not wait_response:
                return None
                
            time.sleep(0.5)  # 等待响应

            # 读取响应
            received = b''
            start_time = time.time()
            while time.time() - start_time < 1.0:
                if self.serial.in_waiting > 0:
                    received += self.serial.read(self.serial.in_waiting)
                else:
                    if received:
                        break
                    time.sleep(0.05)

            text = received.decode('ascii', errors='ignore').strip()

            if text:
                self.log(f"<<< 命令响应: {text}")
                return text
            else:
                self.log("<<< 无响应")
                return ""

        except Exception as e:
            self.log(f">>> 命令错误: {e}")
            return None

    def parse_data(self, text: str) -> Optional[dict]:
        """
        解析DMT143数据
        
        支持的格式:
        1. 带标签格式: Tdf= 6.26 'C Tdfatm= 6.45 'C H2O= 9611 ppm
        2. 简化格式: 6.26 9611 6.45 (Tdf H2O Tdfatm) - 根据实际设备输出
        """
        result = {}

        # 清理文本
        text = text.strip()
        
        # 过滤掉明显不完整的数据
        if len(text) < 2:
            return None
        
        # 1. 首先尝试解析带标签格式
        # DMT143输出格式: Tdf= 6.26 'C Tdfatm= 6.45 'C H2O= 9611 ppm
        
        # 解析露点温度 Tdf
        match = re.search(r'Tdf\s*=\s*([-+]?\d+\.?\d*)\s*[\'\u00B0]?[CF]?', text)
        if match:
            try:
                result['dewpoint'] = float(match.group(1))
            except ValueError:
                pass

        # 解析标准气压露点 Tdfatm (也可能是TDFA)
        match = re.search(r'Tdfatm\s*=\s*([-+]?\d+\.?\d*)\s*[\'\u00B0]?[CF]?', text, re.IGNORECASE)
        if not match:
            match = re.search(r'TDFA\s*=\s*([-+]?\d+\.?\d*)\s*[\'\u00B0]?[CF]?', text, re.IGNORECASE)
        if match:
            try:
                result['dewpoint_atm'] = float(match.group(1))
            except ValueError:
                pass

        # 解析体积含水量 H2O
        match = re.search(r'H2O\s*=\s*(\d+\.?\d*)\s*ppm?', text, re.IGNORECASE)
        if match:
            try:
                result['h2o_ppm'] = float(match.group(1))
            except ValueError:
                pass

        # 2. 如果没有标签格式，尝试解析纯数字格式
        # 根据实际设备测试，数据顺序为: Tdf H2O Tdfatm
        # 例如: 19.8 23586.2 20.0
        if not result or len(result) < 2:
            numbers = re.findall(r'\b([-+]?\d+\.?\d*)\b', text)
            
            # 过滤无效数据
            valid_numbers = []
            for num_str in numbers:
                try:
                    val = float(num_str)
                    # 跳过无效值
                    if abs(val) < 0.1 and num_str != '0' and num_str != '0.0':
                        continue
                    valid_numbers.append(val)
                except ValueError:
                    pass
            
            if len(valid_numbers) >= 3:
                # 根据实际数据格式: Tdf H2O Tdfatm
                val1 = valid_numbers[0]  # 可能是Tdf
                val2 = valid_numbers[1]  # 可能是H2O
                val3 = valid_numbers[2]  # 可能是Tdfatm
                
                # 判断哪个是H2O (最大的值)
                if val2 > 100:
                    # 顺序: Tdf H2O Tdfatm
                    result['dewpoint'] = val1
                    result['h2o_ppm'] = val2
                    result['dewpoint_atm'] = val3
                else:
                    # 尝试其他排列
                    if val3 > 100:
                        result['dewpoint'] = val1
                        result['dewpoint_atm'] = val2
                        result['h2o_ppm'] = val3
                        
            elif len(valid_numbers) == 2:
                # 可能是 Tdf H2O 或 Tdf Tdfatm
                val1, val2 = valid_numbers
                if val2 > 100:
                    result['dewpoint'] = val1
                    result['h2o_ppm'] = val2
                else:
                    result['dewpoint'] = val1
                    result['dewpoint_atm'] = val2
            elif len(valid_numbers) == 1:
                # 只有Tdf
                result['dewpoint'] = valid_numbers[0]

        # 3. 物理合理性检查
        if 'dewpoint' in result and 'dewpoint_atm' in result:
            # 在标准大气压下，Tdfatm >= Tdf
            if result['dewpoint'] > result['dewpoint_atm']:
                # 交换值
                temp = result['dewpoint']
                result['dewpoint'] = result['dewpoint_atm']
                result['dewpoint_atm'] = temp

        if result:
            self.log(f">>> 解析结果: {result}")
        return result if result else None

    def query_single_reading(self) -> Optional[dict]:
        """查询单次读数 (轮询模式)"""
        if not self.connected:
            return None
            
        self._clear_buffer()
        self.serial.write(b'SEND\r')
        time.sleep(0.5)
        
        if self.serial.in_waiting > 0:
            data = self.serial.read(self.serial.in_waiting)
            text = data.decode('ascii', errors='ignore').strip()
            if text:
                self.log(f"<<< 读数: {text}")
                return self.parse_data(text)
        return None
