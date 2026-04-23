# services/pathfinder_service.py
import json
import re
from mcp import stdio_client
from mcp.client.session import ClientSession
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from config import OLLAMA_MODEL, OLLAMA_BASE_URL, MCP_SERVER_PARAMS
from agent.graph import build_graph
from logger import logger

SYSTEM_PROMPT = """
あなたはブラウザ操作エージェントです。

【重要ルール】
- 必要な情報が揃ったら、ツールを使わず必ず最終回答を出すこと
- 無限にツールを呼び続けてはいけない
- 同じページで2回以上 browser_snapshot を実行してはいけない

【最終回答フォーマット】
必ず以下のJSON形式のみで出力せよ。余計な説明文は不要：
```json
{
  "venues": [
    {"name": "会場名1", "address": "住所1"},
    {"name": "会場名2", "address": "住所2"}
  ]
}
```
会場が1つの場合も必ず配列形式で出力せよ。
情報がページ内に存在しない場合は対応する値を "不明" とすること。
"""

USER_PROMPT_TEMPLATE = """
URL: {url}

【タスク】
このイベントの「開催会場」と「住所」を特定せよ。

【解析方針】
- browser_snapshot の結果から、テキスト情報のみを利用する（YAML構造タグは無視）
- ヘッダーメニューから「会場案内」「Venue」「Access」などのリンクを探す
- 必要な場合のみリンクをクリックする

【行動ルール】
1. 最初に browser_navigate を実行してページにアクセス
2. 次に browser_snapshot を実行して内容を確認
3. 会場情報が見つからない場合のみ、関連リンクへ遷移する
4. 情報が見つかったら、その時点でツールの使用を止めて回答する

【禁止事項】
- フォーム操作は禁止
- 存在しない要素の探索は禁止
- 不要なツールの連続実行は禁止
"""

def _parse_final_answer(raw: str) -> dict:
    """最終回答のテキストからJSONをパースして返す。"""
    json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", raw, re.DOTALL)
    raw_json = json_match.group(1) if json_match else raw.strip()

    parsed = json.loads(raw_json)

    # 旧形式 {"venue": ..., "address": ...} を配列形式に変換
    if "venue" in parsed and "venues" not in parsed:
        parsed = {
            "venues": [
                {"name": parsed["venue"], "address": parsed.get("address", "不明")}
            ]
        }
    return parsed


async def run_pathfinder(url: str) -> dict:
    """
    指定URLにアクセスし、開催会場と住所を返す。

    Returns:
        {"venues": [{"name": ..., "address": ...}, ...]}

    Raises:
        ValueError: 最終回答が得られなかった場合
        json.JSONDecodeError: JSONパースに失敗した場合
    """
    logger.info("[1] Connecting to Playwright MCP Server...")
    async with stdio_client(MCP_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            logger.info("[2] Loading tools...")
            tools = await load_mcp_tools(session)

            logger.info("[3] Initializing Ollama...")
            model = ChatOllama(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL
            ).bind_tools(tools)

            logger.info("[4] Building Graph...")
            app = build_graph(model, tools)

            inputs = {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=USER_PROMPT_TEMPLATE.format(url=url)),
                ]
            }

            logger.info("--- Mission Start: %s ---", url)
            final_answer: str | None = None

            async for event in app.astream(inputs, stream_mode="values"):
                last_message = event["messages"][-1]

                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    logger.info("Pathfinder's Plan: %s", last_message.tool_calls)

                if hasattr(last_message, "thinking") and last_message.thinking:
                    logger.info("Pathfinder's thinking: %s", last_message.thinking)

                content = getattr(last_message, "content", None)
                tool_calls = getattr(last_message, "tool_calls", None)
                if content and not tool_calls:
                    final_answer = content if isinstance(content, str) else str(content)

            if not final_answer:
                raise ValueError("最終回答を取得できませんでした。")

            return _parse_final_answer(final_answer)