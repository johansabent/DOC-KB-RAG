"""MCP server exposing the DOC-KB-RAG query pipeline as a tool.

Runs over stdio transport — all logging goes to stderr to avoid
corrupting the JSON-RPC stream on stdout.
"""

import logging
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Route logs to stderr so they don't interfere with MCP stdio transport.
logging.basicConfig(
    stream=sys.stderr,
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

mcp = FastMCP("doc-kb-rag")


@mcp.tool()
async def query_docs(question: str) -> str:
    """Query the documentation knowledge base.

    Takes a natural-language question and returns an answer synthesised
    from the indexed documentation, along with source file attributions.
    """
    from query import retrieve_and_answer

    result = await retrieve_and_answer(question)

    if result.error:
        return f"Error: {result.error}"

    parts = [result.answer]
    if result.sources:
        parts.append("\nSources:")
        parts.extend(result.format_sources())

    return "\n".join(parts)


if __name__ == "__main__":
    mcp.run(transport="stdio")
