import pytest
from observable_agent import VideoCreatorAgent


# ==========================================
# 黄金评测数据集（Golden Dataset）
# 覆盖：单工具意图、多工具协同意图、闲聊兜底边界 Case
# ==========================================
GOLDEN_DATASET = [
    {
        "case_id": "TC_001_单工具素材检索",
        "query": "帮我找一些咖啡制作的空镜素材",
        "expected_tools": ["search_broll_clips"],
        "must_contain": ["匹配到高分素材"],
        "max_latency_ms": 500.0,
    },
    {
        "case_id": "TC_002_单工具时长估算",
        "query": "帮我算一下这段口播文案的语音时长",
        "expected_tools": ["estimate_tts_duration"],
        "must_contain": ["预计口播时长"],
        "max_latency_ms": 500.0,
    },
    {
        "case_id": "TC_003_复合意图多工具协同",
        "query": "我要做一个爆款短视频剪辑方案",
        "expected_tools": ["search_broll_clips", "estimate_tts_duration"],
        "must_contain": ["匹配到高分素材", "预计口播时长", "痛点钩子"],
        "max_latency_ms": 500.0,
    },
    {
        "case_id": "TC_004_模糊输入边界兜底",
        "query": "你好啊，今天天气不错",
        "expected_tools": [],
        "must_contain": ["请告诉我您想剪辑的视频主题"],
        "max_latency_ms": 500.0,
    },
]


@pytest.fixture(scope="module")
def agent():
    return VideoCreatorAgent(prompt_version="v1.0")


@pytest.mark.parametrize("case", GOLDEN_DATASET, ids=[c["case_id"] for c in GOLDEN_DATASET])
def test_agent_trajectory_and_quality(agent, case):
    """自动化评测：验证工具调用轨迹准确率、输出规范忠实度及性能SLA"""
    trace = agent.run(trace_id=case["case_id"], user_query=case["query"])

    # 1. 过程评估（Trajectory Evaluation）：工具选择与调用顺序必须 100% 精准
    assert trace.called_tools == case["expected_tools"], (
        f"[{case['case_id']}] 工具调用轨迹不匹配！期望: {case['expected_tools']}, 实际: {trace.called_tools}"
    )

    # 2. 结果评估（Faithfulness & Rule Check）：核心要素不能遗漏
    for keyword in case["must_contain"]:
        assert keyword in trace.final_output, (
            f"[{case['case_id']}] 输出缺少关键业务要素 '{keyword}'，实际输出: {trace.final_output}"
        )

    # 3. 性能 SLA 断言：全链路总耗时不能超过阈值
    total_latency = sum(span.latency_ms for span in trace.spans)
    assert total_latency <= case["max_latency_ms"], (
        f"[{case['case_id']}] 响应超时！总耗时 {total_latency}ms > 阈值 {case['max_latency_ms']}ms"
    )