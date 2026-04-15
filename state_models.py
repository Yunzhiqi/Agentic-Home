"""
智能家居数字孪生全局状态机模型
使用 Pydantic V2 定义家庭环境的虚拟状态，并在内存中维护
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import datetime


class DeviceType(str, Enum):
    """设备类型枚举"""
    VACUUM = "扫地机"
    LIGHT = "灯光"
    AIR_CONDITIONER = "空调"
    CURTAIN = "窗帘"
    TV = "电视"
    SPEAKER = "音箱"
    SENSOR = "传感器"


class DeviceStatus(str, Enum):
    """设备状态枚举"""
    RUNNING = "运行"
    STANDBY = "待机"
    FAULT = "故障"
    OFFLINE = "离线"


class DeviceState(BaseModel):
    """设备基础状态类"""
    model_config = ConfigDict(use_enum_values=True)
    
    device_id: str = Field(..., description="设备唯一标识符")
    device_type: DeviceType = Field(..., description="设备类型")
    status: DeviceStatus = Field(default=DeviceStatus.STANDBY, description="设备当前状态")
    power_level: int = Field(default=0, ge=0, le=100, description="功率等级 0-100")
    last_update: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    
    # 扩展属性：不同设备类型可能有不同的特殊属性
    extra_attrs: Dict[str, Any] = Field(default_factory=dict, description="设备特有属性")


class RoomState(BaseModel):
    """房间状态类"""
    room_name: str = Field(..., description="房间名称")
    temperature: float = Field(default=25.0, description="当前温度（摄氏度）")
    humidity: float = Field(default=50.0, ge=0, le=100, description="湿度百分比")
    is_occupied: bool = Field(default=False, description="是否有人")
    brightness: int = Field(default=0, ge=0, le=100, description="亮度等级 0-100")
    devices: List[DeviceState] = Field(default_factory=list, description="房间内的设备列表")
    
    def get_device(self, device_id: str) -> Optional[DeviceState]:
        """根据设备ID获取设备"""
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None
    
    def add_device(self, device: DeviceState):
        """添加设备到房间"""
        if not self.get_device(device.device_id):
            self.devices.append(device)
    
    def remove_device(self, device_id: str) -> bool:
        """从房间移除设备"""
        device = self.get_device(device_id)
        if device:
            self.devices.remove(device)
            return True
        return False


class HomeState(BaseModel):
    """家庭全局状态类"""
    rooms: Dict[str, RoomState] = Field(default_factory=dict, description="房间字典，key为房间名")
    active_events: List[str] = Field(default_factory=list, description="当前活跃的事件列表")
    last_user_command: Optional[str] = Field(default=None, description="最后一条用户指令")
    system_mode: str = Field(default="normal", description="系统模式：normal, away, sleep, party")
    
    def get_room(self, room_name: str) -> Optional[RoomState]:
        """获取指定房间"""
        return self.rooms.get(room_name)
    
    def add_room(self, room: RoomState):
        """添加房间"""
        self.rooms[room.room_name] = room
    
    def get_device(self, device_id: str) -> Optional[DeviceState]:
        """全局搜索设备"""
        for room in self.rooms.values():
            device = room.get_device(device_id)
            if device:
                return device
        return None
    
    def add_event(self, event: str):
        """添加事件到活跃事件列表"""
        self.active_events.append(f"[{datetime.now().strftime('%H:%M:%S')}] {event}")
        # 保持最近50条事件
        if len(self.active_events) > 50:
            self.active_events = self.active_events[-50:]
    
    def clear_events(self):
        """清空事件列表"""
        self.active_events.clear()
    
    @classmethod
    def init_mock_home(cls) -> "HomeState":
        """初始化一个包含 mock 数据的家庭状态"""
        # 创建客厅
        living_room = RoomState(
            room_name="客厅",
            temperature=26.0,
            humidity=55.0,
            is_occupied=True,
            brightness=80
        )
        
        # 客厅设备
        living_room.add_device(DeviceState(
            device_id="living_light_001",
            device_type=DeviceType.LIGHT,
            status=DeviceStatus.RUNNING,
            power_level=80,
            extra_attrs={"color": "暖白", "brightness": 80}
        ))
        
        living_room.add_device(DeviceState(
            device_id="living_ac_001",
            device_type=DeviceType.AIR_CONDITIONER,
            status=DeviceStatus.RUNNING,
            power_level=60,
            extra_attrs={"target_temp": 26, "mode": "制冷"}
        ))
        
        living_room.add_device(DeviceState(
            device_id="living_tv_001",
            device_type=DeviceType.TV,
            status=DeviceStatus.STANDBY,
            power_level=0,
            extra_attrs={"channel": 1, "volume": 30}
        ))
        
        living_room.add_device(DeviceState(
            device_id="living_curtain_001",
            device_type=DeviceType.CURTAIN,
            status=DeviceStatus.STANDBY,
            power_level=0,
            extra_attrs={"position": 100}  # 100表示完全打开
        ))
        
        # 创建卧室
        bedroom = RoomState(
            room_name="卧室",
            temperature=24.0,
            humidity=50.0,
            is_occupied=False,
            brightness=0
        )
        
        # 卧室设备
        bedroom.add_device(DeviceState(
            device_id="bedroom_light_001",
            device_type=DeviceType.LIGHT,
            status=DeviceStatus.STANDBY,
            power_level=0,
            extra_attrs={"color": "暖黄", "brightness": 0}
        ))
        
        bedroom.add_device(DeviceState(
            device_id="bedroom_ac_001",
            device_type=DeviceType.AIR_CONDITIONER,
            status=DeviceStatus.STANDBY,
            power_level=0,
            extra_attrs={"target_temp": 24, "mode": "制冷"}
        ))
        
        bedroom.add_device(DeviceState(
            device_id="bedroom_curtain_001",
            device_type=DeviceType.CURTAIN,
            status=DeviceStatus.STANDBY,
            power_level=0,
            extra_attrs={"position": 0}  # 0表示完全关闭
        ))
        
        # 创建厨房
        kitchen = RoomState(
            room_name="厨房",
            temperature=28.0,
            humidity=60.0,
            is_occupied=False,
            brightness=100
        )
        
        kitchen.add_device(DeviceState(
            device_id="kitchen_light_001",
            device_type=DeviceType.LIGHT,
            status=DeviceStatus.RUNNING,
            power_level=100,
            extra_attrs={"color": "冷白", "brightness": 100}
        ))
        
        # 添加扫地机器人（在客厅）
        living_room.add_device(DeviceState(
            device_id="vacuum_robot_001",
            device_type=DeviceType.VACUUM,
            status=DeviceStatus.STANDBY,
            power_level=0,
            extra_attrs={
                "battery": 85,
                "cleaning_mode": "标准",
                "current_location": "客厅"
            }
        ))
        
        # 创建家庭状态
        home = cls()
        home.add_room(living_room)
        home.add_room(bedroom)
        home.add_room(kitchen)
        
        # 添加初始事件
        home.add_event("系统初始化完成")
        home.add_event("客厅检测到有人")
        
        return home


# 全局单例：整个系统共享的家庭状态
_global_home_state: Optional[HomeState] = None


def get_home_state() -> HomeState:
    """获取全局家庭状态单例"""
    global _global_home_state
    if _global_home_state is None:
        _global_home_state = HomeState.init_mock_home()
    return _global_home_state


def reset_home_state():
    """重置全局家庭状态"""
    global _global_home_state
    _global_home_state = HomeState.init_mock_home()


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("智能家居数字孪生状态机测试")
    print("=" * 60)
    
    # 初始化家庭状态
    home = HomeState.init_mock_home()
    
    print(f"\n家庭状态初始化完成，共有 {len(home.rooms)} 个房间")
    
    # 遍历所有房间和设备
    for room_name, room in home.rooms.items():
        print(f"\n【{room_name}】")
        print(f"  温度: {room.temperature}°C, 湿度: {room.humidity}%, 有人: {room.is_occupied}")
        print(f"  设备数量: {len(room.devices)}")
        for device in room.devices:
            print(f"    - {device.device_id} ({device.device_type}): {device.status}, 功率: {device.power_level}%")
    
    # 测试设备查找
    print("\n" + "=" * 60)
    print("测试设备查找功能")
    print("=" * 60)
    device = home.get_device("living_light_001")
    if device:
        print(f"找到设备: {device.device_id}, 类型: {device.device_type}, 状态: {device.status}")
    
    # 测试状态修改
    print("\n" + "=" * 60)
    print("测试状态修改功能")
    print("=" * 60)
    device.status = DeviceStatus.STANDBY
    device.power_level = 0
    print(f"修改后: {device.device_id}, 状态: {device.status}, 功率: {device.power_level}%")
    
    # 测试事件记录
    print("\n" + "=" * 60)
    print("测试事件记录功能")
    print("=" * 60)
    home.add_event("用户关闭客厅灯光")
    home.add_event("检测到卧室温度过高")
    print("活跃事件列表:")
    for event in home.active_events:
        print(f"  {event}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
