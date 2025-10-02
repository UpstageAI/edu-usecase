#!/usr/bin/env python3
"""
Notion MCP Client - Uses MCP Protocol to communicate with Notion MCP Server
This connects to @notionhq/notion-mcp-server via stdio
"""

import os
import json
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


class NotionMCPClient:
    """
    Client for communicating with Notion MCP Server via MCP Protocol

    This uses the official @notionhq/notion-mcp-server package
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Notion MCP Client

        Args:
            api_key: Notion API key (or from env NOTION_API_KEY)
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed. Run: uv add mcp")

        self.api_key = api_key or os.environ.get("NOTION_API_KEY")

        if not self.api_key:
            raise ValueError("NOTION_API_KEY must be provided or set in environment")

        # Server parameters for stdio connection
        # Try both NOTION_API_KEY and NOTION_TOKEN
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env={
                "NOTION_API_KEY": self.api_key,
                "NOTION_TOKEN": self.api_key  # Some MCP servers use this
            }
        )

        logger.info("Notion MCP Client initialized")

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

                logger.info("MCP session established with Notion server")
                yield session

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools from Notion MCP Server

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

    async def search_notion(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search Notion pages/databases using MCP search tool

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search results
        """
        try:
            async with self._get_session() as session:
                result = await session.call_tool(
                    "API-post-search",
                    arguments={
                        "query": query,
                        "page_size": limit
                    }
                )

                # Parse result
                if result.content:
                    # MCP returns TextContent objects
                    content = result.content[0].text if result.content else "{}"
                    data = json.loads(content)

                    logger.info(f"Search returned {len(data.get('results', []))} results")
                    return data.get("results", [])

                return []

        except Exception as e:
            logger.error(f"Error searching Notion: {str(e)}")
            raise

    async def fetch_page(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch a specific Notion page by ID

        Args:
            page_id: Notion page ID

        Returns:
            Page data
        """
        try:
            async with self._get_session() as session:
                result = await session.call_tool(
                    "API-retrieve-a-page",
                    arguments={"page_id": page_id}
                )

                if result.content:
                    content = result.content[0].text if result.content else "{}"
                    data = json.loads(content)

                    logger.info(f"Fetched page: {page_id}")
                    return data

                return {}

        except Exception as e:
            logger.error(f"Error fetching page {page_id}: {str(e)}")
            raise

    async def query_database(self, database_id: str, filter_obj: Optional[Dict] = None,
                            sorts: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """
        Query a Notion database using MCP

        Args:
            database_id: Notion database ID
            filter_obj: Filter object (Notion API format)
            sorts: Sort array (Notion API format)

        Returns:
            List of database pages
        """
        try:
            async with self._get_session() as session:
                arguments = {"database_id": database_id}

                if filter_obj:
                    arguments["filter"] = filter_obj

                if sorts:
                    arguments["sorts"] = sorts

                # Debug logging
                logger.info(f"Calling API-post-database-query with arguments: {arguments}")

                result = await session.call_tool(
                    "API-post-database-query",
                    arguments=arguments
                )

                # Debug logging
                logger.info(f"MCP result type: {type(result)}")
                logger.info(f"MCP result content: {result.content if hasattr(result, 'content') else 'No content attr'}")

                if result.content:
                    content = result.content[0].text if result.content else "{}"
                    logger.info(f"Raw content from MCP: {content[:200]}...")
                    data = json.loads(content)

                    results = data.get("results", [])
                    logger.info(f"Database query returned {len(results)} pages")
                    return results

                return []

        except Exception as e:
            logger.error(f"Error querying database {database_id}: {str(e)}")
            raise

    async def fetch_pending_tasks(self, database_id: str) -> List[Dict[str, Any]]:
        """
        Fetch pending tasks (Status != Done) from Notion database

        Args:
            database_id: Notion database ID

        Returns:
            List of pending tasks with simplified structure
        """
        try:
            # Query with filter for non-Done tasks
            filter_obj = {
                "property": "Status",
                "status": {
                    "does_not_equal": "Done"
                }
            }

            sorts = [
                {
                    "property": "Priority",
                    "direction": "ascending"
                }
            ]

            pages = await self.query_database(database_id, filter_obj, sorts)

            # Parse and simplify task data
            tasks = []
            for page in pages:
                task = self._parse_task_page(page)
                if task:
                    tasks.append(task)

            logger.info(f"Found {len(tasks)} pending tasks")
            return tasks

        except Exception as e:
            logger.error(f"Error fetching pending tasks: {str(e)}")
            raise

    async def create_page(self, parent_id: str, title: str,
                         properties: Optional[Dict] = None,
                         children: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Create a new page in Notion (e.g., for daily briefing)

        Args:
            parent_id: Parent page or database ID
            title: Page title
            properties: Page properties
            children: Page content blocks

        Returns:
            Created page data
        """
        try:
            async with self._get_session() as session:
                arguments = {
                    "parent": {"page_id": parent_id},
                    "properties": {
                        "title": {
                            "title": [{"text": {"content": title}}]
                        }
                    }
                }

                if properties:
                    arguments["properties"].update(properties)

                if children:
                    arguments["children"] = children

                result = await session.call_tool(
                    "API-post-page",
                    arguments=arguments
                )

                if result.content:
                    content = result.content[0].text if result.content else "{}"
                    data = json.loads(content)

                    logger.info(f"Created page: {title}")
                    return data

                return {}

        except Exception as e:
            logger.error(f"Error creating page: {str(e)}")
            raise

    def _parse_task_page(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a Notion page into simplified task structure

        Args:
            page: Raw Notion page object

        Returns:
            Simplified task dictionary
        """
        try:
            properties = page.get("properties", {})

            # Extract title
            title = ""
            title_prop = properties.get("Name", {})
            if title_prop.get("type") == "title":
                title_array = title_prop.get("title", [])
                if title_array:
                    title = title_array[0].get("plain_text", "")

            # Extract status
            status = ""
            status_prop = properties.get("Status", {})
            if status_prop.get("type") == "status":
                status_obj = status_prop.get("status", {})
                status = status_obj.get("name", "")

            # Extract priority
            priority = ""
            priority_prop = properties.get("Priority", {})
            if priority_prop.get("type") == "select":
                priority_obj = priority_prop.get("select", {})
                if priority_obj:
                    priority = priority_obj.get("name", "")

            # Extract due date
            due_date = None
            due_prop = properties.get("Due Date", {})
            if due_prop.get("type") == "date":
                date_obj = due_prop.get("date", {})
                if date_obj:
                    due_date = date_obj.get("start", "")

            return {
                "id": page.get("id", ""),
                "title": title,
                "status": status,
                "priority": priority,
                "due_date": due_date,
                "url": page.get("url", ""),
                "created_time": page.get("created_time", ""),
                "last_edited_time": page.get("last_edited_time", "")
            }

        except Exception as e:
            logger.warning(f"Failed to parse task page: {str(e)}")
            return None


# Convenience function for Agent Orchestrator
async def fetch_notion_data_via_mcp() -> List[Dict[str, Any]]:
    """
    Convenience function to fetch Notion data via MCP

    Returns:
        List of pending tasks
    """
    try:
        database_id = os.environ.get("NOTION_DATABASE_ID")
        if not database_id:
            logger.error("NOTION_DATABASE_ID not set")
            return []

        client = NotionMCPClient()
        return await client.fetch_pending_tasks(database_id)

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error fetching Notion data via MCP: {str(e)}")
        return []