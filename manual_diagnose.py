# -*- coding: utf-8 -*-
"""
DMT143 官方文档诊断工具
基于Vaisala DMT143用户手册的精确诊断
"""

import serial
import serial.tools.list_ports
import time
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def diagnose_by_manual(port_name):
    """
    根据DMT143官方文档的诊断流程
    
    官方文档指出:
    1. 默认波特率: 19200
    2. 数据格式: 8N1 (8数据位,无校验,1停止位)
    3. 默认模式: 可能是STOP模式,需要唤醒
    4. 初始化序列: S → FORM → R
    """
    
    print("=" * 70)
    print("DMT143 官方文档诊断流程")
    print("=" * 70)
    
    # 尝试不同的配置
    configs = [
        {'baudrate': 19200, 'parity': serial.PARITY_NONE, 'name': '19200 8N1 (默认)'},
        {'baudrate': 9600, 'parity': serial.PARITY_NONE, 'name': '9600 8N1'},
        {'baudrate': 38400, 'parity': serial.PARITY_NONE, 'name': '38400 8N1'},
        {'baudrate': 19200, 'parity': serial.PARITY_EVEN, 'name': '19200 8E1 (偶校验)'},
        {'baudrate': 19200, 'parity': serial.PARITY_ODD, 'name': '19200 8O1 (奇校验)'},
    ]
    
    for config in configs:
        print(f"\n{'='*70}")
        print(f"配置: {config['name']}")
        print('='*70)
        
        try:
            ser = serial.Serial(
                port=port_name,
                baudrate=config['baudrate'],
                bytesize=serial.EIGHTBITS,
                parity=config['parity'],
                stopbits=serial.STOPBITS_ONE,
                timeout=1.5,
                rtscts=False,
                dsrdtr=False
            )
            
            print("✅ 串口已打开")
            
            # 清空缓冲区
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            time.sleep(0.3)
            
            # === 测试1: 尝试发送多个S命令(停止输出) ===
            print("\n[测试1] 发送停止命令 (S) - 3次")
            for i in range(3):
                ser.write(b'S\r')
                time.sleep(0.2)
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                    print(f"  第{i+1}次响应: {repr(response)}")
                else:
                    print(f"  第{i+1}次: 无响应")
            
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # === 测试2: 发送问号命令(帮助) ===
            print("\n[测试2] 发送帮助命令 (?)")
            ser.write(b'?\r')
            time.sleep(1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                print(f"✅ 响应:\n{response}")
            else:
                print("❌ 无响应")
            
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # === 测试3: 查询模式 ===
            print("\n[测试3] 查询当前模式 (SMODE?)")
            ser.write(b'SMODE?\r')
            time.sleep(1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                print(f"✅ 当前模式: {response.strip()}")
                
                # 如果是STOP模式,尝试切换到RUN
                if 'STOP' in response.upper():
                    print("\n⚠️  检测到STOP模式,尝试切换到RUN模式...")
                    ser.write(b'SMODE RUN\r')
                    time.sleep(0.5)
                    
                    if ser.in_waiting > 0:
                        switch_resp = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                        print(f"切换响应: {switch_resp}")
            else:
                print("❌ 无响应")
            
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # === 测试4: 查询设备信息 ===
            print("\n[测试4] 查询设备信息 (I)")
            ser.write(b'I\r')
            time.sleep(1)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                print(f"✅ 设备信息:\n{response}")
                
                if 'Serial' in response or 'Model' in response or 'DMT' in response:
                    print("\n🎉 成功! 设备响应正常!")
                    return True
            else:
                print("❌ 无响应")
            
            ser.reset_input_buffer()
            time.sleep(0.3)
            
            # === 测试5: 尝试设置格式并启动输出 ===
            print("\n[测试5] 设置格式并启动输出")
            
            # 设置格式
            print("  → 设置格式: FORM TDF TDFA H2O")
            ser.write(b'FORM TDF TDFA H2O\r')
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                print(f"  格式设置响应: {response.strip()}")
            
            ser.reset_input_buffer()
            time.sleep(0.2)
            
            # 启动输出
            print("  → 启动输出: R")
            ser.write(b'R\r')
            time.sleep(0.5)
            
            print("  → 监听数据 3秒...")
            for i in range(6):
                time.sleep(0.5)
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                    print(f"  ✅ 收到数据: {repr(data[:100])}")
                    if 'Tdf' in data or 'H2O' in data:
                        print("\n🎉 成功! 设备正在输出数据!")
                        # 发送停止命令
                        for _ in range(3):
                            ser.write(b'S\r')
                            time.sleep(0.1)
                        ser.close()
                        return True
                print(f"  .", end='', flush=True)
            
            print()
            ser.close()
            
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        time.sleep(0.5)
    
    return False


def check_hardware_flow_control(port_name):
    """
    测试硬件流控制
    某些设备需要 RTS/DTR 信号
    """
    print("\n" + "=" * 70)
    print("测试硬件流控制 (RTS/DTR)")
    print("=" * 70)
    
    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=19200,
            timeout=1.5,
            rtscts=True,  # 启用RTS/CTS流控
            dsrdtr=True   # 启用DTR/DSR流控
        )
        
        # 设置控制线
        ser.setRTS(True)
        ser.setDTR(True)
        
        print("✅ RTS 和 DTR 已置高")
        
        time.sleep(0.5)
        
        # 清空缓冲区
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # 发送命令
        print("\n发送命令: I")
        ser.write(b'I\r')
        time.sleep(1)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            print(f"✅ 响应: {response}")
            if 'Serial' in response or 'Model' in response:
                return True
        else:
            print("❌ 无响应")
        
        ser.close()
        
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    return False


def main():
    print("\n" + "=" * 70)
    print("DMT143 官方文档诊断工具")
    print("=" * 70)
    
    # 列出串口
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ 未找到任何串口设备")
        return
    
    print("\n可用串口:")
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device} - {port.description}")
    
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
        
        # 运行诊断
        if diagnose_by_manual(port_name):
            print("\n" + "=" * 70)
            print("✅ 诊断成功!")
            print("现在可以使用主程序: python main.py")
            print("=" * 70)
        else:
            # 尝试硬件流控
            if check_hardware_flow_control(port_name):
                print("\n" + "=" * 70)
                print("✅ 硬件流控诊断成功!")
                print("=" * 70)
            else:
                print("\n" + "=" * 70)
                print("❌ 诊断失败")
                print("=" * 70)
                print("\n可能的原因:")
                print("1. 设备未通电")
                print("2. 接线不正确")
                print("3. 设备故障")
                print("4. 驱动问题")
                print("\n建议:")
                print("1. 检查设备指示灯")
                print("2. 检查接线(RS232需要交叉)")
                print("3. 尝试其他串口调试工具")
                print("4. 联系Vaisala技术支持")
        
    except KeyboardInterrupt:
        print("\n\n用户取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    main()
