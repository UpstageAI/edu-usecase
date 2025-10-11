#!/usr/bin/env python3
"""
Daily Briefing Data Collector

Collects data from multiple MCP clients (Gmail, Slack, Notion) in parallel
for the Daily Briefing scenario.

This module provides a unified interface for Agent Orchestrator to fetch
all necessary data for daily briefing generation.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import MCP clients
from mcp_server.gmail_mcp_client import GmailMCPClient
from mcp_server.slack_mcp_client import SlackMCPClient
from mcp_server.notion_mcp_client import NotionMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def collect_daily_briefing_data(
    hours: int = 24,
    notion_database_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Collect daily briefing data from multiple MCP sources in parallel.

    This function orchestrates parallel data collection from:
    - Gmail: Urgent/important emails
    - Slack: Recent mentions and DMs
    - Notion: Pending tasks

    Args:
        hours: Look back period in hours (default: 24)
        notion_database_id: Notion database ID for task tracking (optional)

    Returns:
        Dictionary containing all collected data with structure:
        {
            "timestamp": ISO timestamp,
            "period_hours": 24,
            "data": {
                "gmail": {
                    "emails": [...],
                    "count": N,
                    "status": "success" | "error",
                    "error": None | "error message"
                },
                "slack": {
                    "mentions": [...],
                    "dms": [...],
                    "count": N,
                    "status": "success" | "error",
                    "error": None | "error message"
                },
                "notion": {
                    "tasks": [...],
                    "count": N,
                    "status": "success" | "error",
                    "error": None | "error message"
                }
            },
            "summary": {
                "total_sources": 3,
                "successful_sources": N,
                "failed_sources": N
            }
        }
    """
    logger.info(f"Starting daily briefing data collection (period: {hours} hours)")

    # Prepare result structure
    result = {
        "timestamp": datetime.now().isoformat(),
        "period_hours": hours,
        "data": {},
        "summary": {
            "total_sources": 3,
            "successful_sources": 0,
            "failed_sources": 0
        }
    }

    # Collect data from all sources in parallel
    tasks = [
        _collect_gmail_data(hours),
        _collect_slack_data(hours),
        _collect_notion_data(notion_database_id)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    source_names = ["gmail", "slack", "notion"]
    for source_name, source_result in zip(source_names, results):
        if isinstance(source_result, Exception):
            logger.error(f"Failed to collect {source_name} data: {str(source_result)}")
            result["data"][source_name] = {
                "status": "error",
                "error": str(source_result),
                "count": 0
            }
            result["summary"]["failed_sources"] += 1
        else:
            result["data"][source_name] = source_result
            result["summary"]["successful_sources"] += 1

    logger.info(f"Data collection completed: {result['summary']['successful_sources']}/{result['summary']['total_sources']} sources successful")

    return result


async def _collect_gmail_data(hours: int) -> Dict[str, Any]:
    """
    Collect urgent emails from Gmail.

    Args:
        hours: Look back period in hours

    Returns:
        Dictionary with email data and metadata
    """
    try:
        logger.info("Collecting Gmail data...")
        client = GmailMCPClient()
        emails = await client.fetch_urgent_emails(hours=hours, include_body=True)

        return {
            "emails": emails,
            "count": len(emails),
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Gmail data collection failed: {str(e)}")
        raise


async def _collect_slack_data(hours: int) -> Dict[str, Any]:
    """
    Collect mentions and DMs from Slack.

    Args:
        hours: Look back period in hours

    Returns:
        Dictionary with Slack data and metadata
    """
    try:
        logger.info("Collecting Slack data...")
        client = SlackMCPClient()
        data = await client.fetch_recent_mentions_and_dms(hours=hours)

        mentions = data.get("mentions", [])
        dms = data.get("dms", [])

        return {
            "mentions": mentions,
            "dms": dms,
            "count": len(mentions) + len(dms),
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Slack data collection failed: {str(e)}")
        raise


async def _collect_notion_data(database_id: Optional[str]) -> Dict[str, Any]:
    """
    Collect pending tasks from Notion.

    Args:
        database_id: Notion database ID (optional)

    Returns:
        Dictionary with task data and metadata
    """
    try:
        logger.info("Collecting Notion data...")

        # If no database ID provided, skip Notion collection
        if not database_id:
            logger.warning("No Notion database ID provided, skipping Notion data collection")
            return {
                "tasks": [],
                "count": 0,
                "status": "skipped",
                "error": "No database ID provided"
            }

        client = NotionMCPClient()
        tasks = await client.fetch_pending_tasks(database_id=database_id)

        return {
            "tasks": tasks,
            "count": len(tasks),
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Notion data collection failed: {str(e)}")
        raise


async def main():
    """
    Test the daily briefing collector
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Get Notion database ID from environment (optional)
    notion_db_id = os.environ.get("NOTION_DATABASE_ID")

    print("=" * 80)
    print("Daily Briefing Data Collector Test")
    print("=" * 80)
    print(f"\nCollecting data from last 24 hours...")
    if notion_db_id:
        print(f"Notion Database ID: {notion_db_id[:8]}...{notion_db_id[-4:]}")
    else:
        print("Notion Database ID: Not provided (will skip Notion)")

    try:
        result = await collect_daily_briefing_data(hours=24, notion_database_id=notion_db_id)

        print("\n" + "=" * 80)
        print("COLLECTION SUMMARY")
        print("=" * 80)
        print(f"Timestamp: {result['timestamp']}")
        print(f"Period: {result['period_hours']} hours")
        print(f"Successful sources: {result['summary']['successful_sources']}/{result['summary']['total_sources']}")
        print(f"Failed sources: {result['summary']['failed_sources']}")

        # Gmail summary
        print("\n" + "-" * 80)
        print("GMAIL")
        print("-" * 80)
        gmail_data = result["data"].get("gmail", {})
        if gmail_data["status"] == "success":
            print(f"✅ Status: {gmail_data['status']}")
            print(f"📧 Emails collected: {gmail_data['count']}")
            if gmail_data['count'] > 0:
                print(f"\nFirst 3 emails:")
                for i, email in enumerate(gmail_data['emails'][:3], 1):
                    print(f"  {i}. From: {email['from']}")
                    print(f"     Subject: {email['subject']}")
                    print(f"     Body length: {len(email.get('body', ''))} chars")
        else:
            print(f"❌ Status: {gmail_data['status']}")
            print(f"Error: {gmail_data.get('error', 'Unknown error')}")

        # Slack summary
        print("\n" + "-" * 80)
        print("SLACK")
        print("-" * 80)
        slack_data = result["data"].get("slack", {})
        if slack_data["status"] == "success":
            print(f"✅ Status: {slack_data['status']}")
            print(f"💬 Mentions: {len(slack_data['mentions'])}")
            print(f"📩 DMs: {len(slack_data['dms'])}")
            print(f"📊 Total: {slack_data['count']}")
        else:
            print(f"❌ Status: {slack_data['status']}")
            print(f"Error: {slack_data.get('error', 'Unknown error')}")

        # Notion summary
        print("\n" + "-" * 80)
        print("NOTION")
        print("-" * 80)
        notion_data = result["data"].get("notion", {})
        if notion_data["status"] == "success":
            print(f"✅ Status: {notion_data['status']}")
            print(f"✓ Tasks collected: {notion_data['count']}")
        elif notion_data["status"] == "skipped":
            print(f"⏭️  Status: {notion_data['status']}")
            print(f"Reason: {notion_data.get('error', 'No database ID')}")
        else:
            print(f"❌ Status: {notion_data['status']}")
            print(f"Error: {notion_data.get('error', 'Unknown error')}")

        print("\n" + "=" * 80)
        print("Collection complete!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during collection: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
