#!/usr/bin/env python3
"""
Notion Briefing Formatter - Convert Markdown to Notion blocks

This module provides utilities to convert Markdown formatted text into
Notion API block format for creating Daily Briefing pages.
"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def markdown_to_notion_blocks(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Convert Markdown briefing text to Notion blocks.

    Supports:
    - Headings (# ## ###)
    - Bullet lists (-) with nested items (  -)
    - Numbered lists (1. 2. 3.)
    - Bold text (**text**)
    - Paragraphs

    Args:
        markdown_text: Markdown formatted briefing text

    Returns:
        List of Notion block objects

    Example:
        >>> markdown = "# Title\\n- Item 1"
        >>> blocks = markdown_to_notion_blocks(markdown)
        >>> len(blocks)
        2
    """
    blocks = []
    lines = markdown_text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Heading 1
        if stripped.startswith('# '):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:]}}]
                }
            })
            i += 1

        # Heading 2
        elif stripped.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[3:]}}]
                }
            })
            i += 1

        # Heading 3
        elif stripped.startswith('### '):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[4:]}}]
                }
            })
            i += 1

        # Bullet list (check for indentation)
        elif stripped.startswith('- '):
            # Check if this is a nested item (starts with spaces)
            indent_level = len(line) - len(line.lstrip())

            if indent_level > 0:
                # This is a nested item - add as child to previous block
                if blocks and blocks[-1]["type"] == "bulleted_list_item":
                    if "bulleted_list_item" not in blocks[-1]:
                        blocks[-1]["bulleted_list_item"] = {"rich_text": [], "children": []}

                    if "children" not in blocks[-1]["bulleted_list_item"]:
                        blocks[-1]["bulleted_list_item"]["children"] = []

                    blocks[-1]["bulleted_list_item"]["children"].append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": parse_rich_text(stripped[2:])
                        }
                    })
            else:
                # Top-level item
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": parse_rich_text(stripped[2:])
                    }
                })
            i += 1

        # Numbered list
        elif len(stripped) > 0 and stripped[0].isdigit() and '. ' in stripped[:5]:
            # Extract text after "1. "
            text = stripped.split('. ', 1)[1] if '. ' in stripped else stripped
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": parse_rich_text(text)
                }
            })
            i += 1

        # Regular paragraph
        else:
            # Parse bold text **bold**
            rich_text = parse_rich_text(stripped)
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich_text
                }
            })
            i += 1

    logger.info(f"Converted markdown to {len(blocks)} Notion blocks")
    return blocks


