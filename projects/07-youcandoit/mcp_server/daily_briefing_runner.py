#!/usr/bin/env python3
"""
Daily Briefing Runner with Logging

Wraps the briefing execution with automatic logging to Context Registry.
"""

import os
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from context_registry.registry import registry, DailyBriefingLogRecord
from mcp_server.daily_briefing_collector import collect_daily_briefing_data
from mcp_server.notion_briefing_integration import create_daily_briefing_page
from mcp_server.briefing_analyzer import analyze_briefing_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_daily_briefing_with_logging(
    parent_page_id: str,
    date: Optional[str] = None,
    hours: int = 24,
    notion_database_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run daily briefing with automatic logging to Context Registry

    Args:
        parent_page_id: Notion parent page ID
        date: Target date (YYYY-MM-DD), defaults to today
        hours: Look back period in hours (default 24)
        notion_database_id: Notion database ID for tasks (optional)

    Returns:
        {
            "status": "success" | "error",
            "log_id": "brief_...",
            "page_url": "https://notion.so/...",
            "execution_time": 127.5,
            "error": None | "error message"
        }
    """
    # 1️⃣ 날짜 및 시작 시간 설정
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    start_time = datetime.now()
    start_time_iso = start_time.isoformat()

    logger.info(f"=" * 80)
    logger.info(f"Starting Daily Briefing for {date}")
    logger.info(f"Start time: {start_time_iso}")
    logger.info(f"=" * 80)

    # 초기 로그 레코드 생성 (status: "running")
    log_record = DailyBriefingLogRecord(
        id=None,  # 자동 생성
        execution_date=date,
        start_time=start_time_iso,
        end_time=None,
        status="running",
        services_data=None,
        analysis_result=None,
        notion_page_url=None,
        error_message=None,
        execution_duration=None
    )

    try:
        # 2️⃣ 데이터 수집
        logger.info("Step 1: Collecting data from MCP servers...")
        collected_data = await collect_daily_briefing_data(
            hours=hours,
            notion_database_id=notion_database_id
        )

        logger.info(f"Data collected:")
        logger.info(f"  - Gmail: {collected_data['data']['gmail']['count']} emails")
        logger.info(f"  - Slack: {collected_data['data']['slack']['count']} messages")
        logger.info(f"  - Notion: {collected_data['data']['notion']['count']} tasks")
        logger.info(f"  - Successful sources: {collected_data['summary']['successful_sources']}/3")

        # 수집된 데이터 저장
        log_record.services_data = collected_data

        # 3️⃣ AI 분석 및 우선순위 계산
        logger.info("\nStep 2: Analyzing data with AI for priority ranking...")
        analyzed_data = await analyze_briefing_data(collected_data['data'])

        logger.info(f"AI Analysis completed:")
        logger.info(f"  - Total items: {analyzed_data['metadata']['total_items']}")
        logger.info(f"  - High priority: {analyzed_data['metadata']['high_priority_count']}")
        logger.info(f"  - Urgent: {len(analyzed_data['organized']['urgent'])}")
        logger.info(f"  - Important: {len(analyzed_data['organized']['important'])}")

        # 분석 결과 저장
        log_record.analysis_result = analyzed_data

        # 4️⃣ Notion 브리핑 페이지 생성 (분석된 데이터 사용)
        logger.info("\nStep 3: Creating Notion briefing page with AI insights...")
        result = await create_daily_briefing_page(
            collected_data=analyzed_data,  # 분석된 데이터 전달
            parent_page_id=parent_page_id,
            date=date
        )

        if result["status"] != "success":
            raise Exception(f"Failed to create Notion page: {result.get('error')}")

        page_url = result["page_url"]
        logger.info(f"✅ Briefing page created: {page_url}")

        # 5️⃣ 종료 시간 및 실행 시간 계산
        end_time = datetime.now()
        execution_duration = int((end_time - start_time).total_seconds())

        # 6️⃣ 성공 로그 저장
        log_record.end_time = end_time.isoformat()
        log_record.status = "completed"
        log_record.notion_page_url = page_url
        log_record.execution_duration = execution_duration

        log_id = registry.store_daily_briefing_log(log_record)

        logger.info(f"\n" + "=" * 80)
        logger.info(f"Daily Briefing COMPLETED")
        logger.info(f"Execution time: {execution_duration} seconds")
        logger.info(f"Log ID: {log_id}")
        logger.info(f"Page URL: {page_url}")
        logger.info(f"=" * 80)

        return {
            "status": "success",
            "log_id": log_id,
            "page_url": page_url,
            "execution_time": execution_duration,
            "error": None
        }

    except Exception as e:
        # 7️⃣ 실패 로그 저장
        end_time = datetime.now()
        execution_duration = int((end_time - start_time).total_seconds())

        log_record.end_time = end_time.isoformat()
        log_record.status = "failed"
        log_record.error_message = str(e)
        log_record.execution_duration = execution_duration

        log_id = registry.store_daily_briefing_log(log_record)

        logger.error(f"\n" + "=" * 80)
        logger.error(f"Daily Briefing FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Execution time: {execution_duration} seconds")
        logger.error(f"Log ID: {log_id}")
        logger.error(f"=" * 80)

        return {
            "status": "error",
            "log_id": log_id,
            "page_url": None,
            "execution_time": execution_duration,
            "error": str(e)
        }


async def get_recent_logs(limit: int = 10) -> list:
    """
    Get recent daily briefing logs from Context Registry

    Args:
        limit: Number of logs to retrieve

    Returns:
        List of log records
    """
    import sqlite3

    try:
        conn = sqlite3.connect(registry.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM daily_briefing_log
            ORDER BY execution_date DESC, start_time DESC
            LIMIT ?
        """, (limit,))

        logs = []
        for row in cursor.fetchall():
            logs.append(dict(row))

        conn.close()
        return logs

    except Exception as e:
        logger.error(f"Failed to retrieve logs: {str(e)}")
        return []
