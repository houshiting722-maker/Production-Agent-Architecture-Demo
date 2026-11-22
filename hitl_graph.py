from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver


# ==========================================
# 1. 定义带人工审批状态的 State
# ==========================================
class PublishState(TypedDict):
    topic: str
    script: str
    human_approved: bool    # 人工是否批准发布
    publish_status: str     # 最终发布状态


# ==========================================
# 2. 定义节点
# ==========================================
def draft_node(state: PublishState) -> dict:
    print(f"\n[节点 1: Draft] 正在为主题《{state['topic']}》生成待发布脚本...")
    return {
        "script": f"【待审核脚本】3个让你效率翻倍的 AI 剪辑技巧！",
        "human_approved": False
    }


def publish_node(state: PublishState) -> dict:
    """高危/对外发布节点：必须经过人工确认才能执行"""
    if not state.get("human_approved"):
        print("\n[节点 2: Publish] 人工拒绝发布，流程安全终止。")
        return {"publish_status": "已取消发布"}

    print(f"\n[节点 2: Publish] 收到人工授权！正在自动发布脚本：{state['script']}")
    return {"publish_status": "全网发布成功！"}


# ==========================================
# 3. 组装图并挂载 Checkpointer + 断点
# ==========================================
builder = StateGraph(PublishState)
builder.add_node("draft", draft_node)
builder.add_node("publish", publish_node)

builder.add_edge(START, "draft")
builder.add_edge("draft", "publish")
builder.add_edge("publish", END)

# 核心考点 1：初始化检查点存储器（生产环境可无缝替换为 PostgresSaver / RedisSaver）
memory = MemorySaver()

# 核心考点 2：compile 时指定 checkpointer 和 interrupt_before（在 publish 节点前强制挂起）
graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["publish"]
)


if __name__ == "__main__":
    # 每个用户会话分配唯一的 thread_id，这是状态隔离与恢复的钥匙
    config = {"configurable": {"thread_id": "user_session_888"}}

    print("====== 第一步：启动任务（将在 publish 节点前自动暂停） ======")
    graph.invoke({"topic": "AI 剪辑技巧"}, config=config)

    # 查看当前挂起的状态快照（Snapshot）
    snapshot = graph.get_state(config)
    print(f"\n>>> 当前状态机已挂起！下一个待执行节点: {snapshot.next}")
    print(f">>> 当前保存的草稿内容: {snapshot.values['script']}")

    # ---------------------------------------------------------
    # 模拟前端弹窗：用户审核了草稿，不仅点了“同意”，还顺手改了标题！
    # ---------------------------------------------------------
    user_input = input("\n[人工介入] 是否批准发布？(输入 y 批准，输入其他取消): ")

    if user_input.strip().lower() == "y":
        # 核心考点 3：update_state 动态修改挂起中的状态（模拟人工微调 + 授权）
        graph.update_state(
            config,
            {
                "human_approved": True,
                "script": snapshot.values["script"] + "（人工已润色版）"
            }
        )
    else:
        graph.update_state(config, {"human_approved": False})

    print("\n====== 第二步：从断点处恢复执行（传入 None 表示继续当前状态） ======")
    final_result = graph.invoke(None, config=config)
    print("\n================ 最终结果 ================")
    print(final_result)