def parse_rich_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse text with bold markers into Notion rich_text array.

    Supports:
    - **bold text**

    Args:
        text: Text string that may contain **bold** markers

    Returns:
        List of Notion rich_text objects

    Example:
        >>> parse_rich_text("This is **important** text")
        [
            {"type": "text", "text": {"content": "This is "}},
            {"type": "text", "text": {"content": "important"}, "annotations": {"bold": True}},
            {"type": "text", "text": {"content": " text"}}
        ]
    """
    rich_text = []

    # Split by **bold** pattern
    parts = re.split(r'(\*\*.*?\*\*)', text)

    for part in parts:
        if not part:
            continue

        if part.startswith('**') and part.endswith('**'):
            # Bold text (remove ** markers)
            content = part[2:-2]
            if content:  # Only add if not empty
                rich_text.append({
                    "type": "text",
                    "text": {"content": content},
                    "annotations": {"bold": True}
                })
        else:
            # Regular text
            if part:  # Only add if not empty
                rich_text.append({
                    "type": "text",
                    "text": {"content": part}
                })

    # If no rich_text was generated, return a default empty text
    if not rich_text:
        rich_text = [{"type": "text", "text": {"content": ""}}]

    return rich_text


def create_ai_analyzed_briefing_markdown(analyzed_data: Dict[str, Any]) -> str:
    """
    Create daily briefing markdown from AI-analyzed data.

    This function takes analyzed data from briefing_analyzer and
    formats it into a prioritized Markdown briefing.

    Args:
        analyzed_data: AI-analyzed briefing data
              Expected structure:
              {
                  "organized": {
                      "urgent": [...],
                      "important": [...],
                      "normal": [...],
                      "low": [...]
                  },
                  "metadata": {
                      "total_items": N,
                      "high_priority_count": M,
                      "summary": "..."
                  }
              }

    Returns:
        Markdown formatted briefing text with AI insights
    """
    today = datetime.now().strftime('%Y년 %m월 %d일')

    # Start with title and AI summary
    markdown = f"# 📅 Daily Briefing - {today}\n\n"

    metadata = analyzed_data.get("metadata", {})
    summary = metadata.get("summary", "")
    if summary:
        markdown += f"## 🤖 AI Summary\n\n{summary}\n\n"

    markdown += f"**총 {metadata.get('total_items', 0)}개 항목** | "
    markdown += f"**긴급/중요: {metadata.get('high_priority_count', 0)}개**\n\n"

    organized = analyzed_data.get("organized", {})

    # Section 1: Urgent items (🔥)
    urgent_items = organized.get("urgent", [])
    if urgent_items:
        markdown += "## 🔥 긴급 처리 항목\n\n"
        for item in urgent_items:
            markdown += format_analyzed_item(item)
        markdown += "\n"

    # Section 2: Important items (⭐)
    important_items = organized.get("important", [])
    if important_items:
        markdown += "## ⭐ 중요 항목\n\n"
        for item in important_items:
            markdown += format_analyzed_item(item)
        markdown += "\n"

    # Section 3: Normal items (📋)
    normal_items = organized.get("normal", [])
    if normal_items:
        markdown += "## 📋 일반 항목\n\n"
        for item in normal_items:
            markdown += format_analyzed_item(item)
        markdown += "\n"

    return markdown


def format_analyzed_item(item: Dict[str, Any]) -> str:
    """Format a single analyzed item into markdown"""
    item_type = item.get("type", "unknown")
    category = item.get("category", "unknown")
    priority_score = item.get("priority_score", 0)
    reasoning = item.get("reasoning", "")
    estimated_time = item.get("estimated_time", "")

    # Get title based on item type
    if item_type == "email":
        title = item.get("subject", "No subject")
        from_field = item.get("from", "Unknown")
        snippet = item.get("snippet", "")[:100]
        content = f"**{title}** (from: {from_field})"
        if snippet and snippet.strip():
            content += f"\n- {snippet}"
    elif item_type in ["slack_mention", "slack_dm"]:
        channel = item.get("channel", "Unknown")
        user = item.get("user", "Unknown")
        text = item.get("text", "")
        content = f"{text}"
    elif item_type == "notion_task":
        title = item.get("title", "No title")
        status = item.get("status", "Unknown")
        due_date = item.get("due_date", "")
        content = f"**{title}** (Status: {status})"
        if due_date:
            content += f" | Due: {due_date}"
    else:
        content = str(item.get("text", item.get("title", "Unknown item")))

    # Format: Main item without indent, Priority and AI comment with indent
    markdown = f"- [{category.upper()}] {content}\n"
    if priority_score:
        markdown += f"  - 🎯 Priority: {priority_score:.0f}/100"
        if estimated_time:
            markdown += f" | ⏱️ {estimated_time}"
        markdown += "\n"
    if reasoning:
        markdown += f"  - 💡 {reasoning}\n"

    return markdown + "\n"


def create_briefing_markdown(data: Dict[str, Any]) -> str:
    """
    Create daily briefing markdown from collected data.

    This function takes raw data from daily_briefing_collector and
    formats it into a readable Markdown briefing.

    Args:
        data: Briefing data from daily_briefing_collector
              Expected structure:
              {
                  "timestamp": "2025-10-01T07:00:00",
                  "period_hours": 24,
                  "data": {
                      "gmail": {"emails": [...], "count": N, "status": "success"},
                      "slack": {"mentions": [...], "dms": [...], "count": N, "status": "success"},
                      "notion": {"tasks": [...], "count": N, "status": "success"}
                  }
              }

    Returns:
        Markdown formatted briefing text

    Example:
        >>> data = {"data": {"gmail": {"emails": [...]}}}
        >>> markdown = create_briefing_markdown(data)
        >>> "# 📅 Daily Briefing" in markdown
        True
    """
    # Check if this is AI-analyzed data
    if "organized" in data and "metadata" in data:
        logger.info("Using AI-analyzed briefing format")
        return create_ai_analyzed_briefing_markdown(data)

    # Otherwise use raw data format
    logger.info("Using raw data briefing format (no AI analysis)")
    today = datetime.now().strftime('%Y년 %m월 %d일')

    # Start with title
    markdown = f"# 📅 Daily Briefing - {today}\n\n"

    # Get data sources
    data_sources = data.get("data", {})
    gmail_data = data_sources.get("gmail", {})
    slack_data = data_sources.get("slack", {})
    notion_data = data_sources.get("notion", {})

    # Section 1: Urgent items
    markdown += "## 🔥 긴급 처리 항목\n\n"

    # Gmail urgent emails
    emails = gmail_data.get("emails", [])
    if emails:
        for i, email in enumerate(emails[:3], 1):  # Top 3 emails
            subject = email.get('subject', 'No Subject')
            sender = email.get('from', 'Unknown')
            markdown += f"{i}. **[Gmail]** {subject} - {sender}\n"

    if not emails:
        markdown += "- 긴급 이메일 없음\n"

    markdown += "\n"

    # Section 2: Important tasks
    markdown += "## ⭐ 중요 업무\n\n"

    # Notion tasks
    tasks = notion_data.get("tasks", [])
    if tasks:
        for i, task in enumerate(tasks[:5], 1):  # Top 5 tasks
            title = task.get('title', 'Untitled')
            status = task.get('status', 'Unknown')
            priority = task.get('priority', 'N/A')
            markdown += f"{i}. **{title}** - {status} (우선순위: {priority})\n"

    if not tasks:
        markdown += "- 할 일 없음\n"

    markdown += "\n"

    # Section 3: Team updates
    markdown += "## 📋 팀 관련 업데이트\n\n"

    # Slack mentions
    mentions = slack_data.get("mentions", [])
    dms = slack_data.get("dms", [])

    if mentions or dms:
        if mentions:
            markdown += f"- **Slack 멘션**: {len(mentions)}개\n"
        if dms:
            markdown += f"- **Slack DM**: {len(dms)}개\n"
    else:
        markdown += "- 새로운 알림 없음\n"

    markdown += "\n"

    # Section 4: Summary statistics
    markdown += "## 📊 수집 요약\n\n"
    markdown += f"- Gmail: {gmail_data.get('count', 0)}개 이메일\n"
    markdown += f"- Slack: {slack_data.get('count', 0)}개 메시지\n"
    markdown += f"- Notion: {notion_data.get('count', 0)}개 태스크\n"

    # Footer
    markdown += f"\n---\n"
    markdown += f"🤖 Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}\n"

    logger.info(f"Created briefing markdown ({len(markdown)} characters)")
    return markdown


# Test function
async def test_formatter():
    """Test the formatter with sample data"""

    # Test 1: Markdown to Notion blocks
    print("=" * 80)
    print("TEST 1: Markdown to Notion Blocks")
    print("=" * 80)

    test_markdown = """# 📅 Daily Briefing

