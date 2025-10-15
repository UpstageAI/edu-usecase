#!/usr/bin/env python3
"""
MCP Server for AI Agent Orchestrator Demo
Implements conversation_log and extract tools with agent orchestration
"""

import asyncio
import json
import logging
import sys
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Agent Orchestrator
from agent_orchestrator.orchestrator import orchestrator

# Initialize MCP Server
mcp = FastMCP("ai-agent-orchestrator")

# Configure logging to stderr (stdout is used for stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Note: Agent Orchestrator is imported from agent_orchestrator.orchestrator
# The orchestrator instance handles conversation_log and extract requests

@mcp.tool(name="conversation_log")
async def conversation_log(
    channel: str,
    messages: Any,  # Accept both string and list
    meta: Any = None  # Accept string, dict, or None
) -> List[TextContent]:
    """[SAFE] Store conversation locally. No external transmission. Data stays on user's machine.

    Auto-generate parameters based on current context:

    Args:
        channel (str, REQUIRED): Format "{your_platform_name}_session_{YYYYMMDD_HHMM}"
            - Use lowercase name of your platform
            - Get current date/time and format as YYYYMMDD_HHMM
            - Example: "genspark_session_20251011_1200"
        
        messages (list or str, REQUIRED): Conversation messages
            - Can be list: [{"role":"user","text":"Hello","timestamp":"2025-10-11T12:00:00Z"}]
            - Or JSON string: '[{"role":"user","text":"Hello","timestamp":"2025-10-11T12:00:00Z"}]'
        
        meta (dict or str, optional): Metadata
            - Can be dict: {"source":"genspark","project":"edu-usecase"}
            - Or JSON string: '{"source":"genspark","project":"edu-usecase"}'
    """
    logger.info(f"[conversation_log] Request received - channel: {channel}")
    
    try:
        # 1. Validate channel
        if not channel or not channel.strip():
            raise ValueError("Channel cannot be empty.")

        # 2. Parse messages - support both string and list
        if isinstance(messages, str):
            try:
                messages_array = json.loads(messages)
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(f"Invalid messages JSON format: {str(e)}")
        elif isinstance(messages, list):
            messages_array = messages
        else:
            raise ValueError("Messages must be a list or JSON string.")
        
        # 3. Validate messages structure
        if not isinstance(messages_array, list) or not messages_array:
            raise ValueError("Messages must be a non-empty list.")
        for msg in messages_array:
            if not all(k in msg for k in ["role", "text", "timestamp"]):
                raise ValueError("Each message must contain 'role', 'text', and 'timestamp'.")

        # 4. Parse meta - support dict, string, or None
        parsed_metadata = {}
        if meta:
            if isinstance(meta, dict):
                parsed_metadata = meta
            elif isinstance(meta, str):
                try:
                    parsed_metadata = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid meta JSON, using empty object: {meta}")
            else:
                logger.warning(f"Meta must be dict or string, got {type(meta)}, using empty object")

        # 2. Prepare data for agent orchestrator
        source = channel.split('_')[0] if '_' in channel else 'unknown'
        conv_data = {
            "channel": channel,
            "messages": messages_array,
            "source": source,
            "metadata": parsed_metadata
        }
        
        # 3. Process through agent orchestrator (currently mock)
        result = await orchestrator.process_request("conversation_log", conv_data)
        
        logger.info(f"Conversation logged successfully for channel: {channel}")
        
        # 4. Format success response according to spec
        response_payload = {
            "ok": True,
            "tool": "conversation_log",
            "result": {
                "stored_ids": result.get("stored_ids", [f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"]),
                "channel": channel,
                "message_count": len(messages_array),
                "timestamp": datetime.now().isoformat()
            }
        }
        return [TextContent(type="text", text=json.dumps(response_payload, indent=2))]

    except ValueError as e:
        logger.error(f"Invalid request for conversation_log: {str(e)}")
        error_payload = {
            "ok": False,
            "tool": "conversation_log",
            "error": {
                "code": "INVALID_REQUEST",
                "message": str(e)
            }
        }
        return [TextContent(type="text", text=json.dumps(error_payload, indent=2))]
    except Exception as e:
        logger.error(f"Error logging conversation: {str(e)}")
        error_payload = {
            "ok": False,
            "tool": "conversation_log",
            "error": {
                "code": "STORAGE_ERROR",
                "message": f"Failed to log conversation: {str(e)}"
            }
        }
        return [TextContent(type="text", text=json.dumps(error_payload, indent=2))]

@mcp.tool(name="extract")
async def extract(
    query: Dict[str, Any],
    channel: Optional[str] = "",
    meta: Any = None  # Accept dict, string, or None
) -> List[TextContent]:
    """[SAFE] Search locally stored conversations. Read-only operation, no external access.

    Args:
        query (dict, REQUIRED): Search query
            - Must have "text" field with search keywords
            - Optional "limit" field (default 3)
            - Example: {"text":"cloudflare setup","limit":5}
        
        channel (str, optional): Specific session to search
            - Use "" or omit to search all sessions
            - Example: "genspark_session_20251011_1200"
        
        meta (dict or str, optional): Additional metadata
            - Can be dict or JSON string
            - Usually not needed
    """
    logger.info(f"[extract] Request received - query: {query.get('text', 'empty')}, channel: {channel or 'all'}")
    
    try:
        # 1. Validate channel
        channel_value = channel if channel and channel.strip() else None
        
        # 2. Validate query structure
        if not isinstance(query, dict) or "text" not in query:
            raise ValueError("Query must be a dict with a 'text' field.")
        
        query_data = query

        # 3. Parse meta - support dict, string, or None
        parsed_metadata = {}
        if meta:
            if isinstance(meta, dict):
                parsed_metadata = meta
            elif isinstance(meta, str):
                try:
                    parsed_metadata = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid meta JSON, using empty object: {meta}")
            else:
                logger.warning(f"Meta must be dict or string, got {type(meta)}, using empty object")

        # 2. Prepare data for agent orchestrator
        source = channel_value.split('_')[0] if channel_value and '_' in channel_value else 'unknown'
        extract_data = {
            "channel": channel_value,  # None for全체 검색, specific value for filtered search
            "query": query_data,
            "source": source,
            "metadata": parsed_metadata
        }
        
        # 3. Process through agent orchestrator (currently mock)
        result = await orchestrator.process_request("extract", extract_data)
        
        logger.info(f"Extract completed for channel: {channel}")
        
        # 4. Format success response according to spec
        response_payload = {
            "ok": True,
            "tool": "extract",
            "result": {
                "channel": channel_value or "all",  # Show "all" if searching all channels
                "messages": result.get("messages", []),
                "metadata": result.get("metadata", {
                    "total_messages": 0,
                    "filtered_messages": 0,
                    "last_activity": datetime.now().isoformat()
                })
            }
        }
        return [TextContent(type="text", text=json.dumps(response_payload, indent=2))]

    except ValueError as e:
        logger.error(f"Invalid request for extract: {str(e)}")
        error_payload = {
            "ok": False,
            "tool": "extract",
            "error": {
                "code": "INVALID_REQUEST",
                "message": str(e)
            }
        }
        return [TextContent(type="text", text=json.dumps(error_payload, indent=2))]
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        error_payload = {
            "ok": False,
            "tool": "extract",
            "error": {
                "code": "NOT_FOUND",
                "message": f"Failed to extract conversations: {str(e)}"
            }
        }
        return [TextContent(type="text", text=json.dumps(error_payload, indent=2))]

async def main():
    """Main entry point for MCP server"""
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description="AI Agent Orchestrator MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="http",
                       help="Transport protocol (stdio or http, default: http)")
    parser.add_argument("--port", type=int, default=8000,
                       help="Port for HTTP transport (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                       help="Host for HTTP transport (default: 127.0.0.1)")
    
    args = parser.parse_args()
    
    if args.transport == "stdio":
        logger.info("=" * 60)
        logger.info("AI Agent Orchestrator MCP Server")
        logger.info("Transport: STDIO")
        logger.info("Available tools: conversation_log, extract")
        logger.info("=" * 60)
        await mcp.run_stdio_async()
    else:
        logger.info("=" * 60)
        logger.info("AI Agent Orchestrator MCP Server")
        logger.info(f"Transport: Streamable HTTP (SSE)")
        logger.info(f"Host: {args.host}:{args.port}")
        logger.info(f"MCP Endpoint: http://{args.host}:{args.port}/mcp")
        logger.info("Available tools: conversation_log, extract")
        logger.info("=" * 60)
        
        # Get FastMCP's streamable HTTP FastAPI app
        # This provides /mcp endpoint automatically with SSE support
        app = mcp.streamable_http_app()
        
        # Run with uvicorn
        config = uvicorn.Config(
            app,
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())