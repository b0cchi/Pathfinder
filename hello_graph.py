from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# 1. 状態の定義（何を持ち回るか）


class State(TypedDict):
    message: str

# 2. 処理内容の定義（ノード）


def say_hello(state: State):
    return {"message": state["message"] + " -> Hello from Pathfinder!"}


# 3. グラフの構築
builder = StateGraph(State)

# ノードを追加
builder.add_node("greeter", say_hello)

# エッジ（流れ）を定義
builder.add_edge(START, "greeter")
builder.add_edge("greeter", END)

# グラフをコンパイル
graph = builder.compile()

# 4. 実行
result = graph.invoke({"message": "Start"})
print(result)
