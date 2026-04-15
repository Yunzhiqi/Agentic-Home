"""
智能家居系统集成测试脚本
测试所有四个阶段的功能
"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_phase_1():
    """测试阶段一：数字孪生状态机"""
    print("=" * 60)
    print("阶段一：测试数字孪生状态机")
    print("=" * 60)
    
    from state_models import HomeState, DeviceType, DeviceStatus
    
    # 初始化家庭状态
    home = HomeState.init_mock_home()
    
    print(f"[OK] 家庭状态初始化成功，共有 {len(home.rooms)} 个房间")
    
    # 测试设备查找
    device = home.get_device("living_light_001")
    assert device is not None, "设备查找失败"
    print(f"[OK] 设备查找成功: {device.device_id}")
    
    # 测试状态修改
    device.status = DeviceStatus.STANDBY
    device.power_level = 0
    assert device.status == DeviceStatus.STANDBY, "状态修改失败"
    print(f"[OK] 状态修改成功: {device.status}")
    
    # 测试事件记录
    home.add_event("测试事件")
    assert len(home.active_events) > 0, "事件记录失败"
    print(f"[OK] 事件记录成功，共 {len(home.active_events)} 条事件")
    
    print("\n阶段一测试通过！\n")
    return True


def test_phase_2():
    """测试阶段二：MCP Server"""
    print("=" * 60)
    print("阶段二：测试 MCP Server")
    print("=" * 60)
    
    import asyncio
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
    
    async def test_mcp():
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["home_device_mcp_server.py"]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 测试工具列表
                tools = await session.list_tools()
                assert len(tools.tools) >= 5, "工具数量不足"
                print(f"[OK] 成功获取 {len(tools.tools)} 个工具")
                
                # 测试获取家居状态
                result = await session.call_tool("get_home_status", {})
                assert result.content[0].text, "获取状态失败"
                print("[OK] 获取家居状态成功")
                
                # 测试控制设备
                result = await session.call_tool("control_device", {
                    "device_id": "living_light_001",
                    "command": "on"
                })
                assert "成功" in result.content[0].text, "控制设备失败"
                print("[OK] 控制设备成功")
                
                # 测试报告传感器数据
                result = await session.call_tool("report_sensor_data", {
                    "room_name": "客厅",
                    "event_desc": "测试事件"
                })
                assert "成功" in result.content[0].text, "报告传感器数据失败"
                print("[OK] 报告传感器数据成功")
                
                return True
    
    result = asyncio.run(test_mcp())
    print("\n阶段二测试通过！\n")
    return result


def test_phase_3():
    """测试阶段三：多智能体协作图（需要 API 密钥）"""
    print("=" * 60)
    print("阶段三：测试多智能体协作图")
    print("=" * 60)
    
    # 检查是否配置了 API 密钥
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        print("[SKIP] 跳过阶段三测试：未配置 API 密钥")
        print("提示：设置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 环境变量后可运行此测试")
        return True
    
    try:
        from home_agent_graph import HomeAgentGraph
        
        # 初始化图
        agent_graph = HomeAgentGraph()
        print("[OK] 多智能体系统初始化成功")
        
        # 测试简单查询
        response = agent_graph.execute("家里现在什么情况")
        assert response, "执行失败"
        print(f"[OK] 查询执行成功: {response[:50]}...")
        
        print("\n阶段三测试通过！\n")
        return True
    except Exception as e:
        print(f"[FAIL] 阶段三测试失败: {e}")
        print("提示：请确保 API 密钥配置正确")
        return False


def test_phase_4():
    """测试阶段四：事件驱动主循环（演示模式）"""
    print("=" * 60)
    print("阶段四：测试事件驱动主循环")
    print("=" * 60)
    
    import asyncio
    from main_loop import demo_mode
    
    # 运行演示模式
    asyncio.run(demo_mode())
    
    print("\n阶段四测试通过！\n")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("智能家居系统集成测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 阶段一
    try:
        results.append(("阶段一：数字孪生状态机", test_phase_1()))
    except Exception as e:
        print(f"[FAIL] 阶段一测试失败: {e}\n")
        results.append(("阶段一：数字孪生状态机", False))
    
    # 阶段二
    try:
        results.append(("阶段二：MCP Server", test_phase_2()))
    except Exception as e:
        print(f"[FAIL] 阶段二测试失败: {e}\n")
        results.append(("阶段二：MCP Server", False))
    
    # 阶段三
    try:
        results.append(("阶段三：多智能体协作图", test_phase_3()))
    except Exception as e:
        print(f"[FAIL] 阶段三测试失败: {e}\n")
        results.append(("阶段三：多智能体协作图", False))
    
    # 阶段四
    try:
        results.append(("阶段四：事件驱动主循环", test_phase_4()))
    except Exception as e:
        print(f"[FAIL] 阶段四测试失败: {e}\n")
        results.append(("阶段四：事件驱动主循环", False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    print("=" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能家居系统测试")
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        help="测试指定阶段（1-4），不指定则运行所有测试"
    )
    
    args = parser.parse_args()
    
    if args.phase:
        # 测试指定阶段
        if args.phase == 1:
            test_phase_1()
        elif args.phase == 2:
            test_phase_2()
        elif args.phase == 3:
            test_phase_3()
        elif args.phase == 4:
            test_phase_4()
    else:
        # 运行所有测试
        success = run_all_tests()
        sys.exit(0 if success else 1)
