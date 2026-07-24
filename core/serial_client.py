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

            # 等待设备就绪
            time.sleep(0.3)

            # 清空初始缓冲区
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()

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

            # 等待一小段时间让RS485总线稳定
            time.sleep(0.3)

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

            # 等待更长时间让设备完全上电就绪
            time.sleep(0.5)

            # 清空缓冲区
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()

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
        """设置输出格式为 Tdf Tdfa H2O，可选增强 STAT 状态字段"""
        # 基础三参数格式（所有固件版本确认支持）
        response = self.send_command('FORM TDF TDFA H2O', wait_time=1.0)
        ok = b'OK' in response
        if not ok:
            self.log("⚠️ FORM 基础命令失败")
        else:
            self.log("输出格式: Tdf Tdfa H2O")
        return ok

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

            # 按范围分类每个值，不依赖固定顺序
            dewpoint_range = lambda v: -100 <= v <= 50
            small = [v for v in values if dewpoint_range(v)]
            large = [v for v in values if v > 1000]

            if len(values) >= 3:
                if len(small) >= 2 and len(large) >= 1:
                    return {
                        'raw': text,
                        'dewpoint': small[0],
                        'dewpoint_atm': small[1],
                        'h2o_ppm': large[0]
                    }
                elif len(small) == 1 and len(large) >= 1:
                    return {
                        'raw': text,
                        'dewpoint': small[0],
                        'dewpoint_atm': None,
                        'h2o_ppm': large[0]
                    }
                else:
                    return {
                        'raw': text,
                        'dewpoint': values[0] if values[0] <= 100 else None,
                        'dewpoint_atm': values[1] if len(values) > 1 and values[1] <= 100 else None,
                        'h2o_ppm': values[2] if len(values) > 2 and values[2] > 100 else None
                    }
            elif len(values) == 2:
                mid = [v for v in values if 50 < v <= 1000]
                if len(small) == 1 and len(large) == 1:
                    return {'raw': text, 'dewpoint': small[0], 'dewpoint_atm': None, 'h2o_ppm': large[0]}
                elif len(small) == 1 and len(mid) == 1:
                    return {'raw': text, 'dewpoint': small[0], 'dewpoint_atm': None, 'h2o_ppm': mid[0]}
                elif len(small) == 2:
                    return {'raw': text, 'dewpoint': small[0], 'dewpoint_atm': small[1], 'h2o_ppm': None}
                else:
                    if values[0] <= 100:
                        return {'raw': text, 'dewpoint': values[0], 'dewpoint_atm': None, 'h2o_ppm': values[1]}
                    else:
                        return {'raw': text, 'dewpoint': values[1] if values[1] <= 100 else None, 'dewpoint_atm': None, 'h2o_ppm': values[0]}
            elif len(values) == 1:
                return {'raw': text, 'dewpoint': None, 'dewpoint_atm': None, 'h2o_ppm': values[0]}

        return None

    def start_continuous_reading(self) -> bool:
        """发送 R 命令开始连续输出"""
        # 先清空缓冲区，确保干净的起始状态
        self.serial_port.reset_input_buffer()

        # 发送 R 命令启动连续输出
        response = self.send_command('R', wait_time=0.3, clear_buffer=False)

        # 等待一小段时间让设备开始输出
        time.sleep(0.1)

        # 清空启动命令的响应和过渡数据
        self.serial_port.reset_input_buffer()
        return True

    def stop_continuous_reading(self) -> bool:
        """发送 S 命令停止输出"""
        response = self.send_command('S', wait_time=0.3)
        return bool(response)

    def reset_device(self) -> bool:
        """重置设备状态，确保可以重新开始"""
        # 清空可能残留的数据
        self.serial_port.reset_input_buffer()
        self.serial_port.reset_output_buffer()

        # 多次发送 S 命令确保停止输出（RS485总线可能处于不稳定状态）
        for i in range(3):
            self.send_command('S', wait_time=0.2, clear_buffer=False)
            time.sleep(0.2)

        # 等待设备稳定
        time.sleep(0.5)

        # 再次清空缓冲区
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

            # 提取传感器状态（FORM 输出中的最后一个字符）
            sensor_status = self._parse_sensor_status(text)

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
                    'timestamp': time.time(),
                    'sensor_status': sensor_status
                }

            # 解析纯数字格式: xx xx xxx [STATUS]
            # FORM 格式固定为 TDF TDFA H2O，按位置分配最可靠
            numbers = re.findall(r'[-+]?\d+\.?\d*', text)
            if numbers:
                result = {
                    'raw': text,
                    'timestamp': time.time(),
                    'sensor_status': sensor_status
                }

                values = [float(n) for n in numbers]
                n = len(values)

                if n >= 3:
                    # FORM TDF TDFA H2O: 位置 0=Tdf, 1=Tdfa, 2=H2O
                    result['dewpoint'] = values[0]
                    result['dewpoint_atm'] = values[1]
                    result['h2o_ppm'] = values[2]

                elif n == 2:
                    # 两值：先验证合理性再按位置 + 范围分配
                    small = [v for v in values if -100 <= v <= 50]
                    mid = [v for v in values if 50 < v <= 1000]
                    large = [v for v in values if v > 1000]

                    if len(small) == 1 and len(large) == 1:
                        result['dewpoint'] = small[0]
                        result['dewpoint_atm'] = None
                        result['h2o_ppm'] = large[0]
                    elif len(small) == 1 and len(mid) == 1:
                        result['dewpoint'] = small[0]
                        result['dewpoint_atm'] = None
                        result['h2o_ppm'] = mid[0]
                    elif len(small) == 2:
                        result['dewpoint'] = small[0]
                        result['dewpoint_atm'] = small[1]
                        result['h2o_ppm'] = None
                    else:
                        # 兜底：按位置赋值
                        result['dewpoint'] = values[0]
                        result['dewpoint_atm'] = None
                        result['h2o_ppm'] = values[1]

                elif n == 1:
                    # 单值，可能是 H2O 或露点
                    if -100 <= values[0] <= 50:
                        result['dewpoint'] = values[0]
                    else:
                        result['h2o_ppm'] = values[0]
                    result['dewpoint_atm'] = None

                return result

        except Exception as e:
            self.log(f"数据读取失败: {e}")

        return None

    @staticmethod
    def _parse_sensor_status(text: str) -> str:
        """解析传感器状态字符

        DMT143 FORM 命令中 STAT 修饰符会输出一个字符表示状态：
          'N' 或空格 = 正常测量
          'A' = 正在进行自动校准 (AutoCal)
          'H' = 正在进行化学清除 (Purge)
          'h' = 传感器正在加热 (Heating)

        Returns:
            'N'（正常）、'A'（校准）、'H'（清除）、'h'（加热）
        """
        # STAT 字段在输出末尾，是最后一个非空白字符
        text_clean = text.rstrip()
        if not text_clean:
            return 'N'

        last_char = text_clean[-1]
        if last_char in ('A', 'H', 'h'):
            return last_char

        # 尝试从文本末尾提取（可能在制表符或空格后）
        parts = text_clean.split('\t')
        if len(parts) > 1:
            last_part = parts[-1].strip()
            if last_part in ('A', 'H', 'h'):
                return last_part

        return 'N'  # 默认正常状态

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected and self.serial_port and self.serial_port.is_open
