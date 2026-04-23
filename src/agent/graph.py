# agent/graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from agent.state import PathfinderState
from agent.nodes import make_call_model

def should_continue(state: PathfinderState):
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    return "tools" if tool_calls else END

def build_graph(model, tools):
    """
    LangGraph ワークフローを構築して返すファクトリ関数。
    model, tools を受け取りコンパイル済みグラフを返す。
    """
    workflow = StateGraph(PathfinderState)
    workflow.add_node("agent", make_call_model(model))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    return workflow.compile()