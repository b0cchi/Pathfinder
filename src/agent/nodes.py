# agent/nodes.py
from langchain_core.messages import ToolMessage
from agent.state import PathfinderState
from agent.message_utils import summarize_tool_messages
from logger import logger

def make_call_model(model):
    """
    call_model ノードのファクトリ関数。
    model を受け取り、LangGraph ノードとして使える関数を返す。
    """
    def call_model(state: PathfinderState):
        logger.info("--- LLM is thinking... ---")
        try:
            messages = summarize_tool_messages(state["messages"])

            has_snapshot = any(
                isinstance(m, ToolMessage) and "snapshot" in getattr(m, "name", "")
                for m in state["messages"]
            )
            if has_snapshot:
                messages[0].content += "\n\n[注意: browser_snapshot は既に実行済みです。再実行禁止。]"

            logger.debug("messages sent to model (%d件):", len(messages))
            for m in messages:
                logger.debug("  [%s] %s", type(m).__name__,
                            repr(getattr(m, "content", ""))[:200])

            response = model.invoke(messages)
            logger.debug("response.content: %s", repr(getattr(response, "content", None)))
            logger.debug("response.tool_calls: %s", repr(getattr(response, "tool_calls", None)))
            return {"messages": [response]}

        except Exception as e:
            msg = str(e).lower()
            if "context" in msg or "token" in msg or "too long" in msg:
                logger.warning("context/token overflow の可能性あり")
            logger.error("Error in LLM call: %s", e)
            raise

    return call_model