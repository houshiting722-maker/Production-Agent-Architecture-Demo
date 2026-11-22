from mcp.server.mcpserver import MCPServer

# 初始化一个标准的 MCP 2.x Server
mcp = MCPServer("VideoCreatorTools")


@mcp.tool()
def search_broll_clips(keyword: str, max_duration_sec: int = 10) -> str:
    """
    根据关键词检索符合时长要求的空镜视频素材（B-Roll）。
    
    Args:
        keyword: 画面检索关键词，例如 '城市夜景'、'咖啡制作'
        max_duration_sec: 素材最大时长限制（秒），默认 10 秒
    """
    mock_clips = [
        f"clip_001_{keyword}_4k.mp4 (时长: {min(5, max_duration_sec)}s, 评分: 9.5)",
        f"clip_002_{keyword}_slowmo.mp4 (时长: {min(8, max_duration_sec)}s, 评分: 9.1)"
    ]
    return f"检索到 {len(mock_clips)} 条匹配素材: " + " | ".join(mock_clips)


@mcp.tool()
def estimate_tts_duration(script_text: str, words_per_second: float = 4.2) -> dict:
    """
    估算口播文案生成语音（TTS）后的音频总时长，用于视频时间轴对齐。
    """
    char_count = len(script_text.strip())
    estimated_sec = round(char_count / words_per_second, 2)
    return {
        "char_count": char_count,
        "estimated_duration_sec": estimated_sec,
        "suggestion": "节奏适中，适合作为黄金开头" if estimated_sec <= 5.0 else "建议精简前3秒文案"
    }


@mcp.resource("config://creator/style-guide")
def get_style_guide() -> str:
    """暴露只读的创作规范文档资源（Resource）"""
    return "剪映爆款规范：1. 前3秒必须出现视觉冲突或痛点提问；2. 字幕单行不超过14个字。"


if __name__ == "__main__":
    mcp.run(transport="stdio")