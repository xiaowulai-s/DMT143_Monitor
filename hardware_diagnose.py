# -*- coding: utf-8 -*-
"""
DMT143 硬件诊断工具 - 深度诊断
"""

import serial
import serial.tools.list_ports
import time
import sys
import io

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def diagnose_hardware(port_name):
    """硬件深度诊断"""
    print("=" * 70)
    print(f"DMT143 硬件深度诊断 - {port_name}")
    print("=" * 70)
    
    # 测试不同波特率
    baudrates = [19200, 9600, 38400, 57600, 115200]
    
    for baudrate in baudrates:
        print(f"\n{'='*70}")
        print(f"测试波特率: {baudrate}")
        print('='*70)
        
        try:
            ser = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2
            )
            print(f"✅ 串口打开成功 @ {baudrate} baud")
            
            # 清空缓冲区
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            time.sleep(0.5)
            
            # 测试1: 发送回车换行,看是否有响应
            print("\n[测试1] 发送空命令 (回车)...")
            ser.write(b'\r')
            time.sleep(1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                print(f"✅ 收到响应: {repr(response)}")
            else:
                print("❌ 无响应")
            
            # 清空缓冲区
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # 测试2: 发送帮助命令
            print("\n[测试2] 发送帮助命令 (?)...")
            ser.write(b'?\r')
            time.sleep(1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                print(f"✅ 收到响应:\n{response}")
            else:
                print("❌ 无响应")
            
            # 清空缓冲区
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # 测试3: 发送停止命令
            print("\n[测试3] 发送停止命令 (S)...")
            for _ in range(3):
                ser.write(b'S\r')
                time.sleep(0.1)
            
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # 测试4: 发送设备信息命令
            print("\n[测试4] 发送设备信息命令 (I)...")
            ser.write(b'I\r')
            time.sleep(1.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                print(f"✅ 收到响应:\n{response}")
            else:
                print("❌ 无响应")
            
            # 清空缓冲区
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # 测试5: 尝试读取模式
            print("\n[测试5] 查询当前模式 (SMODE?)...")
            ser.write(b'SMODE?\r')
            time.sleep(1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                print(f"✅ 收到响应: {response}")
            else:
                print("❌ 无响应")
            
            # 清空缓冲区
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # 测试6: 监听10秒,看是否有自发数据
            print("\n[测试6] 监听自发数据 (10秒)...")
            print("监听中", end='', flush=True)
            
            start_time = time.time()
            received_any = False
            
            while time.time() - start_time < 10:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                    if data.strip():
                        print(f"\n✅ 收到自发数据: {repr(data[:100])}")
                        received_any = True
                print('.', end='', flush=True)
                time.sleep(0.5)
            
            if not received_any:
                print("\n❌ 未检测到自发数据")
            
            ser.close()
            
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        time.sleep(1)
    
    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)


def check_port_info(port_name):
    """检查串口详细信息"""
    print("\n" + "=" * 70)
    print(f"串口详细信息: {port_name}")
    print("=" * 70)
    
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if port.device == port_name:
            print(f"设备: {port.device}")
            print(f"描述: {port.description}")
            print(f"硬件ID: {port.hwid}")
            print(f"制造商: {port.manufacturer if hasattr(port, 'manufacturer') else 'N/A'}")
            print(f"产品: {port.product if hasattr(port, 'product') else 'N/A'}")
            print(f"序列号: {port.serial_number if hasattr(port, 'serial_number') else 'N/A'}")
            print(f"VID:PID: {port.vid:04x}:{port.pid:04x}" if port.vid and port.pid else "N/A")
            return
    
    print("❌ 未找到该串口信息")


def print_troubleshooting():
    """打印故障排查建议"""
    print("\n" + "=" * 70)
    print("故障排查建议")
    print("=" * 70)
    
    print("""
🔴 问题: 设备无响应

可能的原因及解决方案:

1. 【硬件连接问题】
   ✓ 检查 DMT143 是否通电(查看设备指示灯)
   ✓ 检查串口线是否连接正确
   ✓ 确认 TX-RX 是否交叉连接
   ✓ 检查串口线是否损坏

2. 【波特率不匹配】
   ✓ 本工具已测试多种波特率 (9600, 19200, 38400, 57600, 115200)
   ✓ 如果都无响应,可能是其他波特率
   ✓ 查看设备手册确认默认波特率

3. 【设备模式问题】
   ✓ DMT143 可能处于特殊模式(如Modbus模式)
   ✓ 可能需要特定的唤醒命令
   ✓ 可能需要硬件流控制(RTS/DTR)

4. 【驱动问题】
   ✓ 在设备管理器中确认 COM3 是 XR21B1411
   ✓ 尝试重新安装驱动
   ✓ 检查驱动版本

5. 【设备故障】
   ✓ 尝试用其他串口调试工具(如Putty, TeraTerm)
   ✓ 联系设备供应商确认设备状态

6. 【接线问题】
   ✓ RS232 vs RS485 接线方式
   ✓ 是否需要转换器
   ✓ 接线顺序: TX-RX, RX-TX, GND-GND

📝 推荐操作:

1. 检查设备指示灯状态
2. 尝试其他串口调试工具
3. 检查串口线连接
4. 确认设备波特率设置
5. 联系设备技术支持
    """)


def main():
    print("\n" + "=" * 70)
    print("DMT143 硬件深度诊断工具")
    print("=" * 70)
    
    # 列出串口
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ 未找到任何串口设备")
        return
    
    print("\n可用串口:")
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device} - {port.description}")
    
    # 选择串口
    print("\n请选择要诊断的串口:")
    try:
        user_input = input("> ").strip()
        
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(ports):
                port_name = ports[idx].device
            else:
                print("❌ 序号超出范围")
                return
        else:
            port_name = user_input
        
        # 检查串口信息
        check_port_info(port_name)
        
        # 开始诊断
        diagnose_hardware(port_name)
        
        # 打印排查建议
        print_troubleshooting()
        
    except KeyboardInterrupt:
        print("\n\n用户取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
