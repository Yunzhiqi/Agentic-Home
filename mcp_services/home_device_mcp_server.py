"""
智能家居设备 MCP Server
基于 MCP 协议将智能设备包装成独立的服务，提供设备控制和状态查询接口
"""
import os
import sys
import json
from mcp.server.fastmcp import FastMCP

# 确保能够正常导入项目内部模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from state_models import (
    get_home_state, 
    DeviceStatus, 
    DeviceType,
    HomeState
)
from utils.log import logger

# 初始化 MCP Server，命名为 SmartHomeDeviceHub（智能家居设备中枢）
mcp = FastMCP("SmartHomeDeviceHub")

# ===== 工具函数：设备控制逻辑 =====

def _control_light(device_id: str, command: str) -> str:
    """控制灯光设备"""
    home = get_home_state()
    device = home.get_device(device_id)
    
    if not device:
        return f"错误：未找到设备 {device_id}"
    
    if device.device_type != DeviceType.LIGHT:
        return f"错误：设备 {device_id} 不是灯光设备"
    
    if command == "on":
        device.status = DeviceStatus.RUNNING
        device.power_level = device.extra_attrs.get("brightness", 80)
        home.add_event(f"灯光 {device_id} 已打开")
        return f"成功：灯光 {device_id} 已打开，亮度 {device.power_level}%"
    
    elif command == "off":
        device.status = DeviceStatus.STANDBY
        device.power_level = 0
        home.add_event(f"灯光 {device_id} 已关闭")
        return f"成功：灯光 {device_id} 已关闭"
    
    elif command.startswith("brightness:"):
        try:
            brightness = int(command.split(":")[1])
            if 0 <= brightness <= 100:
                device.status = DeviceStatus.RUNNING if brightness > 0 else DeviceStatus.STANDBY
                device.power_level = brightness
                device.extra_attrs["brightness"] = brightness
                home.add_event(f"灯光 {device_id} 亮度调整为 {brightness}%")
                return f"成功：灯光 {device_id} 亮度已调整为 {brightness}%"
            else:
                return "错误：亮度值必须在 0-100 之间"
        except:
            return "错误：亮度命令格式错误，应为 brightness:数值"
    
    else:
        return f"错误：不支持的命令 {command}，支持的命令：on, off, brightness:数值"


def _control_air_conditioner(device_id: str, command: str) -> str:
    """控制空调设备"""
    home = get_home_state()
    device = home.get_device(device_id)
    
    if not device:
        return f"错误：未找到设备 {device_id}"
    
    if device.device_type != DeviceType.AIR_CONDITIONER:
        return f"错误：设备 {device_id} 不是空调设备"
    
    if command == "on":
        device.status = DeviceStatus.RUNNING
        device.power_level = 60
        home.add_event(f"空调 {device_id} 已开启")
        return f"成功：空调 {device_id} 已开启，目标温度 {device.extra_attrs.get('target_temp', 26)}°C"
    
    elif command == "off":
        device.status = DeviceStatus.STANDBY
        device.power_level = 0
        home.add_event(f"空调 {device_id} 已关闭")
        return f"成功：空调 {device_id} 已关闭"
    
    elif command.startswith("temp:"):
        try:
            temp = int(command.split(":")[1])
            if 16 <= temp <= 30:
                device.status = DeviceStatus.RUNNING
                device.power_level = 60
                device.extra_attrs["target_temp"] = temp
                home.add_event(f"空调 {device_id} 温度设置为 {temp}°C")
                return f"成功：空调 {device_id} 温度已设置为 {temp}°C"
            else:
                return "错误：温度值必须在 16-30 之间"
        except:
            return "错误：温度命令格式错误，应为 temp:数值"
    
    elif command.startswith("mode:"):
        mode = command.split(":")[1]
        if mode in ["制冷", "制热", "除湿", "送风"]:
            device.extra_attrs["mode"] = mode
            home.add_event(f"空调 {device_id} 模式切换为 {mode}")
            return f"成功：空调 {device_id} 模式已切换为 {mode}"
        else:
            return "错误：不支持的模式，支持：制冷、制热、除湿、送风"
    
    else:
        return f"错误：不支持的命令 {command}，支持的命令：on, off, temp:数值, mode:模式"


