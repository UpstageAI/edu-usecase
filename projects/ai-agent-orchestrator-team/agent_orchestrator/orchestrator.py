#!/usr/bin/env python3
"""
Agent Orchestrator with LangGraph StateGraph
Implements the four-node workflow: plan -> cr_read -> summarize -> cr_write
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict
from dataclasses import dataclass

import aiohttp

# Import summarizers
try:
    from agent_orchestrator.summarizer import ConversationSummarizer, ExtractionSummarizer, BriefingSummarizer
except ImportError:
    from summarizer import ConversationSummarizer, ExtractionSummarizer, BriefingSummarizer

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.state import CompiledStateGraph
except ImportError:
    print("Warning: LangGraph not available, using demo mode")
    
    class StateGraph:
        def __init__(self, state_type=None):
            self.nodes = {}
            self.edges = {}
            self.state_type = state_type
        
        def add_node(self, name: str, func):
            self.nodes[name] = func
        
        def add_edge(self, from_node: str, to_node: str):
            if from_node not in self.edges:
                self.edges[from_node] = []
            self.edges[from_node].append(to_node)
        
        def set_entry_point(self, node: str):
            self.entry = node
        
        def compile(self):
            return CompiledStateGraph(self.nodes, self.edges, self.entry)
    
    class CompiledStateGraph:
        def __init__(self, nodes, edges, entry):
            self.nodes = nodes
            self.edges = edges
            self.entry = entry
        
        async def ainvoke(self, state):
            return {"status": "demo_completed", "result": state}
    
    END = "END"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State structure for the Agent Orchestrator workflow"""
    # Input data
    request_type: str  # "conversation_log", "extract", or "daily_briefing"
    content: Dict[str, Any]

    # Processing state
    plan: Optional[Dict[str, Any]]
    context_data: Optional[Dict[str, Any]]
    summary_result: Optional[Dict[str, Any]]

    # Daily Briefing specific
    collected_data: Optional[Dict[str, Any]]  # MCP collected data
    analysis_result: Optional[Dict[str, Any]]  # AI analysis result
    notion_page_url: Optional[str]  # Created Notion page URL

    # Output
    final_result: Optional[Dict[str, Any]]
    error: Optional[str]

@dataclass
class ContextRegistryClient:
    """Client interface to Context Registry"""
    
    def __init__(self):
        # Import Context Registry
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from context_registry.registry import registry, ConversationRecord, ExtractResultRecord
        self.registry = registry
        self.ConversationRecord = ConversationRecord
        self.ExtractResultRecord = ExtractResultRecord
    
    async def read_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Read relevant context from Context Registry"""
        logger.info(f"Reading context from CR: {query}")
        
        try:
            # None or empty string means search all channels
            channel = query.get("channel")
            limit = query.get("limit", 10)
            
            conversations = self.registry.get_conversations(
                channel=channel if channel else None,
                limit=limit
            )
            
            return {
                "conversations": conversations,
                "extract_results": []
            }
        except Exception as e:
            logger.error(f"Failed to read from CR: {e}")
            return {
                "conversations": [],
                "extract_results": []
            }
    
    async def write_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Write processed data to Context Registry"""
        logger.info(f"Writing to CR: {data.get('type', 'unknown')}")
        
        try:
            content = data.get("content", {})
            
            # Create ConversationRecord
            record = self.ConversationRecord(
                id=None,
                record_type="conversation",
                source=content.get("source", "cursor"),
                channel=content.get("channel", "unknown"),
                payload=content.get("messages", []),
                timestamp=datetime.now().isoformat(),
                actor="ao",
                deleted=False
            )
            
            # Store to CR
            conv_id = self.registry.store_conversation(record)
            
            logger.info(f"Successfully stored conversation: {conv_id}")
            
            return {
                "status": "success",
                "id": conv_id,
                "stored_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to write to CR: {e}")
            raise

