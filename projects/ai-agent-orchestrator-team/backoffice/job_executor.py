#!/usr/bin/env python3
"""
Job Executor for different job types
Handles execution of morning brief, knowledge cards, etc.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobExecutor:
    """Executes different types of jobs"""
    
    def __init__(self, registry=None, orchestrator=None):
        self.registry = registry
        self.orchestrator = orchestrator
        
        # Initialize generators lazily
        self._morning_brief_generator = None
    
    @property
    def morning_brief_generator(self):
        """Lazy initialization of MorningBriefGenerator"""
        if self._morning_brief_generator is None:
            from morning_brief import MorningBriefGenerator
            self._morning_brief_generator = MorningBriefGenerator(self.registry)
        return self._morning_brief_generator
    
    async def execute(self, job_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute job based on type"""
        logger.info(f"Executing job type: {job_type}")
        
        try:
            if job_type == "ambient":
                return await self.execute_ambient(params)
            elif job_type == "agent":
                return await self.execute_agent(params)
            else:
                raise ValueError(f"Unknown job type: {job_type}")
                
        except Exception as e:
            logger.error(f"Job execution failed for {job_type}: {e}")
            raise
    
    async def execute_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent job (calls orchestrator)"""
        logger.info("Executing Agent Job")
        
        if not self.orchestrator:
            return {"error": "Agent Orchestrator not available"}
        
        try:
            message = params.get("message", "")
            request_type = params.get("request_type", "general")
            
            # Call Agent Orchestrator
            result = await self.orchestrator.process_request(
                request_type,
                {"message": message, "params": params}
            )
            
            logger.info("Agent job completed successfully")
            
            return {
                "job_type": "agent",
                "message": message,
                "request_type": request_type,
                "orchestrator_result": result,
                "generated_at": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Agent job failed: {e}")
            return {
                "job_type": "agent",
                "error": str(e),
                "success": False
            }
    
    async def execute_ambient(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ambient job (knowledge cards or daily briefing)"""

        # Detect job subtype
        if "services" in params and "parent_page_id" in params:
            # Daily Briefing job
            return await self.execute_daily_briefing(params)
        else:
            # Knowledge Cards job
            return await self.execute_knowledge_cards(params)

    async def execute_knowledge_cards(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Knowledge Cards generation"""
        logger.info("Executing Ambient Job - Knowledge Cards generation")

        if not self.registry:
            return {"error": "Context Registry not available"}

        try:
            max_cards = params.get("max_cards", 5)
            target_date = params.get("target_date")

            if target_date:
                target_date = datetime.fromisoformat(target_date).date()
            else:
                target_date = (datetime.now() - timedelta(days=1)).date()

            # Generate knowledge cards
            cards = await self.morning_brief_generator.generate_knowledge_cards(
                target_date=target_date,
                max_cards=max_cards
            )

            logger.info(f"Generated {len(cards)} knowledge cards")

            return {
                "job_type": "ambient",
                "subtype": "knowledge_cards",
                "target_date": target_date.isoformat(),
                "cards": cards,
                "card_count": len(cards),
                "generated_at": datetime.now().isoformat(),
                "success": True
            }

        except Exception as e:
            logger.error(f"Ambient job (Knowledge Cards) generation failed: {e}")
            return {
                "job_type": "ambient",
                "subtype": "knowledge_cards",
                "error": str(e),
                "success": False
            }

    async def execute_daily_briefing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Daily Briefing through Agent Orchestrator"""
        logger.info("Executing Ambient Job - Daily Briefing Report")

        if not self.orchestrator:
            return {"error": "Agent Orchestrator not available"}

        try:
            # Prepare request for AO
            request_content = {
                "target_date": params.get("target_date", datetime.now().strftime("%Y-%m-%d")),
                "services": params.get("services", ["gmail", "slack", "notion"]),
                "hours": params.get("hours", 24),
                "parent_page_id": params.get("parent_page_id", ""),
                "notion_database_id": params.get("notion_database_id", "")
            }

            # Call Agent Orchestrator with daily_briefing request type
            result = await self.orchestrator.process_request(
                "daily_briefing",
                request_content
            )

            logger.info(f"Daily Briefing completed: {result.get('notion_page_url', 'N/A')}")

            return {
                "job_type": "ambient",
                "subtype": "daily_briefing",
                "target_date": request_content["target_date"],
                "notion_page_url": result.get("notion_page_url"),
                "orchestrator_result": result,
                "generated_at": datetime.now().isoformat(),
                "success": True
            }

        except Exception as e:
            logger.error(f"Ambient job (Daily Briefing) failed: {e}")
            return {
                "job_type": "ambient",
                "subtype": "daily_briefing",
                "error": str(e),
                "success": False
            }
    
    
    async def save_to_notion(self, content: Dict[str, Any]) -> Optional[str]:
        """Save content to Notion (placeholder implementation)"""
        try:
            # TODO: Implement Notion integration
            logger.info("Notion integration not implemented yet")
            
            # For now, save to local file
            output_file = Path("briefing_output") / f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_file.parent.mkdir(exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Brief saved to {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Failed to save to Notion: {e}")
            return None