def _control_curtain(device_id: str, command: str) -> str:
    """控制窗帘设备"""
    home = get_home_state()
    device = home.get_device(device_id)
    
    if not device:
        return f"错误：未找到设备 {device_id}"
    
    if device.device_type != DeviceType.CURTAIN:
        return f"错误：设备 {device_id} 不是窗帘设备"
    
    if command == "open":
        device.status = DeviceStatus.RUNNING
        device.power_level = 100
        device.extra_attrs["position"] = 100
        home.add_event(f"窗帘 {device_id} 已打开")
        return f"成功：窗帘 {device_id} 已完全打开"
    
    elif command == "close":
        device.status = DeviceStatus.STANDBY
        device.power_level = 0
        device.extra_attrs["position"] = 0
        home.add_event(f"窗帘 {device_id} 已关闭")
        return f"成功：窗帘 {device_id} 已完全关闭"
    
    elif command.startswith("position:"):
        try:
            position = int(command.split(":")[1])
            if 0 <= position <= 100:
                device.status = DeviceStatus.RUNNING if position > 0 else DeviceStatus.STANDBY
                device.power_level = position
                device.extra_attrs["position"] = position
                home.add_event(f"窗帘 {device_id} 位置调整为 {position}%")
                return f"成功：窗帘 {device_id} 位置已调整为 {position}%"
            else:
                return "错误：位置值必须在 0-100 之间"
        except:
            return "错误：位置命令格式错误，应为 position:数值"
    
    else:
        return f"错误：不支持的命令 {command}，支持的命令：open, close, position:数值"


def _control_vacuum(device_id: str, command: str) -> str:
    """控制扫地机器人"""
    home = get_home_state()
    device = home.get_device(device_id)
    
    if not device:
        return f"错误：未找到设备 {device_id}"
    
    if device.device_type != DeviceType.VACUUM:
        return f"错误：设备 {device_id} 不是扫地机器人"
    
    if command == "start" or command == "clean":
        device.status = DeviceStatus.RUNNING
        device.power_level = 80
        home.add_event(f"扫地机器人 {device_id} 开始清扫")
        return f"成功：扫地机器人 {device_id} 已开始清扫，电量 {device.extra_attrs.get('battery', 100)}%"
    
    elif command == "stop":
        device.status = DeviceStatus.STANDBY
        device.power_level = 0
        home.add_event(f"扫地机器人 {device_id} 停止清扫")
        return f"成功：扫地机器人 {device_id} 已停止清扫"
    
    elif command == "charge":
        device.status = DeviceStatus.STANDBY
        device.power_level = 0
        home.add_event(f"扫地机器人 {device_id} 返回充电")
        return f"成功：扫地机器人 {device_id} 正在返回充电座"
    
    elif command.startswith("mode:"):
        mode = command.split(":")[1]
        if mode in ["标准", "强力", "安静", "拖地"]:
            device.extra_attrs["cleaning_mode"] = mode
            home.add_event(f"扫地机器人 {device_id} 模式切换为 {mode}")
            return f"成功：扫地机器人 {device_id} 清扫模式已切换为 {mode}"
        else:
            return "错误：不支持的模式，支持：标准、强力、安静、拖地"
    
    else:
        return f"错误：不支持的命令 {command}，支持的命令：start, stop, charge, mode:模式"


def _control_tv(device_id: str, command: str) -> str:
    """控制电视设备"""
    home = get_home_state()
    device = home.get_device(device_id)
    
    if not device:
        return f"错误：未找到设备 {device_id}"
    
    if device.device_type != DeviceType.TV:
        return f"错误：设备 {device_id} 不是电视设备"
    
    if command == "on":
        device.status = DeviceStatus.RUNNING
        device.power_level = 100
        home.add_event(f"电视 {device_id} 已打开")
        return f"成功：电视 {device_id} 已打开"
    
    elif command == "off":
        device.status = DeviceStatus.STANDBY
        device.power_level = 0
        home.add_event(f"电视 {device_id} 已关闭")
        return f"成功：电视 {device_id} 已关闭"
    
    else:
        return f"错误：不支持的命令 {command}，支持的命令：on, off"


