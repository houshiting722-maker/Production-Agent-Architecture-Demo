import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_mcp_client():
    # 配置要连接的本地 MCP Server 启动参数（使用当前虚拟环境的 python 解释器）
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["video_mcp_server.py"],
    )

    # 建立 stdio 双向通信管道
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 1. MCP 协议标准初始化握手
            await session.initialize()
            print(">>> [MCP 握手成功] 已连接到 VideoCreatorTools Server\n")

            # 2. 动态发现服务端暴露的所有 Tools（大模型靠这个知道有哪些工具可用）
            tools_response = await session.list_tools()
            print(f">>> 发现 {len(tools_response.tools)} 个标准 MCP 工具：")
            for tool in tools_response.tools:
                print(f"  - 工具名: {tool.name}")
                print(f"    描述: {tool.description.strip().splitlines()[0]}")
                print(f"    自动生成的参数 Schema: {tool.input_schema}\n")

            # 3. 模拟 Agent 发起标准工具调用（tools/call）
            print(">>> [执行调用 1] 调用 search_broll_clips...")
            res1 = await session.call_tool(
                "search_broll_clips",
                arguments={"keyword": "赛博朋克夜景", "max_duration_sec": 6}
            )
            print(f"返回结果: {res1.content[0].text}\n")

            print(">>> [执行调用 2] 调用 estimate_tts_duration...")
            res2 = await session.call_tool(
                "estimate_tts_duration",
                arguments={"script_text": "还在手动一帧帧剪视频吗？今天教你一招全自动成片！"}
            )
            print(f"返回结果: {res2.content[0].text}\n")

            # 4. 读取只读资源（Resources）
            resource_res = await session.read_resource("config://creator/style-guide")
            print(f">>> [读取资源] {resource_res.contents[0].text}")


if __name__ == "__main__":
    asyncio.run(run_mcp_client())