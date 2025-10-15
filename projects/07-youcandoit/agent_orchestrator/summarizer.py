#!/usr/bin/env python3
"""
Summarizer module for Agent Orchestrator
Handles conversation and content summarization using LLM providers
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from agent_orchestrator.llm_provider import get_llm_provider, SummaryResult
except ImportError:
    from llm_provider import get_llm_provider, SummaryResult

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """Summarizer for conversation data"""

    def __init__(self):
        self.llm = get_llm_provider()
        logger.info(f"Initialized ConversationSummarizer with {type(self.llm).__name__}")

    async def summarize(
        self,
        content: Dict[str, Any],
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Summarize conversation content

        Args:
            content: Conversation content from MCP request
            context_data: Related context from Context Registry

        Returns:
            Summary result dictionary
        """
        logger.info("Summarizing conversation")

        # Extract messages from content
        messages = content.get("messages", [])
        if not messages:
            logger.warning("No messages found in content")
            return self._empty_summary()

        # Prepare context for LLM
        llm_context = {
            "platform": content.get("source", "unknown"),
            "session_id": content.get("channel", "unknown"),
            "timestamp": datetime.now().isoformat()
        }

        # Add context data if available
        if context_data:
            conversations = context_data.get("conversations", [])
            if conversations:
                llm_context["previous_conversations"] = len(conversations)

        try:
            # Use LLM to summarize
            result = await self.llm.summarize_conversation(messages, llm_context)

            # Format result for Agent Orchestrator
            return {
                "type": "conversation_summary",
                "summary": result.summary,
                "key_points": result.key_points,
                "entities": result.entities,
                "action_items": result.action_items,
                "metadata": {
                    "session_id": content.get("channel"),
                    "platform": content.get("source"),
                    "timestamp": datetime.now().isoformat(),
                    "message_count": len(messages),
                    "context_count": len(context_data.get("conversations", [])) if context_data else 0,
                    "confidence": result.confidence
                }
            }

        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")
            return self._empty_summary()

    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary as fallback"""
        return {
            "type": "conversation_summary",
            "summary": "No summary available",
            "key_points": [],
            "entities": [],
            "action_items": [],
            "metadata": {
                "confidence": 0.0,
                "error": "Summarization failed"
            }
        }


class ExtractionSummarizer:
    """Summarizer for content extraction"""

    def __init__(self):
        self.llm = get_llm_provider()
        logger.info(f"Initialized ExtractionSummarizer with {type(self.llm).__name__}")

    async def extract(
        self,
        content: Dict[str, Any],
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract and summarize content

        Args:
            content: Content to extract from
            context_data: Related context from Context Registry

        Returns:
            Extraction result dictionary
        """
        logger.info("Extracting insights from content")

        # Get content text
        content_text = content.get("content", "")
        extract_type = content.get("extract_type", "summary")

        if not content_text:
            logger.warning("No content text found")
            return self._empty_extraction(extract_type)

        try:
            # Use LLM to extract insights
            result = await self.llm.extract_insights(content_text, extract_type)

            # Format result for Agent Orchestrator
            return {
                "type": "extraction_result",
                "extract_type": extract_type,
                "summary": result.summary,
                "data": {
                    "key_insights": result.key_points,
                    "action_items": result.action_items,
                    "entities": result.entities,
                    "confidence": result.confidence
                },
                "metadata": {
                    "extract_type": extract_type,
                    "content_length": len(content_text),
                    "context_integration": len(context_data.get("extract_results", [])) if context_data else 0,
                    "timestamp": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Failed to extract insights: {e}")
            return self._empty_extraction(extract_type)

    def _empty_extraction(self, extract_type: str) -> Dict[str, Any]:
        """Return empty extraction as fallback"""
        return {
            "type": "extraction_result",
            "extract_type": extract_type,
            "summary": "No extraction available",
            "data": {
                "key_insights": [],
                "action_items": [],
                "entities": [],
                "confidence": 0.0
            },
            "metadata": {
                "error": "Extraction failed"
            }
        }


class BriefingSummarizer:
    """Summarizer for daily briefing data"""

    def __init__(self):
        self.llm = get_llm_provider()
        logger.info(f"Initialized BriefingSummarizer with {type(self.llm).__name__}")

    async def analyze_and_prioritize(
        self,
        collected_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze collected briefing data and prioritize items

        Args:
            collected_data: Data from daily_briefing_collector

        Returns:
            Analyzed and prioritized briefing data
        """
        logger.info("Analyzing and prioritizing briefing data")

        # Prepare items for priority analysis
        items = []

        # Add Gmail items
        gmail_data = collected_data.get("gmail", {})
        for email in gmail_data.get("emails", []):
            items.append({
                "id": f"gmail_{email.get('id', 'unknown')}",
                "type": "email",
                "category": "email",
                "subject": email.get("subject", ""),
                "from": email.get("from", ""),
                "snippet": email.get("snippet", ""),
                "received_time": email.get("received_time", ""),
                "labels": email.get("labels", [])
            })

        # Add Slack items (mentions and DMs)
        slack_data = collected_data.get("slack", {})
        for msg in slack_data.get("mentions", []):
            items.append({
                "id": f"slack_mention_{msg.get('MsgID', msg.get('Time', 'unknown'))}",
                "type": "slack_mention",
                "category": "slack",
                "channel": msg.get("channel_name", msg.get("Channel", "")),
                "user": msg.get("UserName", msg.get("user", "")),
                "text": msg.get("Text", msg.get("text", "")),
                "timestamp": msg.get("Time", msg.get("ts", ""))
            })

        for msg in slack_data.get("dms", []):
            items.append({
                "id": f"slack_dm_{msg.get('MsgID', msg.get('Time', 'unknown'))}",
                "type": "slack_dm",
                "category": "slack",
                "channel": "DM",
                "user": msg.get("UserName", msg.get("user", "")),
                "text": msg.get("Text", msg.get("text", "")),
                "timestamp": msg.get("Time", msg.get("ts", ""))
            })

        # Add Notion items
        notion_data = collected_data.get("notion", {})
        for task in notion_data.get("tasks", []):
            items.append({
                "id": f"notion_{task.get('id', 'unknown')}",
                "type": "notion_task",
                "category": "notion",
                "title": task.get("title", ""),
                "status": task.get("status", ""),
                "priority": task.get("priority", ""),
                "due_date": task.get("due_date", "")
            })

        if not items:
            logger.warning("No items to analyze")
            return {
                "analyzed_items": [],
                "summary": "No items collected",
                "total_items": 0,
                "high_priority_count": 0,
                "categories": {}
            }

        try:
            # Use LLM to analyze priorities
            context = f"Today's date: {datetime.now().strftime('%Y-%m-%d')}"
            priorities = await self.llm.analyze_priorities(items, context)

            # Organize results
            analyzed_items = []
            high_priority_count = 0
            category_counts = {}

            for priority in priorities:
                # Find original item
                original_item = next(
                    (item for item in items if item["id"] == priority.item_id),
                    None
                )

                if original_item:
                    analyzed_item = {
                        **original_item,
                        "priority_score": priority.priority_score,
                        "urgency": priority.urgency,
                        "reasoning": priority.reasoning,
                        "estimated_time": priority.estimated_time
                    }
                    analyzed_items.append(analyzed_item)

                    # Count high priority items
                    if priority.urgency in ["urgent", "important"]:
                        high_priority_count += 1

                    # Count by category
                    category = priority.category
                    category_counts[category] = category_counts.get(category, 0) + 1

            # Generate overall summary
            summary_text = await self._generate_briefing_summary(analyzed_items)

            return {
                "analyzed_items": analyzed_items,
                "summary": summary_text,
                "total_items": len(analyzed_items),
                "high_priority_count": high_priority_count,
                "categories": category_counts,
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to analyze priorities: {e}")
            # Return items without priority analysis
            return {
                "analyzed_items": items,
                "summary": "Priority analysis failed - showing items in original order",
                "total_items": len(items),
                "high_priority_count": 0,
                "categories": {},
                "error": str(e)
            }

    async def _generate_briefing_summary(self, analyzed_items: List[Dict[str, Any]]) -> str:
        """Generate a brief summary of the day's priorities"""
        if not analyzed_items:
            return "No items to brief today."

        # Get top 3 items
        top_items = analyzed_items[:3]

        summary_parts = [f"Today you have {len(analyzed_items)} items requiring attention."]

        # Add top priorities
        if top_items:
            summary_parts.append("\n\nTop priorities:\n")
            for i, item in enumerate(top_items, 1):
                item_type = item.get("type", "item")
                title = item.get("subject") or item.get("title") or item.get("text", "")[:50]
                summary_parts.append(f"{i}. [{item.get('urgency', 'normal').upper()}] {title}\n")

        return "".join(summary_parts)