# ===== MCP 工具定义 =====

@mcp.tool()
def get_home_status() -> str:
    """
    获取当前智能家居的完整状态信息。
    
    返回值：JSON 格式的字符串，包含所有房间、设备状态和活跃事件。
    
    使用场景：
    - 当用户询问"家里现在什么情况"时调用
    - 需要了解整体家居状态时调用
    - 作为其他操作前的状态检查
    """
    logger.info("[MCP Server] 执行工具: get_home_status")
    
    home = get_home_state()
    
    # 构建返回数据
    result = {
        "system_mode": home.system_mode,
        "rooms": {},
        "active_events": home.active_events[-10:],  # 最近10条事件
        "last_user_command": home.last_user_command
    }
    
    for room_name, room in home.rooms.items():
        result["rooms"][room_name] = {
            "temperature": room.temperature,
            "humidity": room.humidity,
            "is_occupied": room.is_occupied,
            "brightness": room.brightness,
            "devices": [
                {
                    "device_id": d.device_id,
                    "device_type": d.device_type,
                    "status": d.status,
                    "power_level": d.power_level,
                    "extra_attrs": d.extra_attrs
                }
                for d in room.devices
            ]
        }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def control_device(device_id: str, command: str) -> str:
    """
    控制指定的智能设备。
    
    参数：
    - device_id: 设备的唯一标识符（如 living_light_001, bedroom_ac_001）
    - command: 控制命令，不同设备支持不同的命令
    
    支持的设备类型和命令：
    
    1. 灯光 (LIGHT):
       - on: 打开灯光
       - off: 关闭灯光
       - brightness:数值: 调整亮度（0-100）
    
    2. 空调 (AIR_CONDITIONER):
       - on: 打开空调
       - off: 关闭空调
       - temp:数值: 设置温度（16-30）
       - mode:模式: 切换模式（制冷/制热/除湿/送风）
    
    3. 窗帘 (CURTAIN):
       - open: 打开窗帘
       - close: 关闭窗帘
       - position:数值: 调整位置（0-100）
    
    4. 扫地机器人 (VACUUM):
       - start/clean: 开始清扫
       - stop: 停止清扫
       - charge: 返回充电
       - mode:模式: 切换清扫模式（标准/强力/安静/拖地）
    
    5. 电视 (TV):
       - on: 打开电视
       - off: 关闭电视
    
    返回值：操作结果的描述字符串
    
    使用场景：
    - 用户说"打开客厅的灯"时，调用 control_device("living_light_001", "on")
    - 用户说"把空调温度调到26度"时，调用 control_device("living_ac_001", "temp:26")
    - 用户说"开始扫地"时，调用 control_device("vacuum_robot_001", "start")
    """
    logger.info(f"[MCP Server] 执行工具: control_device, 参数: device_id={device_id}, command={command}")
    
    home = get_home_state()
    device = home.get_device(device_id)
    
    if not device:
        return f"错误：未找到设备 {device_id}，请检查设备ID是否正确"
    
    # 根据设备类型分发到不同的控制函数
    if device.device_type == DeviceType.LIGHT:
        return _control_light(device_id, command)
    elif device.device_type == DeviceType.AIR_CONDITIONER:
        return _control_air_conditioner(device_id, command)
    elif device.device_type == DeviceType.CURTAIN:
        return _control_curtain(device_id, command)
    elif device.device_type == DeviceType.VACUUM:
        return _control_vacuum(device_id, command)
    elif device.device_type == DeviceType.TV:
        return _control_tv(device_id, command)
    else:
        return f"错误：设备类型 {device.device_type} 暂不支持控制"


