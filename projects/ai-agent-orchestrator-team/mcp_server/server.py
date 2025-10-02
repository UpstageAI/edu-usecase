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

@mcp.tool(
    name="conversation_log",
    description="Log conversation data to Context Registry via Agent Orchestrator"
)
async def conversation_log(
    channel: str,
    messages: str,  # JSON string of messages array
    meta: Optional[str] = None
) -> List[TextContent]:
    """
    Log conversation turns to the Context Registry through Agent Orchestrator.
    
    Args:
        channel: Channel identifier (format: {source}_session_{timestamp})
        messages: JSON string containing array of message objects with role, text, timestamp
        meta: Optional JSON string with additional metadata (can be empty {})
    """
    logger.info(f"[conversation_log] Request received - channel: {channel}")
    
    try:
        # 1. Validate inputs
        if not channel or not channel.strip():
            raise ValueError("Channel cannot be empty.")

        try:
            messages_array = json.loads(messages)
            if not isinstance(messages_array, list) or not messages_array:
                raise ValueError("Messages must be a non-empty list.")
            for msg in messages_array:
                if not all(k in msg for k in ["role", "text", "timestamp"]):
                    raise ValueError("Each message must contain 'role', 'text', and 'timestamp'.")
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"Invalid messages JSON format.")

        parsed_metadata = {}
        if meta:
            try:
                parsed_metadata = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid meta JSON, using empty object: {meta}")

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

@mcp.tool(
    name="extract",
    description="Extract conversations from Context Registry via Agent Orchestrator"
)
async def extract(
    channel: str,
    query: str,  # JSON string with text and optional limit
    meta: Optional[str] = None
) -> List[TextContent]:
    """
    Extract conversations from Context Registry using query text.
    
    Args:
        channel: Channel identifier to search in
        query: JSON string with text (search query) and optional limit
        meta: Optional JSON string with additional metadata (can be empty {})
    """
    logger.info(f"[extract] Request received - channel: {channel}, query: {query[:100]}...")
    
    try:
        # 1. Validate inputs
        if not channel or not channel.strip():
            raise ValueError("Channel cannot be empty.")

        try:
            query_data = json.loads(query)
            if not isinstance(query_data, dict) or "text" not in query_data:
                raise ValueError("Query must be a JSON object with a 'text' field.")
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"Invalid query JSON format.")

        parsed_metadata = {}
        if meta:
            try:
                parsed_metadata = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid meta JSON, using empty object: {meta}")

        # 2. Prepare data for agent orchestrator
        source = channel.split('_')[0] if '_' in channel else 'unknown'
        extract_data = {
            "channel": channel,
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
                "channel": channel,
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