class AgentOrchestrator:
    """Main orchestrator using LangGraph StateGraph"""

    def __init__(self):
        self.cr_client = ContextRegistryClient()
        self.conversation_summarizer = ConversationSummarizer()
        self.extraction_summarizer = ExtractionSummarizer()
        self.briefing_summarizer = BriefingSummarizer()
        self.graph = self._create_graph()
        
    def _create_graph(self) -> CompiledStateGraph:
        """Create the LangGraph StateGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes for all request types
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("cr_read", self._cr_read_node)
        workflow.add_node("summarize", self._summarize_node)
        workflow.add_node("cr_write", self._cr_write_node)

        # Daily Briefing specific nodes
        workflow.add_node("external_action_collect", self._external_action_collect_node)
        workflow.add_node("transform", self._transform_node)
        workflow.add_node("external_action_notion", self._external_action_notion_node)

        # Entry point
        workflow.set_entry_point("plan")

        # Conditional routing after plan
        workflow.add_conditional_edges(
            "plan",
            self._route_after_plan,
            {
                "conversation_extract": "cr_read",  # conversation_log, extract
                "daily_briefing": "external_action_collect"  # daily_briefing
            }
        )

        # Conversation/Extract flow
        workflow.add_edge("cr_read", "summarize")
        workflow.add_edge("summarize", "cr_write")

        # Daily Briefing flow
        workflow.add_edge("external_action_collect", "transform")
        workflow.add_edge("transform", "external_action_notion")
        workflow.add_edge("external_action_notion", "cr_write")

        # End
        workflow.add_edge("cr_write", END)

        return workflow.compile()

    def _route_after_plan(self, state: AgentState) -> str:
        """Route to appropriate workflow based on request type"""
        request_type = state["request_type"]
        if request_type == "daily_briefing":
            return "daily_briefing"
        else:
            return "conversation_extract"
    
    async def _plan_node(self, state: AgentState) -> AgentState:
        """Plan node: Analyze incoming request and determine processing strategy"""
        logger.info(f"Planning for request type: {state['request_type']}")
        
        try:
            request_type = state["request_type"]
            content = state["content"]
            
            if request_type == "conversation_log":
                plan = {
                    "strategy": "conversation_processing",
                    "steps": [
                        "read_session_context",
                        "summarize_conversation",
                        "store_with_metadata"
                    ],
                    "context_query": {
                        "session_id": content.get("session_id"),
                        "platform": content.get("platform"),
                        "type": "conversation"
                    }
                }
            elif request_type == "extract":
                plan = {
                    "strategy": "content_extraction",
                    "steps": [
                        "read_related_context",
                        "extract_structured_data",
                        "store_extract_result"
                    ],
                    "context_query": {
                        "channel": content.get("channel"),  # None for all channels
                        "query": content.get("query", {}),  # Include query with text and limit
                        "limit": content.get("query", {}).get("limit", 10),
                        "type": "extract"
                    }
                }
            elif request_type == "daily_briefing":
                plan = {
                    "strategy": "daily_briefing_generation",
                    "steps": [
                        "collect_mcp_data",
                        "ai_priority_analysis",
                        "create_notion_page",
                        "store_execution_log"
                    ],
                    "config": {
                        "target_date": content.get("target_date"),
                        "services": content.get("services", ["gmail", "slack", "notion"]),
                        "hours": content.get("hours", 24),
                        "parent_page_id": content.get("parent_page_id"),
                        "notion_database_id": content.get("notion_database_id")
                    }
                }
            else:
                raise ValueError(f"Unknown request type: {request_type}")
            
            state["plan"] = plan
            logger.info(f"Plan created: {plan['strategy']}")
            
        except Exception as e:
            logger.error(f"Planning failed: {str(e)}")
            state["error"] = f"Planning failed: {str(e)}"
        
        return state
    
    async def _cr_read_node(self, state: AgentState) -> AgentState:
        """CR Read node: Retrieve relevant context from Context Registry"""
        logger.info("Reading context from Context Registry")
        
        try:
            if state.get("error"):
                return state
            
            plan = state["plan"]
            context_query = plan["context_query"]
            
            # Read context from CR
            context_data = await self.cr_client.read_context(context_query)
            
            state["context_data"] = context_data
            logger.info(f"Context retrieved: {len(context_data.get('conversations', []))} conversations, "
                       f"{len(context_data.get('extract_results', []))} extracts")
            
        except Exception as e:
            logger.error(f"Context reading failed: {str(e)}")
            state["error"] = f"Context reading failed: {str(e)}"
        
        return state
    
    async def _summarize_node(self, state: AgentState) -> AgentState:
        """Summarize node: Process and summarize conversation content using LLM"""
        logger.info("Processing and summarizing content with LLM")

        try:
            if state.get("error"):
                return state

            request_type = state["request_type"]
            content = state["content"]
            context_data = state["context_data"]

            # Use appropriate summarizer based on request type
            if request_type == "conversation_log":
                # Skip LLM summarization for conversation_log - store original messages as-is
                # This improves performance and preserves full conversation context
                logger.info("Skipping LLM summarization for conversation_log (storing original messages)")
                summary_result = {
                    "type": "conversation_storage",
                    "summary": "Original conversation stored without summarization",
                    "key_points": [],
                    "entities": [],
                    "action_items": [],
                    "metadata": {
                        "session_id": content.get("channel"),
                        "platform": content.get("source"),
                        "timestamp": datetime.now().isoformat(),
                        "message_count": len(content.get("messages", [])),
                        "summarization_skipped": True
                    }
                }
            elif request_type == "extract":
                summary_result = await self.extraction_summarizer.extract(
                    content, context_data
                )
            else:
                raise ValueError(f"Unknown request type: {request_type}")

            state["summary_result"] = summary_result
            logger.info(f"Processing completed: {summary_result['type']}")

        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            state["error"] = f"Processing failed: {str(e)}"

        return state
    
    async def _fetch_notion_data(self) -> List[Dict[str, Any]]:
        """Fetch pending tasks from Notion MCP server using MCP protocol."""
        logger.info("Fetching data from Notion MCP server...")

        try:
            # Import the MCP client
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))
            from mcp_server.notion_mcp_client import fetch_notion_data_via_mcp

            # Fetch data via MCP protocol
            tasks = await fetch_notion_data_via_mcp()

            logger.info(f"Successfully fetched {len(tasks)} tasks from Notion via MCP")
            return tasks

        except ImportError as e:
            logger.error(f"MCP client not available: {str(e)}")
            logger.info("Please install: uv add mcp")
            return []
        except Exception as e:
            logger.error(f"Error fetching Notion data via MCP: {str(e)}")
            return []

    async def _external_action_collect_node(self, state: AgentState) -> AgentState:
        """External Action: Collect data from MCP servers (Gmail, Slack, Notion)"""
        logger.info("Collecting data from external MCP servers")

        try:
            if state.get("error"):
                return state

            plan = state["plan"]
            config = plan.get("config", {})

            # Import collector
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))
            from mcp_server.daily_briefing_collector import collect_daily_briefing_data

            # Collect data
            collected_data = await collect_daily_briefing_data(
                hours=config.get("hours", 24),
                notion_database_id=config.get("notion_database_id")
            )

            state["collected_data"] = collected_data
            logger.info(f"Data collected from {collected_data['summary']['successful_sources']} sources")

        except Exception as e:
            logger.error(f"Data collection failed: {str(e)}")
            state["error"] = f"Data collection failed: {str(e)}"

        return state

    async def _transform_node(self, state: AgentState) -> AgentState:
        """Transform: AI analysis and priority ranking"""
        logger.info("Analyzing collected data with AI")

        try:
            if state.get("error"):
                return state

            collected_data = state["collected_data"]

            # Use BriefingSummarizer for AI analysis
            analysis_result = await self.briefing_summarizer.analyze_and_prioritize(
                collected_data.get("data", {})
            )

            state["analysis_result"] = analysis_result
            logger.info(f"AI analysis completed: {analysis_result.get('total_items', 0)} items analyzed")

        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            state["error"] = f"AI analysis failed: {str(e)}"

        return state

    async def _external_action_notion_node(self, state: AgentState) -> AgentState:
        """External Action: Create Notion briefing page"""
        logger.info("Creating Notion briefing page")

        try:
            if state.get("error"):
                return state

            analysis_result = state["analysis_result"]
            plan = state["plan"]
            config = plan.get("config", {})

            # Import Notion integration
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))
            from mcp_server.notion_briefing_integration import create_daily_briefing_page

            # Create organized data structure for Notion formatter
            analyzed_data = {
                "organized": {
                    "urgent": [],
                    "important": [],
                    "normal": [],
                    "low": []
                },
                "metadata": {
                    "total_items": analysis_result.get("total_items", 0),
                    "high_priority_count": analysis_result.get("high_priority_count", 0),
                    "summary": analysis_result.get("summary", "")
                }
            }

            # Organize items by urgency (filter by priority_score >= 50)
            PRIORITY_THRESHOLD = 50
            for item in analysis_result.get("analyzed_items", []):
                priority_score = item.get("priority_score", 0)

                # Filter: only include items with priority_score >= 50
                if priority_score >= PRIORITY_THRESHOLD:
                    urgency = item.get("urgency", "normal")
                    if urgency in analyzed_data["organized"]:
                        analyzed_data["organized"][urgency].append(item)

            # Create Notion page
            result = await create_daily_briefing_page(
                collected_data=analyzed_data,
                parent_page_id=config.get("parent_page_id"),
                date=config.get("target_date")
            )

            if result.get("status") == "success":
                state["notion_page_url"] = result.get("page_url")
                logger.info(f"Notion page created: {result.get('page_url')}")
            else:
                raise Exception(f"Notion page creation failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Notion page creation failed: {str(e)}")
            state["error"] = f"Notion page creation failed: {str(e)}"

        return state

    async def _cr_write_node(self, state: AgentState) -> AgentState:
        """CR Write node: Store results back to Context Registry"""
        logger.info("Writing results to Context Registry")

        try:
            if state.get("error"):
                return state

            request_type = state["request_type"]

            # Handle different request types
            if request_type == "daily_briefing":
                # Store daily briefing log
                import sys
                from pathlib import Path
                sys.path.append(str(Path(__file__).parent.parent))
                from context_registry.registry import registry, DailyBriefingLogRecord

                plan = state["plan"]
                config = plan.get("config", {})

                log_record = DailyBriefingLogRecord(
                    id=None,
                    execution_date=config.get("target_date", datetime.now().strftime("%Y-%m-%d")),
                    start_time=datetime.now().isoformat(),
                    end_time=datetime.now().isoformat(),
                    status="completed",
                    services_data=state.get("collected_data"),
                    analysis_result=state.get("analysis_result"),
                    notion_page_url=state.get("notion_page_url"),
                    error_message=None,
                    execution_duration=0
                )

                log_id = registry.store_daily_briefing_log(log_record)

                state["final_result"] = {
                    "status": "success",
                    "log_id": log_id,
                    "notion_page_url": state.get("notion_page_url"),
                    "message": "Daily briefing completed successfully"
                }

                logger.info(f"Daily briefing log stored: {log_id}")

            elif request_type == "extract":
                # Extract: Return messages from retrieved conversations (no DB write)
                context_data = state.get("context_data", {})
                conversations = context_data.get("conversations", [])
                
                # Extract messages from conversations
                all_messages = []
                for conv in conversations:
                    messages = conv.payload if hasattr(conv, 'payload') else []
                    all_messages.extend(messages)
                
                state["final_result"] = {
                    "status": "success",
                    "messages": all_messages,
                    "metadata": {
                        "total_messages": len(all_messages),
                        "filtered_messages": len(all_messages),
                        "conversations_found": len(conversations),
                        "last_activity": datetime.now().isoformat()
                    }
                }
                
                logger.info(f"Extract completed: {len(all_messages)} messages from {len(conversations)} conversations")
                
            else:
                # Conversation log handling
                summary_result = state["summary_result"]

                # Prepare data for storage
                cr_data = {
                    "type": summary_result["type"],
                    "content": state["content"],
                    "summary": summary_result,
                    "timestamp": datetime.now().isoformat(),
                    "agent_version": "1.0.0"
                }

                # Write to Context Registry
                write_result = await self.cr_client.write_context(cr_data)

                state["final_result"] = {
                    "status": "success",
                    "cr_result": write_result,
                    "summary": summary_result,
                    "message": "Data successfully processed and stored"
                }

                logger.info(f"Results stored: {write_result.get('id', 'unknown')}")

        except Exception as e:
            logger.error(f"Context writing failed: {str(e)}")
            state["error"] = f"Context writing failed: {str(e)}"
            state["final_result"] = {
                "status": "error",
                "message": str(e)
            }

        return state
    
    async def process_request(self, request_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for processing requests"""
        logger.info(f"Processing {request_type} request")
        
        # Initialize state
        initial_state = AgentState(
            request_type=request_type,
            content=content,
            plan=None,
            context_data=None,
            summary_result=None,
            collected_data=None,
            analysis_result=None,
            notion_page_url=None,
            final_result=None,
            error=None
        )
        
        try:
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            if final_state.get("error"):
                logger.error(f"Workflow failed: {final_state['error']}")
                return {
                    "status": "error",
                    "error": final_state["error"]
                }
            
            result = final_state.get("final_result", {})
            logger.info(f"Workflow completed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                "status": "error",
                "error": f"Workflow execution failed: {str(e)}"
            }

# Global orchestrator instance
orchestrator = AgentOrchestrator()

async def main():
    """Main entry point for testing the orchestrator"""
    logger.info("Starting Agent Orchestrator")
    
    # Test conversation logging
    test_conversation = {
        "session_id": "test_session_001",
        "user_message": "What is the capital of France?",
        "assistant_response": "The capital of France is Paris.",
        "platform": "claude",
        "timestamp": datetime.now().isoformat()
    }
    
    result = await orchestrator.process_request("conversation_log", test_conversation)
    print("Conversation logging result:", result)
    
    # Test content extraction
    test_extract = {
        "content": "The meeting discussed three main topics: budget planning, team restructuring, and new product launch. Action items include reviewing Q4 budget by Friday and scheduling team interviews next week.",
        "extract_type": "action_items"
    }
    
    result = await orchestrator.process_request("extract", test_extract)
    print("Content extraction result:", result)

if __name__ == "__main__":
    asyncio.run(main())