# Copilot Instructions for LangGraph Python Project

## Project Overview
このプロジェクトは **LangGraph** を用いた状態保持型・グラフベースのAIエージェント/ワークフローアプリケーションです。
- LangGraph（LangChainエコシステム）のStateGraph / 関数型APIを中心に構築
- 信頼性・デバッグ容易性・生産性・Human-in-the-Loop（HITL）を重視した生産レベルコード
- Python 3.11+、型ヒント（TypedDict / Pydantic）を徹底

## Core Principles (最優先)
1. **Modularity & Separation of Concerns**
   - State定義（state.py）
   - Nodes（個別関数、nodes/ または utils/nodes.py）
   - Tools（tools/ または utils/tools.py）
   - Graph構築（agent.py / graphs/）
   - Promptsは別ファイル（prompts/）に分離し、f-stringやPromptTemplateで動的生成

2. **State Management**
   - 基本は `TypedDict` + `Annotated` + `operator.add`（reducer）を使用
   - 複雑な場合は Pydantic BaseModel（v2） + `langgraph.pydantic` 対応
   - Stateには「生データ」を保存（フォーマットはnode内で）
   - 必須キー例: messages (AIMessage/HumanMessage), next, error, metadata

3. **Node Design**
   - 各nodeは純粋関数（def node(state: State) -> State:）
   - LLM呼び出しは `langchain_core.runnables` や bind_tools を活用
   - ツール呼び出し後は必ず tool_calls を処理
   - エラーハンドリングとリトライロジックを明確に

4. **Graph Construction**
   - `StateGraph(State)` を使用
   - `add_node`, `add_edge`, `add_conditional_edges` を適切に
   - START / END から明確に開始・終了
   - コンパイル時は `checkpointer=MemorySaver()` または PostgresSaver など
   - 条件分岐は `route_` プレフィックス関数で明確に

## Coding Standards
- **Type Hints**: 全ての関数・変数に厳格に適用（from typing import Annotated, TypedDict）
- **Style**: Black + Ruff + isort（pyproject.toml で管理）
- **Docstrings**: Googleスタイル or NumPyスタイル。ツールには詳細なdescriptionとexamples必須
- **Error Handling**: 可能な限り例外をキャッチし、stateにerrorフィールドを追加してグラフを継続
- **Logging / Tracing**: LangSmith / LangGraph tracingを有効化。`logger.info` を適切に使用
- **Async**: 可能なら `async def` node と `async` graphを使用（特にAPI呼び出し時）

## Recommended Project Structure

```tree
project-root/
├── .devcontainer/
├── .github/
│   └── copilot-instructions.md
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── src/
    ├── __init__.py
    ├── config.py              # 設定・環境変数（Ollama, MCP など）
    ├── logger.py              # ロギング設定（RotatingFileHandler）
    ├── main.py                # エントリポイント（asyncio.run）
    ├── agent/
    │   ├── __init__.py
    │   ├── graph.py           # StateGraph 構築・compile()
    │   ├── message_utils.py   # メッセージ加工ユーティリティ
    │   ├── nodes.py           # ノード関数（make_call_model など）
    │   └── state.py           # State 定義（PathfinderState）
    └── services/
        └── pathfinder_service.py  # MCP 接続・グラフ実行・結果パース
```


## Best Practices for LangGraph
- **Persistence**: MemorySaver（開発）→ PostgresSaver / Redis など（本番）
- **Human-in-the-Loop**: `interrupt_before=["tool_node"]` や `Command(resume=...)` を活用
- **Streaming**: `.astream_events()` または `.astream()` を積極利用
- **Multi-Agent**: Send API や hierarchical graph を検討
- **ReAct / Tool Calling**: ツールのdocstringを非常に詳細に（examples必須）
- **Testing**: 各nodeを独立テスト + グラフのsnapshotテスト
- **Security**: ツール実行前に権限チェック、sandbox化検討
- **Performance**: 不要なstate肥大化を避け、reducerを適切に使用

## Prompt Engineering Rules
- System promptは明確・役割指定・出力形式指定（JSON mode推奨時）
- Few-shot examplesを積極的に含める
- ツール説明は「このツールは何をするか」「いつ使うか」「引数の意味」を詳細に

## When Generating/Refactoring Code
- 常に上記の構造と原則を守る
- 新しいnodeを作成するときは既存の命名規則・パターンに合わせる
- ツール追加時は @tool デコレータ + 詳細docstring
- グラフ更新時は visualize（graph.get_graph().draw_mermaid()）を提案
- 最新のLangGraphベストプラクティス（StateGraph + reducers + checkpointer）を優先

## Forbidden / Avoid
- グローバル変数多用
- Stateにフォーマット済み文字列を直接保存
- 大きな単一関数での全部実装
- 型ヒントなしのコード
- ハードコードされたAPIキー

Copilotはこの指示を厳密に守り、**クリーンで保守性が高く、LangGraph公式推奨パターンに沿ったコード**を生成してください。
質問があればまずこの構造と原則を確認してから提案を。