## 🔥 긴급 처리 항목
- **[Gmail]** 프로젝트 승인 요청 - manager@company.com
- **[Slack]** 코드 리뷰 부탁 - #dev-team

## ⭐ 중요 업무
1. Q3 보고서 작성 - 진행중 (우선순위: High)
2. 클라이언트 미팅 준비 - 예정 (우선순위: Medium)
"""

    blocks = markdown_to_notion_blocks(test_markdown)
    print(f"✅ Generated {len(blocks)} blocks")
    print(f"\nFirst block: {blocks[0]['type']}")
    print(f"Content: {blocks[0][blocks[0]['type']]['rich_text'][0]['text']['content']}")

    # Test 2: Bold text parsing
    print("\n" + "=" * 80)
    print("TEST 2: Bold Text Parsing")
    print("=" * 80)

    test_text = "이것은 **중요한** 내용입니다"
    rich_text = parse_rich_text(test_text)
    print(f"✅ Parsed into {len(rich_text)} segments")
    for i, segment in enumerate(rich_text, 1):
        is_bold = segment.get("annotations", {}).get("bold", False)
        content = segment["text"]["content"]
        print(f"  {i}. '{content}' - Bold: {is_bold}")

    # Test 3: Create briefing markdown
    print("\n" + "=" * 80)
    print("TEST 3: Create Briefing Markdown")
    print("=" * 80)

    sample_data = {
        "timestamp": "2025-10-01T07:00:00",
        "period_hours": 24,
        "data": {
            "gmail": {
                "emails": [
                    {"subject": "긴급: 프로젝트 마감", "from": "manager@company.com"},
                    {"subject": "Q3 보고서 검토", "from": "ceo@company.com"}
                ],
                "count": 2,
                "status": "success"
            },
            "slack": {
                "mentions": [
                    {"text": "@you 코드 리뷰 부탁드립니다", "channel": "#dev"}
                ],
                "dms": [],
                "count": 1,
                "status": "success"
            },
            "notion": {
                "tasks": [
                    {"title": "API 문서 업데이트", "status": "In Progress", "priority": "High"},
                    {"title": "테스트 코드 작성", "status": "Todo", "priority": "Medium"}
                ],
                "count": 2,
                "status": "success"
            }
        }
    }

    markdown = create_briefing_markdown(sample_data)
    print("✅ Generated markdown briefing")
    print(f"\nFirst 300 characters:\n{markdown[:300]}...")
    print(f"\nTotal length: {len(markdown)} characters")

    # Test 4: Full conversion
    print("\n" + "=" * 80)
    print("TEST 4: Full Conversion (Markdown -> Notion Blocks)")
    print("=" * 80)

    blocks_from_briefing = markdown_to_notion_blocks(markdown)
    print(f"✅ Converted briefing into {len(blocks_from_briefing)} Notion blocks")

    # Count block types
    block_types = {}
    for block in blocks_from_briefing:
        block_type = block["type"]
        block_types[block_type] = block_types.get(block_type, 0) + 1

    print("\nBlock type distribution:")
    for block_type, count in block_types.items():
        print(f"  - {block_type}: {count}")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED! ✨")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_formatter())
