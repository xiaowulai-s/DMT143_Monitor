"""
DMT143 露点变送器 - 串口通信客户端
支持 RS485 半双工通信
"""

import serial
import serial.tools.list_ports
import time
import logging
import re
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)


class DMT143Client:
    """DMT143 串口通信客户端"""

    def __init__(self, port: str = 'COM3', baudrate: int = 19200):
        self.port = port
        self.baudrate = baudrate
        self.serial_port: Optional[serial.Serial] = None
        self.log_callback: Optional[Callable] = None
        self.connected = False
        self.rs485_mode = True  # RS485 模式

    def set_log_callback(self, callback: Callable):
        """设置日志回调"""
        self.log_callback = callback

    @staticmethod
    def list_ports() -> List[str]:
        """列出所有可用的串口"""
        ports = serial.tools.list_ports.comports()
        return [p.device for p in ports]

    def log(self, message: str):
        """输出日志"""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def connect(self) -> bool:
        """连接设备"""
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0,
                write_timeout=5.0
            )

            # RS485 半双工控制
            if self.rs485_mode:
                try:
                    self.serial_port.rts = False
                    self.serial_port.dtr = False
                except Exception as e:
                    self.log(f"RS485 控制设置失败: {e}")

            time.sleep(0.2)
            self.connected = True
            self.log(f"已连接到 {self.port} @ {self.baudrate} baud")
            return True

        except Exception as e:
            self.log(f"连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.connected = False
        self.log("已断开连接")

    def reconnect(self) -> bool:
        """重新连接（用于硬件断开后重连）"""
        try:
            # 关闭旧端口
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

            # 重新打开端口
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0,
                write_timeout=5.0
            )

            # RS485 半双工控制
            if self.rs485_mode:
                try:
                    self.serial_port.rts = False
                    self.serial_port.dtr = False
                except Exception as e:
                    self.log(f"RS485 控制设置失败: {e}")

            time.sleep(0.2)
            self.connected = True
            self.log(f"已重新连接到 {self.port}")
            return True

        except Exception as e:
            self.log(f"重连失败: {e}")
            self.connected = False
            return False

    def _rs485_send(self, data: bytes):
        """RS485 发送模式"""
        if self.rs485_mode and self.serial_port:
            try:
                self.serial_port.rts = True
                time.sleep(0.001)
            except:
                pass

    def _rs485_receive(self):
        """RS485 接收模式"""
        if self.rs485_mode and self.serial_port:
            try:
                self.serial_port.rts = False
                time.sleep(0.001)
            except:
                pass

    def send_command(self, cmd: str, wait_time: float = 0.3, clear_buffer: bool = True) -> bytes:
        """发送命令并接收响应

        Args:
            cmd: 命令字符串
            wait_time: 等待响应的时间
            clear_buffer: 是否清空缓冲区（连续读取时设为False避免丢数据）
        """
        if not self.serial_port or not self.connected:
            return b''

        try:
            # 可选：清空缓冲区
            if clear_buffer:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()

            # 发送命令
            cmd_bytes = cmd.encode('ascii') + b'\r'
            self._rs485_send(cmd_bytes)
            self.serial_port.write(cmd_bytes)
            time.sleep(0.001)
            self._rs485_receive()

            # 等待响应
            time.sleep(wait_time)

            # 读取响应
            response = b''
            start = time.time()
            while time.time() - start < 2.0:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    response += data
                    time.sleep(0.05)
                else:
                    if response:
                        break
                    time.sleep(0.1)

            return response

        except Exception as e:
            self.log(f"命令发送失败: {e}")
            return b''

    def get_device_info(self) -> dict:
        """获取设备信息"""
        response = self.send_command('?', wait_time=1.5)
        info = {}

        if response:
            text = response.decode('ascii', errors='replace')
            # 解析关键信息
            for line in text.split('\r\n'):
                if 'Serial number' in line:
                    info['serial'] = line.split(':')[-1].strip()
                elif 'Sensor model' in line:
                    info['model'] = line.split(':')[-1].strip()
                elif 'Serial mode' in line:
                    info['mode'] = line.split(':')[-1].strip()
                elif 'SCI' in line and 'Baud' in line:
                    info['sci'] = line.split(':')[-1].strip()
                elif 'Address' in line:
                    try:
                        info['address'] = int(line.split(':')[-1].strip())
                    except:
                        pass
                elif 'Output interval' in line:
                    info['interval'] = line.split(':')[-1].strip()

        return info

    def set_output_format(self) -> bool:
        """设置输出格式为 Tdf Tdfa H2O"""
        response = self.send_command('FORM TDF TDFA H2O', wait_time=1.0)
        return b'OK' in response

    def query_format(self) -> str:
        """查询当前输出格式"""
        response = self.send_command('FORM', wait_time=1.0)
        return response.decode('ascii', errors='replace').strip()

    def send_single_reading(self) -> Optional[dict]:
        """发送 SEND 命令获取单次读数"""
        response = self.send_command('SEND', wait_time=2.0)

        if response:
            text = response.decode('ascii', errors='replace').strip()

            # 解析带标签格式: Tdf=xx Tdfatm=xx H2O=xxx
            tdf_match = re.search(r'Tdf\s*=\s*([-+]?\d+\.?\d*)', text)
            tdfatm_match = re.search(r'Tdfatm\s*=\s*([-+]?\d+\.?\d*)', text)
            h2o_match = re.search(r'H2O\s*=\s*([-+]?\d+\.?\d*)', text)

            if tdf_match and tdfatm_match and h2o_match:
                return {
                    'raw': text,
                    'dewpoint': float(tdf_match.group(1)),
                    'dewpoint_atm': float(tdfatm_match.group(1)),
                    'h2o_ppm': float(h2o_match.group(1))
                }

            # 解析纯数字格式: xx xx xxx
            numbers = re.findall(r'[-+]?\d+\.?\d*', text)
            values = [float(n) for n in numbers]
            
            # 智能解析
            dewpoint_candidates = [v for v in values if -100 <= v <= 50]
            h2o_candidates = [v for v in values if v > 100]
            
            if len(values) >= 3:
                return {
                    'raw': text,
                    'dewpoint': values[0] if -100 <= values[0] <= 50 else (dewpoint_candidates[0] if dewpoint_candidates else None),
                    'dewpoint_atm': values[1] if -100 <= values[1] <= 50 else None,
                    'h2o_ppm': values[2] if values[2] > 100 else (h2o_candidates[0] if h2o_candidates else None)
                }
            elif len(values) == 2:
                if -100 <= values[0] <= 50:
                    return {'raw': text, 'dewpoint': values[0], 'h2o_ppm': values[1]}
                else:
                    return {'raw': text, 'dewpoint': values[1] if -100 <= values[1] <= 50 else None, 'h2o_ppm': values[0]}
            elif len(values) == 1:
                return {'raw': text, 'dewpoint': None, 'h2o_ppm': values[0]}

        return None

    def start_continuous_reading(self) -> bool:
        """发送 R 命令开始连续输出"""
        # 先清空缓冲区，确保干净的起始状态
        self.serial_port.reset_input_buffer()

        # 发送 R 命令启动连续输出
        response = self.send_command('R', wait_time=0.3, clear_buffer=False)

        # 等待一小段时间让设备开始输出
        time.sleep(0.1)

        # 清空启动命令的响应
        self.serial_port.reset_input_buffer()
        return True

    def stop_continuous_reading(self) -> bool:
        """发送 S 命令停止输出"""
        response = self.send_command('S', wait_time=0.3)
        return bool(response)

    def reset_device(self) -> bool:
        """重置设备状态，确保可以重新开始"""
        # 先发送 S 停止当前输出
        self.send_command('S', wait_time=0.3, clear_buffer=False)
        time.sleep(0.5)  # 等待设备稳定
        # 清空缓冲区
        self.serial_port.reset_input_buffer()
        self.serial_port.reset_output_buffer()
        return True

    def read_data(self, timeout: float = 0.5) -> Optional[dict]:
        """读取数据（从缓冲区）- 按行读取

        Args:
            timeout: 读取超时时间（秒）
        """
        if not self.serial_port or not self.connected:
            return None

        try:
            # 按行读取，设置较短超时避免阻塞
            self.serial_port.timeout = timeout
            line = self.serial_port.readline()

            if not line:
                return None

            # 解码并清理
            text = line.decode('ascii', errors='replace').strip()

            # 跳过空行
            if not text:
                return None

            # 解析带标签格式: Tdf=xx Tdfatm=xx H2O=xxx
            tdf_match = re.search(r'Tdf\s*=\s*([-+]?\d+\.?\d*)', text)
            tdfatm_match = re.search(r'Tdfatm\s*=\s*([-+]?\d+\.?\d*)', text)
            h2o_match = re.search(r'H2O\s*=\s*([-+]?\d+\.?\d*)', text)

            if tdf_match and h2o_match:
                return {
                    'raw': text,
                    'dewpoint': float(tdf_match.group(1)),
                    'dewpoint_atm': float(tdfatm_match.group(1)) if tdfatm_match else None,
                    'h2o_ppm': float(h2o_match.group(1)),
                    'timestamp': time.time()
                }

            # 解析纯数字格式: xx xx xxx
            numbers = re.findall(r'[-+]?\d+\.?\d*', text)
            if numbers:
                result = {
                    'raw': text,
                    'timestamp': time.time()
                }

                # 智能解析：识别哪些是露点，哪些是H2O
                # 露点范围: -100 ~ 50 (°C)
                # H2O范围: > 100 (ppm)
                values = [float(n) for n in numbers]

                # 检查是否有合理的三值组合
                valid_three = False
                if len(values) >= 3:
                    # 检查第一个和第二个值是否像露点(小数值)，第三个是否像H2O(大数值)
                    if values[0] < 100 and values[1] < 100 and values[2] > 1000:
                        result['dewpoint'] = values[0]
                        result['dewpoint_atm'] = values[1]
                        result['h2o_ppm'] = values[2]
                        valid_three = True

                if not valid_three:
                    if len(values) >= 2:
                        if values[0] < 100:
                            result['dewpoint'] = values[0]
                            result['h2o_ppm'] = values[1]
                        else:
                            result['h2o_ppm'] = values[0]
                            result['dewpoint'] = values[1] if len(values) > 1 and values[1] < 100 else None
                    elif len(values) == 1:
                        # 单值需要更多上下文判断，暂时跳过
                        return None

                return result

        except Exception as e:
            self.log(f"数据读取失败: {e}")

        return None

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected and self.serial_port and self.serial_port.is_open
