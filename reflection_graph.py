from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END


# ==========================================
# 1. 定义全局状态（State）：所有节点共享的数据结构
# ==========================================
class AgentState(TypedDict):
    topic: str              # 用户输入的创作主题
    draft: str              # 当前生成的方案草稿
    critique: str           # 质检官（Critic）给出的修改意见
    revision_count: int     # 当前修改次数（防止死循环的熔断计数器！）
    is_approved: bool       # 质检是否通过


# ==========================================
# 2. 定义图节点（Nodes）：每个节点接收 state，返回部分更新字段
# ==========================================
def generator_node(state: AgentState) -> dict:
    """节点 A：方案生成器（首次生成 或 根据质检意见重写）"""
    count = state.get("revision_count", 0) + 1
    critique = state.get("critique", "")

    print(f"\n--- [执行节点: Generator] 第 {count} 次生成 ---")
    if not critique:
        # 首次生成：故意写一个缺少数据支撑和行动号召的粗糙草稿
        new_draft = f"《{state['topic']}》短视频脚本：开头直接讲产品功能，中间展示画面，结尾结束。"
    else:
        # 收到 Critic 的打回意见后，针对性优化
        print(f"收到质检反馈，正在针对性重构：{critique}")
        new_draft = (
            f"《{state['topic']}》爆款脚本（v{count}）："
            f"【黄金3秒痛点钩子】+【3组核心数据对比画面】+【结尾引导评论区互动CTA】。"
        )

    return {
        "draft": new_draft,
        "revision_count": count
    }


def critic_node(state: AgentState) -> dict:
    """节点 B：严苛质检官（模拟 Reflection 反思评估）"""
    draft = state["draft"]
    print(f"--- [执行节点: Critic] 正在审查草稿: {draft} ---")

    # 模拟业务质检规则：必须包含“痛点钩子”和“CTA”才算合格
    if "痛点钩子" in draft and "CTA" in draft:
        print(">>> 质检结果：【通过】结构完整，符合爆款标准！")
        return {"is_approved": True, "critique": "完美通过"}
    else:
        feedback = "缺少前3秒痛点钩子，且结尾没有互动引导（CTA），请补充重写。"
        print(f">>> 质检结果：【打回】{feedback}")
        return {"is_approved": False, "critique": feedback}


# ==========================================
# 3. 定义条件路由边（Conditional Edge）：决定图的流向
# ==========================================
def should_continue(state: AgentState) -> Literal["generator", "__end__"]:
    """路由决策函数：决定是打回重写，还是结束流程"""
    # 生产级必备红线：必须设置最大重试上限，防止大模型陷入死循环烧光 Token！
    MAX_REVISIONS = 3

    if state["is_approved"]:
        return "__end__"
    if state["revision_count"] >= MAX_REVISIONS:
        print(f"--- [路由熔断] 已达到最大修改次数 ({MAX_REVISIONS}次)，强制结束 ---")
        return "__end__"
    return "generator"


# ==========================================
# 4. 组装并编译状态图（Graph）
# ==========================================
builder = StateGraph(AgentState)

# 添加节点
builder.add_node("generator", generator_node)
builder.add_node("critic", critic_node)

# 连接边：START -> generator -> critic -> (条件路由) -> generator 或 END
builder.add_edge(START, "generator")
builder.add_edge("generator", "critic")
builder.add_conditional_edges(
    "critic",
    should_continue,
    {
        "generator": "generator",  # 打回重做，形成循环！
        "__end__": END             # 质检通过，流程结束
    }
)

# 编译成可执行的 Runnable 应用
graph = builder.compile()


if __name__ == "__main__":
    initial_state: AgentState = {
        "topic": "AI 剪辑神器测评",
        "draft": "",
        "critique": "",
        "revision_count": 0,
        "is_approved": False
    }

    final_state = graph.invoke(initial_state)
    print("\n================ 最终交付结果 ================")
    print(f"总迭代次数: {final_state['revision_count']}")
    print(f"最终成品: {final_state['draft']}")