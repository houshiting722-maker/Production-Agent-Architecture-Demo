import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Dict


# ==========================================
# 1. 轻量级全链路追踪器（Tracing 底层原理）
# ==========================================
@dataclass
class SpanRecord:
    step_name: str
    input_data: Any
    output_data: Any
    latency_ms: float
    status: str = "SUCCESS"


@dataclass
class ExecutionTrace:
    trace_id: str
    query: str
    spans: List[SpanRecord] = field(default_factory=list)
    called_tools: List[str] = field(default_factory=list)
    final_output: str = ""

    def record_span(self, step_name: str, input_data: Any, output_data: Any, latency_ms: float, status: str = "SUCCESS"):
        self.spans.append(SpanRecord(step_name, input_data, output_data, latency_ms, status))


# ==========================================
# 2. 模拟带轨迹记录的智能创作 Agent
# ==========================================
class VideoCreatorAgent:
    def __init__(self, prompt_version: str = "v1.0"):
        self.prompt_version = prompt_version

    def _run_tool(self, trace: ExecutionTrace, tool_name: str, func: Callable, **kwargs) -> Any:
        start = time.perf_counter()
        try:
            res = func(**kwargs)
            latency = round((time.perf_counter() - start) * 1000, 2)
            trace.called_tools.append(tool_name)
            trace.record_span(f"tool:{tool_name}", kwargs, res, latency, "SUCCESS")
            return res
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            trace.record_span(f"tool:{tool_name}", kwargs, str(e), latency, "ERROR")
            raise

    def run(self, trace_id: str, user_query: str) -> ExecutionTrace:
        trace = ExecutionTrace(trace_id=trace_id, query=user_query)

        # 步骤 1：意图识别与规划（Plan）
        t0 = time.perf_counter()
        if "素材" in user_query or "空镜" in user_query:
            plan = ["search_broll"]
        elif "时长" in user_query or "口播" in user_query:
            plan = ["estimate_tts"]
        elif "爆款" in user_query or "剪辑" in user_query:
            plan = ["search_broll", "estimate_tts"]
        else:
            plan = []
        trace.record_span("planner", user_query, plan, round((time.perf_counter() - t0) * 1000, 2))

        # 步骤 2：按规划调用工具（Act）
        context_pieces = []
        if "search_broll" in plan:
            clip_res = self._run_tool(
                trace,
                "search_broll_clips",
                lambda kw: f"匹配到高分素材: {kw}_4k.mp4",
                kw=user_query[:6]
            )
            context_pieces.append(clip_res)

        if "estimate_tts" in plan:
            tts_res = self._run_tool(
                trace,
                "estimate_tts_duration",
                lambda txt: {"duration_sec": round(len(txt) / 4.2, 2)},
                txt=user_query
            )
            context_pieces.append(f"预计口播时长 {tts_res['duration_sec']}s")

        # 步骤 3：生成最终回复（Synthesize）
        t1 = time.perf_counter()
        if not context_pieces:
            final_msg = "您好，请告诉我您想剪辑的视频主题，我来为您匹配素材并规划脚本。"
        else:
            final_msg = f"[{self.prompt_version}] 已为您完成规划：" + "；".join(context_pieces) + "。建议前3秒加入痛点钩子！"

        trace.final_output = final_msg
        trace.record_span("synthesizer", context_pieces, final_msg, round((time.perf_counter() - t1) * 1000, 2))
        return trace