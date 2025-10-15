#!/usr/bin/env python3
"""
Slack MCP Client - Uses MCP Protocol to communicate with Slack MCP Server
This connects to slack-mcp-server (by korotovsky) via stdio
"""

import os
import json
import csv
import io
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: MCP SDK not installed. Run: uv add mcp")

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlackMCPClient:
    """
    Client for communicating with Slack MCP Server via MCP Protocol

    This uses the slack-mcp-server package (by korotovsky)
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Slack MCP Client

        Args:
            token: Slack user token (or from env SLACK_MCP_XOXP_TOKEN)
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed. Run: uv add mcp")

        self.token = token or os.environ.get("SLACK_MCP_XOXP_TOKEN")

        if not self.token:
            raise ValueError("SLACK_MCP_XOXP_TOKEN must be provided or set in environment")

        # Server parameters for stdio connection
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "slack-mcp-server"],
            env={
                "SLACK_MCP_XOXP_TOKEN": self.token
            }
        )

        logger.info("Slack MCP Client initialized")

    @asynccontextmanager
    async def _get_session(self):
        """
        Create MCP client session (context manager)

        Usage:
            async with client._get_session() as session:
                result = await session.call_tool(...)
        """
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                logger.info("MCP session established with Slack server")

                # Wait a bit for Slack MCP server to sync cache on first run
                import asyncio
                await asyncio.sleep(5)

                yield session

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools from Slack MCP Server

        Returns:
            List of tool definitions
        """
        try:
            async with self._get_session() as session:
                tools = await session.list_tools()

                logger.info(f"Found {len(tools.tools)} available tools")

                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools.tools
                ]
        except Exception as e:
            logger.error(f"Error listing tools: {str(e)}")
            raise

    async def list_channels(self) -> List[Dict[str, Any]]:
        """
        List all channels in Slack workspace

        Returns:
            List of channel information
        """
        try:
            async with self._get_session() as session:
                result = await session.call_tool(
                    "channels_list",
                    arguments={}
                )

                # Debug logging
                logger.info(f"MCP result type: {type(result)}")

                if result.content:
                    content = result.content[0].text if result.content else ""

                    if not content or content.strip() == "":
                        logger.warning("Empty content from MCP server")
                        return []

                    # Parse CSV format (korotovsky/slack-mcp-server returns CSV)
                    # Format: ID,Name,Topic,Purpose,MemberCount,Cursor
                    channels = []
                    csv_reader = csv.DictReader(io.StringIO(content))

                    for row in csv_reader:
                        channel = {
                            "id": row.get("ID", ""),
                            "name": row.get("Name", "").lstrip("#"),
                            "topic": row.get("Topic", ""),
                            "purpose": row.get("Purpose", ""),
                            "member_count": int(row.get("MemberCount", "0") or "0"),
                            "is_member": True  # Assuming listed channels are joined
                        }
                        channels.append(channel)

                    logger.info(f"Found {len(channels)} channels")
                    return channels

                return []

        except csv.Error as e:
            logger.error(f"CSV parse error: {str(e)}")
            logger.error(f"Content that failed to parse: {content if 'content' in locals() else 'N/A'}")
            raise
        except Exception as e:
            logger.error(f"Error listing channels: {str(e)}")
            raise

    async def get_conversation_history(
        self,
        channel_id: str,
        limit: int = 50,
        oldest: Optional[str] = None,
        latest: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history from a channel or DM

        Args:
            channel_id: Channel or conversation ID
            limit: Number of messages to fetch (default 50)
            oldest: Only messages after this Unix timestamp
            latest: Only messages before this Unix timestamp

        Returns:
            List of messages
        """
        try:
            async with self._get_session() as session:
                limit_str = f"{limit}m" if isinstance(limit, int) else str(limit)
                arguments = {"channel_id": channel_id, "limit": limit_str}
                logger.info(f"Fetching conversation history for channel {channel_id}")

                result = await session.call_tool("conversations_history", arguments=arguments)

                if result.content and result.content[0].text:
                    content = result.content[0].text.strip()
                    if content:
                        messages = list(csv.DictReader(io.StringIO(content)))
                        logger.info(f"Fetched {len(messages)} messages from {channel_id} (parsed from CSV)")
                        return messages

                logger.info(f"No messages found or empty response for channel {channel_id}")
                return []
        except csv.Error as e:
            logger.error(f"CSV parse error in get_conversation_history: {e}")
            logger.error(f"Content that failed to parse: {result.content[0].text if result.content else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"Error fetching conversation history: {str(e)}")
            raise

    async def search_messages(
        self,
        query: str,
        count: int = 20,
        sort: str = "timestamp",
        sort_dir: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Search messages in Slack workspace

        Args:
            query: Search query string (supports Slack search modifiers)
            count: Number of results (default 20)
            sort: Sort by 'timestamp' or 'score' (default timestamp)
            sort_dir: Sort direction 'asc' or 'desc' (default desc)

        Returns:
            List of matching messages
        """
        try:
            async with self._get_session() as session:
                arguments = {"search_query": query, "limit": count}
                logger.info(f"Searching messages with query: {query}")

                result = await session.call_tool("conversations_search_messages", arguments=arguments)

                if result.content and result.content[0].text:
                    content = result.content[0].text.strip()

                    if content:
                        messages = list(csv.DictReader(io.StringIO(content)))
                        logger.info(f"Found {len(messages)} matching messages (parsed from CSV)")
                        return messages

                logger.info(f"No search results or empty response for query: {query}")
                return []
        except csv.Error as e:
            logger.error(f"CSV parse error in search_messages: {e}")
            logger.error(f"Content that failed to parse: {result.content[0].text if result.content else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"Error searching messages: {str(e)}")
            raise

    async def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get replies from a thread

        Args:
            channel_id: Channel ID containing the thread
            thread_ts: Thread timestamp (parent message ts)
            limit: Number of replies to fetch

        Returns:
            List of thread messages
        """
        try:
            async with self._get_session() as session:
                limit_str = f"{limit}m" if isinstance(limit, int) else str(limit)
                arguments = {"channel_id": channel_id, "thread_ts": thread_ts, "limit": limit_str}
                logger.info(f"Fetching thread replies for {thread_ts} in {channel_id}")

                result = await session.call_tool("conversations_replies", arguments=arguments)

                if result.content and result.content[0].text:
                    content = result.content[0].text.strip()
                    if content:
                        messages = list(csv.DictReader(io.StringIO(content)))
                        logger.info(f"Fetched {len(messages)} thread replies (parsed from CSV)")
                        return messages

                logger.info(f"No replies found or empty response for thread {thread_ts}")
                return []
        except csv.Error as e:
            logger.error(f"CSV parse error in get_thread_replies: {e}")
            logger.error(f"Content that failed to parse: {result.content[0].text if result.content else 'N/A'}")
            return []

    async def fetch_recent_mentions_and_dms(
        self,
        hours: int = 24
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch recent mentions and direct messages

        Since search API doesn't work reliably, we fetch recent messages from all channels
        and filter for mentions (messages containing <@USER_ID>)

        Args:
            hours: Fetch messages from the last N hours (default 24)

        Returns:
            Dictionary with 'mentions' and 'dms' lists
        """
        try:
            import time

            all_mentions = []
            cutoff_timestamp = time.time() - (hours * 3600)

            # Get all channels
            channels = await self.list_channels()
            logger.info(f"Checking {len(channels)} channels for mentions")

            # Check each channel for recent messages with mentions
            for channel in channels:
                try:
                    # Fetch recent messages from this channel
                    messages = await self.get_conversation_history(
                        channel['id'],
                        limit=50  # Last 50 messages per channel
                    )

                    # Filter messages:
                    # 1. Within time range
                    # 2. Contains mention syntax <@USER_ID>
                    for msg in messages:
                        try:
                            msg_text = msg.get('Text', '')
                            time_str = msg.get('Time', '')

                            # Parse timestamp - can be Unix timestamp or ISO 8601
                            msg_time = 0
                            if time_str:
                                try:
                                    # Try Unix timestamp first
                                    msg_time = float(time_str)
                                except ValueError:
                                    # Try ISO 8601 format (2025-10-02T00:38:31Z)
                                    from datetime import datetime
                                    try:
                                        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                                        msg_time = dt.timestamp()
                                    except ValueError:
                                        logger.warning(f"Could not parse timestamp: {time_str}")
                                        continue

                            # Check if message is recent and contains a mention
                            # Slack MCP server may return mentions as:
                            # - <@USER_ID> format
                            # - Plain USER_ID at start of message (U followed by alphanumeric)
                            has_mention = '<@' in msg_text or (msg_text.startswith('U') and len(msg_text.split()[0]) > 5)

                            if msg_time > cutoff_timestamp and has_mention:
                                # Add channel info to message
                                msg['channel_name'] = channel['name']
                                msg['channel_id'] = channel['id']
                                all_mentions.append(msg)

                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error parsing message: {e}")
                            continue

                    # Count mentions found in this channel
                    mention_count = len([m for m in all_mentions if m.get('channel_id') == channel['id']])
                    logger.info(f"Channel #{channel['name']}: found {mention_count} mentions out of {len(messages)} messages")

                except Exception as e:
                    logger.warning(f"Error checking channel #{channel.get('name', 'unknown')}: {e}")
                    continue

            logger.info(f"Found {len(all_mentions)} total mentions in last {hours} hours across all channels")

            return {
                "mentions": all_mentions,
                "dms": []  # Placeholder - DM detection requires different approach
            }

        except Exception as e:
            logger.error(f"Error fetching mentions and DMs: {str(e)}")
            raise

    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Slack message into simplified structure

        Args:
            message: Raw Slack message object

        Returns:
            Simplified message dictionary
        """
        try:
            return {
                "ts": message.get("ts", ""),
                "user": message.get("user", ""),
                "text": message.get("text", ""),
                "type": message.get("type", ""),
                "channel": message.get("channel", {}).get("id") if isinstance(message.get("channel"), dict) else message.get("channel", ""),
                "channel_name": message.get("channel", {}).get("name") if isinstance(message.get("channel"), dict) else "",
                "permalink": message.get("permalink", ""),
                "timestamp": message.get("ts", "")
            }
        except Exception as e:
            logger.warning(f"Failed to parse message: {str(e)}")
            return {}


# Convenience function for Agent Orchestrator
async def fetch_slack_data_via_mcp(hours: int = 24) -> Dict[str, Any]:
    """
    Convenience function to fetch Slack data via MCP

    Args:
        hours: Fetch data from the last N hours (default 24)

    Returns:
        Dictionary with mentions and DMs
    """
    try:
        client = SlackMCPClient()
        data = await client.fetch_recent_mentions_and_dms(hours)

        logger.info(f"Fetched Slack data: {len(data.get('mentions', []))} mentions, {len(data.get('dms', []))} DMs")
        return data

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return {"mentions": [], "dms": []}
    except Exception as e:
        logger.error(f"Error fetching Slack data via MCP: {str(e)}")
        return {"mentions": [], "dms": []}