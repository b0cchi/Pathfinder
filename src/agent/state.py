# agent/state.py
from typing import Annotated, List, TypedDict
from langchain_core.messages import BaseMessage

class PathfinderState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]