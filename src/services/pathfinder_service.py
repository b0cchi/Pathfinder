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

【会場の収集ルール】
- ページ内に複数の会場が記載されている場合は、すべて収集すること
- 「一部だけ取得して終了」は禁止。必ずページ全体を確認してから回答すること
- 地域・カテゴリ別にグループ化されている場合も、各グループのすべての会場を収集すること

【住所の扱い】
- 住所が明記されていない場合は "不明" とすること
- 住所を探すために英語ページや別ドメインへ遷移することは禁止
- 日本語ページに住所がなければ素直に "不明" と記載すること

【最終回答フォーマット】
必ず以下のJSON形式のみで出力せよ。余計な説明文は不要：
```json
{
  "venues": [
    {"name": "会場名1", "address": "住所1"},
    {"name": "会場名2", "address": "住所2"},
    {"name": "会場名3", "address": "不明"}
  ]
}
```
会場が1つの場合も必ず配列形式で出力せよ。
情報がページ内に存在しない場合は対応する値を "不明" とすること。

【JSON出力の厳守ルール】
- 応答は必ず「JSONオブジェクトのみ」にしてください。
- 挨拶、説明文、Markdown記法（```jsonなど）は一切含めないでください。
- JSONとして解析できない形式で出力した場合、処理がエラーになります。

【思考の出力ルール】
ツールを呼び出す際は、必ず tool_calls の直前に、「なぜそのツールが必要なのか」「そのツールで何を確認したいのか」を説明する文章を出力してください。
この文章はユーザーがあなたの意図を理解するために非常に重要です。
"""

USER_PROMPT_TEMPLATE = """
URL: {url}

【タスク】
このイベントの「開催会場」をすべて特定し、「住所」とともに列挙せよ。
会場が複数ある場合は、1件も漏らさず収集すること。

【解析方針】
- browser_snapshot の結果から、テキスト情報のみを利用する（YAML構造タグは無視）
- ヘッダーメニューから「会場案内」「Venue」「Access」などのリンクを探す
- 会場一覧ページに遷移した場合、ページ内のすべての会場名を収集してから回答すること
- 地域別・カテゴリ別に分かれている場合も、すべてのセクションを確認すること
- 必要な場合のみリンクをクリックする

【行動ルール】
1. 最初に browser_navigate を実行してページにアクセス
2. 次に browser_snapshot を実行して内容を確認
3. 会場情報が見つからない場合のみ、関連リンクへ遷移する
4. 会場ページに到達したら、ページ内のすべての会場を収集してから回答する

【禁止事項】
- フォーム操作は禁止
- 存在しない要素の探索は禁止
- 不要なツールの連続実行は禁止
- 住所取得のための英語ページや別ドメインへの遷移は禁止
- 会場を途中で打ち切って回答することは禁止
"""

def translate_tool_to_message(tool_call):
    name = tool_call.get("name")
    args = tool_call.get("args", {})

    # ツール名に基づく翻訳テーブル
    messages = {
        "browser_navigate": f"🔗 ウェブサイトにアクセス中: {args.get('url', '指定URL')}",
        "browser_snapshot": "📸 ページ構造を解析中...",
        "browser_evaluate": "🔍 ページ内の情報を検索・抽出中...",
        "browser_click": f"🖱️ リンクをクリック中: {args.get('ref', 'リンク')}",
    }

    return messages.get(name, f"⚙️ ツールを実行中: {name}")

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

                # AIが回答（思考やツール呼び出し）を出力した時
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    # 1. AIの思考（テキスト）を取得
                    reasoning = last_message.content.strip()

                    # 2. ツール呼び出しを取得
                    for tool_call in last_message.tool_calls:
                        action_desc = translate_tool_to_message(tool_call) # 先ほど作成した翻訳関数

                        # 3. ユーザーフレンドリーなログ出力
                        print(f"🤖 思考: {reasoning if reasoning else '（特に記述なし）'}")
                        print(f"   → アクション: {action_desc}")
                        print("-" * 40)

                if hasattr(last_message, "thinking") and last_message.thinking:
                    logger.info("Pathfinder's thinking: %s", last_message.thinking)

                content = getattr(last_message, "content", None)
                tool_calls = getattr(last_message, "tool_calls", None)
                if content and not tool_calls:
                    final_answer = content if isinstance(content, str) else str(content)

            if not final_answer:
                raise ValueError("最終回答を取得できませんでした。")

            return _parse_final_answer(final_answer)


from typing import AsyncGenerator
async def stream_pathfinder(url: str) -> AsyncGenerator[str, None]:
    """
    Pathfinderの進捗をSSEイベントとして逐次yieldする。
    """
    import json

    async with stdio_client(MCP_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            model = ChatOllama(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL
            ).bind_tools(tools)
            app = build_graph(model, tools)

            inputs = {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=USER_PROMPT_TEMPLATE.format(url=url)),
                ]
            }

            final_answer: str | None = None

            async for event in app.astream(inputs, stream_mode="values"):
                last_message = event["messages"][-1]

                # ツール呼び出し中
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    reasoning = getattr(last_message, "content", "").strip()
                    for tool_call in last_message.tool_calls:
                        action_desc = translate_tool_to_message(tool_call)
                        payload = json.dumps({
                            "type": "action",
                            "thinking": reasoning or "（特に記述なし）",
                            "action": action_desc,
                        }, ensure_ascii=False)
                        yield f"data: {payload}\n\n"

                # 最終回答
                content = getattr(last_message, "content", None)
                tool_calls = getattr(last_message, "tool_calls", None)
                if content and not tool_calls:
                    final_answer = content if isinstance(content, str) else str(content)

            # 完了イベント
            if not final_answer:
                payload = json.dumps({"type": "error", "message": "最終回答を取得できませんでした。"}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            else:
                try:
                    result = _parse_final_answer(final_answer)
                    payload = json.dumps({"type": "result", "venues": result["venues"]}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                except Exception as e:
                    payload = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"