"""
测试 MCP Server 的简单客户端脚本
不接入 LLM，直接通过 MCP 协议调用工具，验证设备控制功能
"""
import asyncio
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def test_mcp_server():
    """测试 MCP Server 的基本功能"""
    print("=" * 60)
    print("智能家居 MCP Server 测试")
    print("=" * 60)
    
    # 启动 MCP Server
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_services/home_device_mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化会话
            await session.initialize()
            
            print("\n1. 获取可用工具列表")
            print("-" * 60)
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description[:50]}...")
            
            print("\n2. 测试获取家居状态")
            print("-" * 60)
            result = await session.call_tool("get_home_status", {})
            print(result.content[0].text[:500] + "...")
            
            print("\n3. 测试控制设备：打开客厅灯光")
            print("-" * 60)
            result = await session.call_tool("control_device", {
                "device_id": "living_light_001",
                "command": "on"
            })
            print(f"  结果: {result.content[0].text}")
            
            print("\n4. 测试控制设备：调整灯光亮度到50%")
            print("-" * 60)
            result = await session.call_tool("control_device", {
                "device_id": "living_light_001",
                "command": "brightness:50"
            })
            print(f"  结果: {result.content[0].text}")
            
            print("\n5. 测试报告传感器数据")
            print("-" * 60)
            result = await session.call_tool("report_sensor_data", {
                "room_name": "客厅",
                "event_desc": "检测到有人移动"
            })
            print(f"  结果: {result.content[0].text}")
            
            print("\n6. 测试查询房间设备")
            print("-" * 60)
            result = await session.call_tool("query_device_by_room", {
                "room_name": "客厅"
            })
            print(f"  结果: {result.content[0].text[:300]}...")
            
            print("\n7. 测试设置系统模式")
            print("-" * 60)
            result = await session.call_tool("set_system_mode", {
                "mode": "sleep"
            })
            print(f"  结果: {result.content[0].text}")
            
            print("\n8. 再次获取家居状态，验证状态变化")
            print("-" * 60)
            result = await session.call_tool("get_home_status", {})
            import json
            status = json.loads(result.content[0].text)
            print(f"  系统模式: {status['system_mode']}")
            print(f"  最近事件: {status['active_events'][-3:]}")
            
            print("\n" + "=" * 60)
            print("测试完成！")
            print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