@mcp.tool()
def report_sensor_data(room_name: str, event_desc: str) -> str:
    """
    向系统报告传感器检测到的环境事件。
    
    参数：
    - room_name: 房间名称（如 客厅、卧室、厨房）
    - event_desc: 事件描述（如 "检测到有人移动"、"温度过高"、"烟雾报警"）
    
    返回值：事件记录确认信息
    
    使用场景：
    - 传感器检测到环境变化时调用
    - 模拟外部事件输入
    - 触发自动化场景的前置条件
    
    示例：
    - report_sensor_data("客厅", "检测到有人进入")
    - report_sensor_data("卧室", "温度达到30度")
    - report_sensor_data("厨房", "检测到烟雾")
    """
    logger.info(f"[MCP Server] 执行工具: report_sensor_data, 参数: room_name={room_name}, event_desc={event_desc}")
    
    home = get_home_state()
    
    # 检查房间是否存在
    room = home.get_room(room_name)
    if not room:
        return f"警告：房间 {room_name} 不存在，但事件已记录"
    
    # 记录事件
    full_event = f"[{room_name}] {event_desc}"
    home.add_event(full_event)
    
    # 根据事件类型更新房间状态
    if "有人" in event_desc or "进入" in event_desc:
        room.is_occupied = True
    elif "离开" in event_desc or "无人" in event_desc:
        room.is_occupied = False
    
    if "温度" in event_desc:
        # 尝试从描述中提取温度值
        import re
        temp_match = re.search(r'(\d+)度', event_desc)
        if temp_match:
            room.temperature = float(temp_match.group(1))
    
    return f"成功：已记录事件 [{room_name}] {event_desc}"


@mcp.tool()
def query_device_by_room(room_name: str) -> str:
    """
    查询指定房间内的所有设备信息。
    
    参数：
    - room_name: 房间名称（如 客厅、卧室、厨房）
    
    返回值：JSON 格式的字符串，包含该房间的所有设备信息
    
    使用场景：
    - 用户询问"客厅有哪些设备"时调用
    - 需要了解特定房间的设备配置时调用
    """
    logger.info(f"[MCP Server] 执行工具: query_device_by_room, 参数: room_name={room_name}")
    
    home = get_home_state()
    room = home.get_room(room_name)
    
    if not room:
        return json.dumps({"error": f"房间 {room_name} 不存在"}, ensure_ascii=False)
    
    result = {
        "room_name": room_name,
        "temperature": room.temperature,
        "humidity": room.humidity,
        "is_occupied": room.is_occupied,
        "devices": [
            {
                "device_id": d.device_id,
                "device_type": d.device_type,
                "status": d.status,
                "power_level": d.power_level,
                "extra_attrs": d.extra_attrs
            }
            for d in room.devices
        ]
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def set_system_mode(mode: str) -> str:
    """
    设置智能家居系统的全局模式。
    
    参数：
    - mode: 系统模式（normal-正常, away-离家, sleep-睡眠, party-派对）
    
    返回值：模式切换确认信息
    
    使用场景：
    - 用户说"我要出门了"时，调用 set_system_mode("away")
    - 用户说"准备睡觉"时，调用 set_system_mode("sleep")
    - 用户说"开派对模式"时，调用 set_system_mode("party")
    
    不同模式的效果：
    - normal: 正常模式，设备按需运行
    - away: 离家模式，关闭大部分设备，启用安防
    - sleep: 睡眠模式，降低灯光亮度，调整空调温度
    - party: 派对模式，增强灯光效果，调整音响
    """
    logger.info(f"[MCP Server] 执行工具: set_system_mode, 参数: mode={mode}")
    
    home = get_home_state()
    
    valid_modes = ["normal", "away", "sleep", "party"]
    if mode not in valid_modes:
        return f"错误：不支持的模式 {mode}，支持的模式：{', '.join(valid_modes)}"
    
    old_mode = home.system_mode
    home.system_mode = mode
    home.add_event(f"系统模式从 {old_mode} 切换为 {mode}")
    
    return f"成功：系统模式已切换为 {mode}"


if __name__ == "__main__":
    # 启动 stdio 通信模式的服务
    logger.info("[MCP Server] 智能家居设备 MCP Server 启动中...")
    mcp.run()
