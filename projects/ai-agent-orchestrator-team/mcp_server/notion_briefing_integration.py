#!/usr/bin/env python3
"""
Notion Daily Briefing Integration

Integrates the collected daily briefing data with Notion page creation.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from mcp_server.notion_formatter import (
    create_briefing_markdown,
    markdown_to_notion_blocks
)
from mcp_server.notion_mcp_client import NotionMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_daily_briefing_page(
    collected_data: Dict[str, Any],
    parent_page_id: str,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a Daily Briefing page in Notion

    Args:
        collected_data: Data from daily_briefing_collector
                       (includes data.gmail, data.slack, data.notion)
        parent_page_id: Notion parent page ID where briefing will be created
        date: Target date (YYYY-MM-DD), defaults to today

    Returns:
        {
            "status": "success" | "error",
            "page_url": "https://notion.so/...",
            "page_id": "abc123-...",
            "created_at": "2025-09-29T07:02:30+09:00",
            "error": None | "error message"
        }

    Example:
        >>> collected = await collect_daily_briefing_data(hours=24)
        >>> result = await create_daily_briefing_page(
        ...     collected_data=collected,
        ...     parent_page_id="your-notion-page-id"
        ... )
        >>> print(result["page_url"])
        https://notion.so/workspace/daily-briefing-20250929
    """
    try:
        # 1️⃣ 날짜 설정
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Creating Daily Briefing page for {date}")

        # 2️⃣ Markdown 브리핑 생성
        logger.info("Generating briefing markdown...")
        markdown_text = create_briefing_markdown(collected_data)
        logger.info(f"Generated markdown ({len(markdown_text)} chars)")

        # 3️⃣ Notion 블록으로 변환
        logger.info("Converting markdown to Notion blocks...")
        blocks = markdown_to_notion_blocks(markdown_text)
        logger.info(f"Generated {len(blocks)} Notion blocks")

        # 4️⃣ 페이지 제목 생성
        # 날짜를 한국어 형식으로 변환: "2025-09-29" → "2025년 9월 29일"
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        title = f"📅 Daily Briefing - {date_obj.year}년 {date_obj.month}월 {date_obj.day}일"

        logger.info(f"Creating Notion page: {title}")

        # 5️⃣ Notion MCP Client로 페이지 생성
        client = NotionMCPClient()

        # Notion API 페이지 생성 요청
        page_data = await client.create_page(
            parent_id=parent_page_id,
            title=title,
            children=blocks
        )

        # 6️⃣ 결과 반환
        # Debug: Notion API 응답 확인
        import json
        logger.info(f"DEBUG: Notion API response keys: {list(page_data.keys())}")
        logger.info(f"DEBUG: Full response: {json.dumps(page_data, indent=2, ensure_ascii=False)[:500]}")

        page_url = page_data.get("url", "")
        page_id = page_data.get("id", "")

        # URL이 없으면 page_id로부터 생성
        if not page_url and page_id:
            # Notion URL 형식: https://www.notion.so/{page_id with hyphens removed}
            clean_id = page_id.replace("-", "")
            page_url = f"https://www.notion.so/{clean_id}"
            logger.info(f"Generated URL from page_id: {page_url}")

        logger.info(f"✅ Briefing page created: {page_url}")

        return {
            "status": "success",
            "page_url": page_url,
            "page_id": page_id,
            "created_at": datetime.now().isoformat(),
            "error": None
        }

    except Exception as e:
        logger.error(f"Failed to create briefing page: {str(e)}")
        return {
            "status": "error",
            "page_url": None,
            "page_id": None,
            "created_at": datetime.now().isoformat(),
            "error": str(e)
        }
