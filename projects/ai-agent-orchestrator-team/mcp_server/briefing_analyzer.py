#!/usr/bin/env python3
"""
Briefing Analyzer - AI-powered priority analysis for Daily Briefing
Integrates with Agent Orchestrator's BriefingSummarizer
"""

import asyncio
import logging
import sys
import os
from typing import Any, Dict, List
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_orchestrator.summarizer import BriefingSummarizer

logger = logging.getLogger(__name__)


class BriefingAnalyzer:
    """Analyzer for daily briefing data with AI-powered prioritization"""

    def __init__(self):
        self.summarizer = BriefingSummarizer()
        logger.info("BriefingAnalyzer initialized with AI summarizer")

    async def analyze(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze collected briefing data and add AI-powered insights

        Args:
            collected_data: Raw data from daily_briefing_collector

        Returns:
            Analyzed data with priorities and insights
        """
        logger.info("Starting AI analysis of briefing data")

        try:
            # Use BriefingSummarizer to analyze and prioritize
            analysis_result = await self.summarizer.analyze_and_prioritize(collected_data)

            # Organize by category and urgency
            organized_data = self._organize_by_priority(analysis_result)

            return {
                "raw_data": collected_data,
                "analysis": analysis_result,
                "organized": organized_data,
                "metadata": {
                    "total_items": analysis_result.get("total_items", 0),
                    "high_priority_count": analysis_result.get("high_priority_count", 0),
                    "categories": analysis_result.get("categories", {}),
                    "summary": analysis_result.get("summary", "")
                }
            }

        except Exception as e:
            logger.error(f"Failed to analyze briefing data: {e}")
            # Return raw data without analysis
            return {
                "raw_data": collected_data,
                "analysis": {
                    "error": str(e),
                    "analyzed_items": []
                },
                "organized": {
                    "urgent": [],
                    "important": [],
                    "normal": [],
                    "low": []
                },
                "metadata": {
                    "total_items": 0,
                    "high_priority_count": 0,
                    "error": "Analysis failed"
                }
            }

    def _organize_by_priority(self, analysis_result: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Organize analyzed items by urgency level"""
        organized = {
            "urgent": [],
            "important": [],
            "normal": [],
            "low": []
        }

        for item in analysis_result.get("analyzed_items", []):
            urgency = item.get("urgency", "normal")
            if urgency in organized:
                organized[urgency].append(item)

        return organized


async def analyze_briefing_data(collected_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to analyze briefing data

    Args:
        collected_data: Raw collected data from daily_briefing_collector

    Returns:
        Analyzed and prioritized briefing data
    """
    analyzer = BriefingAnalyzer()
    return await analyzer.analyze(collected_data)


# Example usage and testing
if __name__ == "__main__":
    async def test_analyzer():
        """Test the briefing analyzer with sample data"""
        # Sample collected data
        sample_data = {
            "gmail": {
                "emails": [
                    {
                        "id": "email1",
                        "subject": "Urgent: Production server down",
                        "from": "ops@company.com",
                        "snippet": "Our main production server is experiencing downtime...",
                        "received_time": "2025-10-02T08:30:00Z",
                        "labels": ["IMPORTANT", "UNREAD"]
                    },
                    {
                        "id": "email2",
                        "subject": "Team lunch next week",
                        "from": "hr@company.com",
                        "snippet": "Please confirm your attendance for team lunch...",
                        "received_time": "2025-10-02T09:00:00Z",
                        "labels": ["UNREAD"]
                    }
                ],
                "total": 2
            },
            "slack": {
                "messages": [
                    {
                        "ts": "1696234567.123456",
                        "channel": "#engineering",
                        "user": "john.doe",
                        "text": "@you Can you review the PR for the new feature?",
                        "type": "mention"
                    }
                ],
                "total": 1
            },
            "notion": {
                "tasks": [
                    {
                        "id": "task1",
                        "title": "Finish Q4 roadmap presentation",
                        "status": "In Progress",
                        "priority": "High",
                        "due_date": "2025-10-03"
                    }
                ],
                "total": 1
            }
        }

        print("=" * 60)
        print("Testing Briefing Analyzer with AI")
        print("=" * 60)

        analyzer = BriefingAnalyzer()
        result = await analyzer.analyze(sample_data)

        print("\n📊 Analysis Results:")
        print(f"Total items: {result['metadata']['total_items']}")
        print(f"High priority: {result['metadata']['high_priority_count']}")
        print(f"\n📝 Summary:")
        print(result['metadata']['summary'])

        print("\n🔥 Urgent Items:")
        for item in result['organized']['urgent']:
            title = item.get('subject') or item.get('title') or item.get('text', '')[:50]
            print(f"  - [{item['category']}] {title}")
            print(f"    Score: {item['priority_score']:.1f} | Reasoning: {item['reasoning'][:80]}...")

        print("\n⭐ Important Items:")
        for item in result['organized']['important']:
            title = item.get('subject') or item.get('title') or item.get('text', '')[:50]
            print(f"  - [{item['category']}] {title}")
            print(f"    Score: {item['priority_score']:.1f} | Reasoning: {item['reasoning'][:80]}...")

        print("\n" + "=" * 60)

    asyncio.run(test_analyzer())
