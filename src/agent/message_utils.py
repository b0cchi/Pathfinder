# agent/message_utils.py
from langchain_core.messages import ToolMessage
from config import MAX_SNAPSHOT_CHARS

def summarize_tool_messages(messages: list) -> list:
    snapshot_indices = []
    for i, m in enumerate(messages):
        if isinstance(m, ToolMessage):
            name = getattr(m, "name", "") or ""
            if "snapshot" in name.lower():
                snapshot_indices.append(i)

    stale_snapshot_indices = set(snapshot_indices[:-1])

    new_messages = []
    for i, m in enumerate(messages):
        if not isinstance(m, ToolMessage):
            new_messages.append(m)
            continue

        name = getattr(m, "name", "") or ""
        content = m.content if isinstance(m.content, str) else str(m.content)

        if i in stale_snapshot_indices:
            trimmed = ToolMessage(
                content="[この browser_snapshot 結果は省略済み]",
                tool_call_id=m.tool_call_id,
                name=name,
            )
            new_messages.append(trimmed)

        elif "snapshot" in name.lower() and len(content) > MAX_SNAPSHOT_CHARS:
            trimmed_content = (
                "[前略 — スナップショット先頭省略]\n"
                + content[-MAX_SNAPSHOT_CHARS:]
            )
            trimmed = ToolMessage(
                content=trimmed_content,
                tool_call_id=m.tool_call_id,
                name=name,
            )
            new_messages.append(trimmed)

        else:
            new_messages.append(m)

    return new_messages