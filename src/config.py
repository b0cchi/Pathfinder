# config.py
import os
from dotenv import load_dotenv
from mcp import StdioServerParameters

load_dotenv()

# スナップショット
MAX_SNAPSHOT_CHARS: int = 6000

# Ollama
OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b")
OLLAMA_BASE_URL: str = os.environ["OLLAMA_BASE_URL"]

# MCP
MCP_SERVER_PARAMS = StdioServerParameters(
    command="npx",
    args=["-y", "@playwright/mcp"]
)