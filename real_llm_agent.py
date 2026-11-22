import os
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


# ==========================================
# 1. 定义强类型结构化输出契约（以剪映分镜规划为例）
# ==========================================
class VideoClipAction(BaseModel):
    step_id: int = Field(..., description="分镜步骤序号，从1开始")
    tool_name: Literal["search_broll_clips", "estimate_tts_duration", "add_subtitle"] = Field(
        ..., description="必须从指定的可用工具列表中选择"
    )
    tool_args: str = Field(..., min_length=2, description="传给工具的具体参数描述或关键词")
    duration_sec: float = Field(..., gt=0, le=60.0, description="该镜头预计时长（秒），必须大于0且不超过60")

    @field_validator("tool_args")
    @classmethod
    def check_no_placeholder(cls, v: str) -> str:
        # 业务规则校验：防止模型偷懒输出“待定”、“无”等无效参数
        if v.strip() in ["无", "待定", "None", "null", "N/A"]:
            raise ValueError("工具参数不能为无效占位符，必须提取具体业务关键词！")
        return v


class VideoEditingPlan(BaseModel):
    """大模型必须严格按照此结构输出完整剪辑规划"""
    title: str = Field(..., description="吸引人的短视频标题")
    hook_copy: str = Field(..., description="前3秒黄金痛点钩子文案")
    actions: List[VideoClipAction] = Field(..., min_length=1, description="有序的工具执行动作列表")


# ==========================================
# 2. 构建结构化输出大模型调用链
# ==========================================
def generate_editing_plan(user_request: str) -> VideoEditingPlan:
    # 支持任意兼容 OpenAI 协议的平台（如 DeepSeek / 火山方舟豆包 / 通义千问）
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model_name = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

    if not api_key:
        print(">>> [提示] 未检测到 OPENAI_API_KEY 环境变量，使用本地结构化校验演示模式...\n")
        # 模拟模型返回符合 Schema 的字典，验证 Pydantic 强校验流水线
        raw_mock_data = {
            "title": "3分钟学会AI自动剪辑，效率翻倍！",
            "hook_copy": "还在熬夜一帧帧剪视频？今天教你一招全自动成片！",
            "actions": [
                {
                    "step_id": 1,
                    "tool_name": "estimate_tts_duration",
                    "tool_args": "还在熬夜一帧帧剪视频？今天教你一招全自动成片！",
                    "duration_sec": 4.5
                },
                {
                    "step_id": 2,
                    "tool_name": "search_broll_clips",
                    "tool_args": "程序员熬夜剪辑电脑屏幕特写",
                    "duration_sec": 5.0
                }
            ]
        }
        return VideoEditingPlan.model_validate(raw_mock_data)

    # 真实在线大模型调用（核心考点：with_structured_output）
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.2,  # 工程开发/工具规划场景，温度务必调低（0.0~0.3）保证确定性
    )

    # 绑定 Pydantic Schema，强制大模型输出可直接映射为 VideoEditingPlan 实例
    structured_llm = llm.with_structured_output(VideoEditingPlan,method="function_calling")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的短视频剪辑 Agent 规划器。请根据用户需求拆解结构化的剪辑执行步骤。"),
        ("human", "{query}")
    ])

    chain = prompt | structured_llm
    return chain.invoke({"query": user_request})


if __name__ == "__main__":
    plan = generate_editing_plan("帮我规划一个关于 AI 剪辑工具测评的短视频，需要找一些熬夜加班的空镜素材")
    print(">>> 解析成功！获得强类型 Python 对象：")
    print(f"标题: {plan.title}")
    print(f"黄金开头: {plan.hook_copy}")
    print("执行动作序列:")
    for act in plan.actions:
        print(f"  [Step {act.step_id}] 调用工具 `{act.tool_name}` | 参数: {act.tool_args} | 预计时长: {act.duration_sec}s")