#!/usr/bin/env python3
"""
Gmail MCP Client - Uses MCP Protocol to communicate with Gmail MCP Server
This connects to @gongrzhe/server-gmail-autoauth-mcp via stdio
"""

import os
import json
import logging
import re
from html import unescape
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

class GmailMCPClient:
    """
    Client for communicating with Gmail MCP Server via MCP Protocol
    """

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Gmail MCP Client

        Args:
            credentials_path: Path to Google OAuth credentials JSON file
                              (or from env GMAIL_CREDENTIALS)
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed. Run: uv add mcp")

        self.credentials_path = credentials_path or os.environ.get("GMAIL_CREDENTIALS")

        if not self.credentials_path or not os.path.exists(self.credentials_path):
            raise ValueError(
                "GMAIL_CREDENTIALS path must be provided or set in environment, "
                "and the file must exist."
            )

        logger.info(f"Gmail credentials loaded from: {self.credentials_path}")

        # Server parameters for stdio connection
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
            env={
                "GMAIL_CREDENTIALS": self.credentials_path,
                "GMAIL_TOKEN_PATH": os.environ.get("GMAIL_TOKEN_PATH")
            }
        )

        logger.info("Gmail MCP Client initialized")

    @asynccontextmanager
    async def _get_session(self):
        """Create MCP client session (context manager)"""
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info("MCP session established with Gmail server")
                yield session

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from Gmail MCP Server"""
        try:
            async with self._get_session() as session:
                tools = await session.list_tools()
                logger.info(f"Found {len(tools.tools)} available tools")
                return [{"name": tool.name, "description": tool.description} for tool in tools.tools]
        except Exception as e:
            logger.error(f"Error listing tools: {str(e)}")
            raise

    async def search_emails(
        self,
        query: str,
        max_results: int = 20,
        include_spam_trash: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for emails matching a query.

        Args:
            query: Gmail search query (e.g., 'is:unread in:inbox')
            max_results: Maximum number of emails to return
            include_spam_trash: Whether to include spam/trash in results

        Returns:
            List of email thread objects
        """
        try:
            async with self._get_session() as session:
                arguments = {
                    "query": query,
                    "maxResults": max_results,
                    "includeSpamTrash": include_spam_trash,
                }
                logger.info(f"Searching emails with query: {query}")
                result = await session.call_tool("search_emails", arguments=arguments)

                if result.content and result.content[0].text:
                    content = result.content[0].text.strip()
                    if content:
                        try:
                            data = json.loads(content)
                            threads = data.get("threads", [])
                            logger.info(f"Found {len(threads)} email threads")
                            return threads
                        except json.JSONDecodeError:
                            # Gmail MCP server returns text format, not JSON
                            logger.info("Response is in text format, parsing as key-value pairs")
                            logger.info(f"DEBUG: Raw Gmail MCP response (first 500 chars):\n{content[:500]}")
                            threads = self._parse_text_response(content)
                            logger.info(f"Parsed {len(threads)} email threads from text format")
                            if threads:
                                logger.info(f"DEBUG: First parsed thread: {threads[0]}")
                            return threads

                logger.info("No emails found for the query.")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in search_emails: {e}")
            logger.error(f"Content that failed to parse: {result.content[0].text if result.content else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"Error searching emails: {str(e)}")
            raise

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """
        Read a specific email by message ID to get full content including body.

        Args:
            message_id: Gmail message ID

        Returns:
            Full email data including body
        """
        try:
            async with self._get_session() as session:
                # Note: Gmail MCP server expects camelCase 'messageId', not 'message_id'
                arguments = {"messageId": message_id}
                logger.info(f"Reading email: {message_id}")
                result = await session.call_tool("read_email", arguments=arguments)

                if result.content and result.content[0].text:
                    content = result.content[0].text.strip()
                    if content:
                        try:
                            # Try JSON first
                            data = json.loads(content)
                            return data
                        except json.JSONDecodeError:
                            # Parse text format
                            parsed = self._parse_single_email_text(content)
                            return parsed

                logger.warning(f"No content returned for email {message_id}")
                return {}

        except Exception as e:
            logger.error(f"Error reading email {message_id}: {str(e)}")
            raise

    def _parse_single_email_text(self, text: str) -> Dict[str, Any]:
        """
        Parse a single email's text format response into a structured dict.

        Format from Gmail MCP:
        Thread ID: 1999b6fbc1884a7e
        Subject: 보안 알림
        From: Google <no-reply@accounts.google.com>
        To: user@example.com
        Date: Tue, 30 Sep 2025 16:23:34 GMT

        [email body starts here, no "Body:" header]

        Returns:
            Email dictionary with all fields including body
        """
        email_data = {}
        body_lines = []
        in_body = False

        # Known header fields (case-insensitive)
        header_fields = {'thread id', 'subject', 'from', 'to', 'date', 'cc', 'bcc'}

        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Check if line is a header (key: value format)
            if ':' in line and not line.startswith(' ') and not in_body:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower()
                    value = parts[1].strip()

                    # If it's a known header field, store it
                    if key in header_fields:
                        email_data[key] = value
                        continue

            # If we've passed all headers and hit an empty line, body starts next
            if not in_body and line.strip() == '' and email_data:
                # Empty line after headers = body starts
                in_body = True
                continue

            # Collect body lines
            if in_body or (email_data and line.strip() and ':' not in line[:20]):
                in_body = True
                body_lines.append(line)

        # Combine body
        if body_lines:
            email_data['body'] = '\n'.join(body_lines).strip()
        else:
            email_data['body'] = ''

        return email_data

    def _clean_email_body(self, body: str) -> str:
        """
        Clean and normalize email body text by removing HTML tags and normalizing whitespace.

        This method handles:
        1. HTML tag removal (including self-closing tags and attributes)
        2. HTML entity decoding (&nbsp;, &amp;, etc.)
        3. Whitespace normalization (\\r\\n → \\n, excessive blank lines)
        4. URL preservation (keeps https:// links intact)
        5. Email structure preservation (keeps important line breaks)

        Args:
            body: Raw email body text (may contain HTML)

        Returns:
            Cleaned plain text suitable for LLM processing
        """
        if not body:
            return ""

        text = body

        # 1. Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

        # 2. Remove <script> and <style> tags with their content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # 3. Remove HTML tags but preserve structure
        # Keep line breaks for block-level elements
        block_elements = ['div', 'p', 'br', 'tr', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        for elem in block_elements:
            # Opening tags
            text = re.sub(f'<{elem}[^>]*>', '\n', text, flags=re.IGNORECASE)
            # Closing tags
            text = re.sub(f'</{elem}>', '\n', text, flags=re.IGNORECASE)

        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # 4. Decode HTML entities (&nbsp; &amp; &lt; &gt; etc.)
        text = unescape(text)

        # 5. Normalize line breaks: \r\n → \n
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')

        # 6. Remove excessive blank lines (3+ → 2)
        # Preserve paragraph structure by keeping up to 2 consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 7. Clean up spaces around line breaks
        # Remove trailing spaces before newlines
        text = re.sub(r' +\n', '\n', text)
        # Remove leading spaces after newlines (except for intentional indentation)
        text = re.sub(r'\n +', '\n', text)

        # 8. Normalize multiple spaces to single space (within lines)
        text = re.sub(r'[ \t]+', ' ', text)

        # 9. Strip leading/trailing whitespace from entire text
        text = text.strip()

        return text

    def _parse_text_response(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse Gmail MCP text format response into thread objects.

        Format example:
        ID: 1999b6fbc1884a7e
        Subject: 보안 알림
        From: Google <no-reply@accounts.google.com>
        Date: Tue, 30 Sep 20

        Returns:
            List of thread-like dictionaries with messages
        """
        threads = []
        current_email = {}

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                # Empty line marks end of an email
                if current_email:
                    # Convert to thread format with messages array
                    thread = {
                        "id": current_email.get("id", ""),
                        "messages": [{
                            "id": current_email.get("id", ""),
                            "threadId": current_email.get("id", ""),
                            "snippet": current_email.get("snippet", ""),
                            "payload": {
                                "headers": [
                                    {"name": "Subject", "value": current_email.get("subject", "")},
                                    {"name": "From", "value": current_email.get("from", "")},
                                    {"name": "Date", "value": current_email.get("date", "")}
                                ]
                            }
                        }]
                    }
                    threads.append(thread)
                    current_email = {}
                continue

            # Parse key: value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                current_email[key] = value

        # Don't forget last email if no trailing newline
        if current_email:
            thread = {
                "id": current_email.get("id", ""),
                "messages": [{
                    "id": current_email.get("id", ""),
                    "threadId": current_email.get("id", ""),
                    "snippet": current_email.get("snippet", ""),
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": current_email.get("subject", "")},
                            {"name": "From", "value": current_email.get("from", "")},
                            {"name": "Date", "value": current_email.get("date", "")}
                        ]
                    }
                }]
            }
            threads.append(thread)

        return threads

    async def fetch_urgent_emails(self, hours: int = 24, include_body: bool = True) -> List[Dict[str, Any]]:
        """
        Fetches emails considered urgent from the last N hours.
        Urgent is defined as 'is:important' or 'is:unread'.

        Args:
            hours: Look back period in hours.
            include_body: Whether to fetch full email body (slower but more complete)

        Returns:
            A list of simplified email objects with optional body content.
        """
        import datetime

        time_delta = datetime.timedelta(hours=hours)
        since_date = (datetime.datetime.now() - time_delta).strftime('%Y/%m/%d')

        query = f"(is:important OR is:unread) after:{since_date}"

        logger.info(f"Fetching urgent emails with query: {query}")

        threads = await self.search_emails(query=query, max_results=50)

        emails = []
        logger.info(f"DEBUG: Processing {len(threads)} threads to extract emails")
        for thread in threads:
            logger.info(f"DEBUG: Thread structure keys: {thread.keys() if isinstance(thread, dict) else 'not a dict'}")
            # The gmail mcp server returns message data inside the 'messages' key of a thread
            for message in thread.get('messages', []):
                headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
                email = {
                    "id": message.get("id"),
                    "threadId": message.get("threadId"),
                    "snippet": message.get("snippet"),
                    "subject": headers.get("Subject", "No Subject"),
                    "from": headers.get("From", "Unknown Sender"),
                    "date": headers.get("Date", ""),
                }

                # Fetch full body if requested
                if include_body and email["id"]:
                    try:
                        full_email = await self.read_email(email["id"])
                        raw_body = full_email.get("body", "")
                        # Clean HTML and normalize text
                        email["body"] = self._clean_email_body(raw_body)
                        logger.info(f"Fetched and cleaned body for email {email['id'][:8]}... (raw: {len(raw_body)} chars → cleaned: {len(email['body'])} chars)")
                    except Exception as e:
                        logger.warning(f"Failed to fetch body for email {email['id']}: {str(e)}")
                        email["body"] = ""

                emails.append(email)

        logger.info(f"Processed {len(emails)} urgent emails from {len(threads)} threads.")
        return emails

async def main():
    """For testing the client directly"""
    try:
        client = GmailMCPClient()
        print("Gmail MCP Client initialized.")
        
        tools = await client.list_available_tools()
        print("Available tools:", [tool['name'] for tool in tools])

        print("\nFetching urgent emails from last 24 hours...")
        urgent_emails = await client.fetch_urgent_emails(hours=24)
        
        if urgent_emails:
            print(f"Found {len(urgent_emails)} urgent emails:")
            for i, email in enumerate(urgent_emails[:5], 1):
                print(f"  {i}. From: {email['from']}")
                print(f"     Subject: {email['subject']}")
                print(f"     Snippet: {email['snippet'][:80]}...")
        else:
            print("No urgent emails found.")

    except ValueError as e:
        print(f"\n[ERROR] Configuration error: {e}")
        print("Please ensure the GMAIL_CREDENTIALS environment variable is set correctly.")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
