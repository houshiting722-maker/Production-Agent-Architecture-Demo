import asyncio
import json
import time
from typing import AsyncGenerator, List, Literal
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Production Agent Service Demo")


# ==========================================
# 1. Pydantic 强类型契约（入参 & Agent 内部状态）
# ==========================================
class AgentRequest(BaseModel):
    session_id: str = Field(..., description="会话唯一ID，用于追踪上下文")
    query: str = Field(..., min_length=1, max_length=1000, description="用户输入指令")
    enable_parallel_tools: bool = Field(default=True, description="是否开启工具并行调用")


class StreamEvent(BaseModel):
    """标准 SSE 推送事件结构"""
    type: Literal["thought", "tool_call", "tool_result", "content", "error", "done"]
    payload: str
    timestamp: float = Field(default_factory=time.time)

    def to_sse(self) -> str:
        # 严格遵循 SSE 协议格式：data: <json>\n\n
        return f"data: {self.model_dump_json()}\n\n"


# ==========================================
# 2. 模拟异步工具（Tool Calling 底层）
# ==========================================
async def mock_search_tool(keyword: str) -> str:
    """模拟耗时 1.5 秒的外部检索工具"""
    await asyncio.sleep(1.5)
    return f"[检索结果] 找到与 '{keyword}' 相关的 3 条最新业务数据。"


async def mock_user_profile_tool(session_id: str) -> str:
    """模拟耗时 1.2 秒的用户画像/记忆查询工具"""
    await asyncio.sleep(1.2)
    return f"[用户偏好] 会话 {session_id} 偏好简洁、结构化的输出风格。"

async def mock_broken_tool() -> str:
    """模拟耗时 0.5 秒后超时的第三方非核心工具"""
    await asyncio.sleep(0.5)
    raise TimeoutError("热点趋势接口响应超时")

# ==========================================
# 3. 核心 Agent 异步流式编排器
# ==========================================
async def agent_event_generator(req: AgentRequest) -> AsyncGenerator[str, None]:
    try:
        # 步骤 A：推送思考状态
        yield StreamEvent(type="thought", payload="正在拆解用户意图并规划所需工具...").to_sse()
        await asyncio.sleep(0.3)

        # 步骤 B：并行 vs 串行调用工具（性能分水岭）
        yield StreamEvent(
            type="tool_call",
            payload="并行调用: search_tool & user_profile_tool"
        ).to_sse()

        start_time = time.perf_counter()
        if req.enable_parallel_tools:
            results = await asyncio.gather(
                mock_search_tool(req.query),
                mock_user_profile_tool(req.session_id),
                mock_broken_tool(),
                return_exceptions=True  # 捕获单个工具异常，不中断其他工具
            )
            search_res = results[0] if not isinstance(results[0], Exception) else "[降级] 检索服务暂不可用"
            profile_res = results[1] if not isinstance(results[1], Exception) else "[降级] 使用默认用户画像"
            trend_res = results[2] if not isinstance(results[2], Exception) else "[降级] 热点接口超时，已跳过"
        else:
            search_res = await mock_search_tool(req.query)
            profile_res = await mock_user_profile_tool(req.session_id)
            trend_res = "[降级] 串行模式已跳过热点查询"

        elapsed = round(time.perf_counter() - start_time, 2)
        yield StreamEvent(
            type="tool_result",
            payload=f"工具执行完成（耗时 {elapsed}s）| {search_res} | {profile_res} | {trend_res}"
        ).to_sse()

        # 步骤 C：模拟大模型 Token 级流式输出（Streaming）
        mock_llm_tokens = [
            "根据", "检索", "结果", "与您的", "偏好，",
            "为您", "生成", "如下", "执行", "方案：",
            "1. 确认目标；", "2. 异步执行；", "3. 闭环验收。"
        ]
        for token in mock_llm_tokens:
            await asyncio.sleep(0.1)  # 模拟大模型逐字生成延迟
            yield StreamEvent(type="content", payload=token).to_sse()

        # 步骤 D：发送结束信号
        yield StreamEvent(type="done", payload="[DONE]").to_sse()

    except asyncio.CancelledError:
        # 生产级必备：捕获前端主动断开连接（用户点击“停止生成”）
        print(f"[INFO] Session {req.session_id} 客户端主动中断了流式连接，释放资源。")
        raise
    except Exception as e:
        # 兜底异常捕获，防止流意外中断无提示
        yield StreamEvent(type="error", payload=f"服务内部异常: {str(e)}").to_sse()


# ==========================================
# 4. FastAPI 路由暴露
# ==========================================
@app.post("/api/v1/agent/chat")
async def chat_stream(request: AgentRequest):
    return StreamingResponse(
        agent_event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 关键工程细节：防止 Nginx 反向代理缓存 SSE 流
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)