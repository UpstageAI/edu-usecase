#!/usr/bin/env python3
"""
Backoffice UI for Context Registry viewing and job management
FastAPI-based web interface with HTML templates
"""

import asyncio
import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Import Job Management components
from job_manager import JobManager
from job_executor import JobExecutor

# Import Agent Orchestrator
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from agent_orchestrator.orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Job Management System - global variables
job_manager = None
job_executor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    global job_manager, job_executor

    # Startup
    logger.info("Initializing Agent Orchestrator...")
    orchestrator = AgentOrchestrator()

    logger.info("Initializing Job Management System...")
    job_manager = JobManager(db_path="jobs.db")
    job_executor = JobExecutor(registry=None, orchestrator=orchestrator)
    job_manager.set_executor(job_executor)
    await job_manager.start()

    logger.info("Backoffice startup complete")

    yield

    # Shutdown (if needed)
    # await job_manager.stop()

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Context Registry Backoffice",
    version="1.0.0",
    lifespan=lifespan
)

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Context Registry DB path
CONTEXT_DB_PATH = Path(__file__).parent.parent / "context_registry" / "context_registry.db"

# Context Registry DB helper functions
def get_context_db_stats():
    """Get Context Registry database statistics"""
    try:
        with sqlite3.connect(CONTEXT_DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Count conversations
            cursor.execute("SELECT COUNT(*) FROM conversation")
            conversation_count = cursor.fetchone()[0]
            
            # Count by source
            cursor.execute("SELECT source, COUNT(*) FROM conversation GROUP BY source")
            source_stats = dict(cursor.fetchall())
            
            # Get last conversation date
            cursor.execute("SELECT MAX(created_at) FROM conversation")
            last_updated = cursor.fetchone()[0]
            
            # Get database size
            db_size = CONTEXT_DB_PATH.stat().st_size if CONTEXT_DB_PATH.exists() else 0
            
            return {
                "total_conversations": conversation_count,
                "source_stats": source_stats,
                "last_updated": last_updated,
                "db_size_bytes": db_size,
                "db_size_mb": round(db_size / (1024 * 1024), 2)
            }
    except Exception as e:
        logger.error(f"Failed to get DB stats: {e}")
        return {
            "total_conversations": 0,
            "source_stats": {},
            "last_updated": None,
            "db_size_bytes": 0,
            "db_size_mb": 0
        }

def get_conversations(limit=50, source_filter=None, date_filter=None, sort_order="desc"):
    """Get conversations from Context Registry DB with source and date filtering"""
    try:
        with sqlite3.connect(CONTEXT_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM conversation WHERE deleted = FALSE"
            params = []
            
            # Source filter
            if source_filter:
                query += " AND source = ?"
                params.append(source_filter)
            
            # Date filter
            if date_filter and date_filter != "all":
                if date_filter == "today":
                    query += " AND created_at >= date('now')"
                else:
                    # Assume it's a number of days
                    query += " AND created_at >= date('now', ?)"
                    params.append(f'-{date_filter} days')
            
            # Sort order
            order = "DESC" if sort_order == "desc" else "ASC"
            query += f" ORDER BY created_at {order} LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            conversations = []
            for row in cursor.fetchall():
                conv = dict(row)
                # Parse JSON payload
                if conv.get('payload'):
                    try:
                        conv['payload'] = json.loads(conv['payload'])
                    except json.JSONDecodeError:
                        conv['payload'] = []
                else:
                    conv['payload'] = []
                
                # Extract all messages from payload (preserve full conversation)
                conv['messages'] = []
                conv['user_message'] = ""
                conv['assistant_response'] = ""
                conv['platform'] = conv.get('source', 'unknown')
                conv['session_id'] = conv.get('channel', 'unknown')
                
                if isinstance(conv['payload'], list):
                    for msg in conv['payload']:
                        if isinstance(msg, dict):
                            role = msg.get('role', '')
                            text = msg.get('text', '')
                            timestamp = msg.get('timestamp', '')
                            
                            # Add to messages list (full conversation)
                            conv['messages'].append({
                                'role': role,
                                'text': text,
                                'timestamp': timestamp
                            })
                            
                            # Also keep first message for backward compatibility
                            if role == 'user' and not conv['user_message']:
                                conv['user_message'] = text
                            elif role == 'assistant' and not conv['assistant_response']:
                                conv['assistant_response'] = text
                
                conversations.append(conv)
            
            return conversations
    except Exception as e:
        logger.error(f"Failed to get conversations: {e}")
        return []

def get_daily_briefings(source_filter=None, date_filter=None, sort_order="desc", limit=50):
    """Get daily briefings from Context Registry DB with source and date filtering"""
    try:
        with sqlite3.connect(CONTEXT_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM daily_briefing_log WHERE 1=1"
            params = []
            
            # Date filter
            if date_filter and date_filter != "all":
                if date_filter == "today":
                    query += " AND execution_date >= date('now')"
                else:
                    # Assume it's a number of days
                    query += " AND execution_date >= date('now', ?)"
                    params.append(f'-{date_filter} days')
            
            # Sort order
            order = "DESC" if sort_order == "desc" else "ASC"
            query += f" ORDER BY execution_date {order} LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            briefings = []
            
            for row in cursor.fetchall():
                briefing = dict(row)
                
                # Parse services_data JSON
                if briefing.get('services_data'):
                    try:
                        briefing['services_data'] = json.loads(briefing['services_data'])
                    except json.JSONDecodeError:
                        briefing['services_data'] = {}
                else:
                    briefing['services_data'] = {}
                
                # Apply source filter (gmail, slack, notion)
                if source_filter and source_filter != "all":
                    services = briefing['services_data'].get('data', {})
                    source_lower = source_filter.lower()
                    
                    # Check if the specified source exists and is successful
                    if source_lower in services:
                        source_data = services[source_lower]
                        # Include only if source has successful data
                        if source_data.get('status') == 'success' and source_data.get('count', 0) > 0:
                            briefings.append(briefing)
                    # If source not found or failed, skip this briefing
                else:
                    # No source filter, include all
                    briefings.append(briefing)
            
            # Extract summary info for display
            for briefing in briefings:
                services = briefing['services_data'].get('data', {})
                briefing['gmail_count'] = services.get('gmail', {}).get('count', 0)
                briefing['slack_count'] = services.get('slack', {}).get('count', 0)
                briefing['notion_count'] = services.get('notion', {}).get('count', 0)
                briefing['gmail_status'] = services.get('gmail', {}).get('status', 'unknown')
                briefing['slack_status'] = services.get('slack', {}).get('status', 'unknown')
                briefing['notion_status'] = services.get('notion', {}).get('status', 'unknown')
            
            return briefings
    except Exception as e:
        logger.error(f"Failed to get daily briefings: {e}")
        return []

def delete_conversation(conversation_id):
    """Delete a conversation from Context Registry DB"""
    try:
        with sqlite3.connect(CONTEXT_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversation WHERE id = ?", (conversation_id,))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        return False

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page with Context Registry status"""
    db_stats = get_context_db_stats()
    job_stats = await job_manager.get_ambient_jobs_status() if job_manager else {}
    recent_conversations = get_conversations(limit=10)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "db_stats": db_stats,
        "job_stats": job_stats,
        "recent_conversations": recent_conversations
    })

@app.get("/registry", response_class=HTMLResponse)
async def registry_page(
    request: Request,
    view: str = "conversations",
    source: str = "all",
    date: str = "30",
    sort: str = "desc",
    limit: int = 50
):
    """Context Registry management page with unified filtering"""
    
    if view == "briefings":
        # Get daily briefings
        data = get_daily_briefings(
            source_filter=source if source != "all" else None,
            date_filter=date,
            sort_order=sort,
            limit=limit
        )
        conversations = []  # Empty for briefings view
    else:
        # Get conversations (default)
        conversations = get_conversations(
            limit=limit,
            source_filter=source if source != "all" else None,
            date_filter=date,
            sort_order=sort
        )
        data = []  # Empty for conversations view
    
    db_stats = get_context_db_stats()
    
    return templates.TemplateResponse("registry.html", {
        "request": request,
        "view": view,
        "source": source,
        "date": date,
        "sort": sort,
        "limit": limit,
        "conversations": conversations,
        "briefings": data,
        "db_stats": db_stats,
        "available_sources": list(db_stats["source_stats"].keys())
    })


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    """Job management page"""
    ambient_status = await job_manager.get_ambient_jobs_status()
    custom_jobs = await job_manager.list_custom_jobs()
    
    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "ambient_status": ambient_status,
        "custom_jobs": custom_jobs
    })

@app.get("/api/stats")
async def api_stats():
    """API endpoint for Context Registry statistics"""
    return get_context_db_stats()

@app.get("/api/conversations")
async def api_conversations(source: str = None, limit: int = 100):
    """API endpoint for conversations"""
    return get_conversations(limit=limit, source_filter=source)

@app.delete("/api/conversations/{conversation_id}")
async def api_delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        success = delete_conversation(conversation_id)
        if success:
            return {"success": True, "message": "Conversation deleted"}
        else:
            return {"success": False, "error": "Conversation not found"}
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        return {"success": False, "error": str(e)}

# Job Management API Endpoints

@app.post("/api/ambient-jobs/toggle")
async def toggle_ambient_job(request: Request):
    """Toggle ambient job on/off"""
    try:
        data = await request.json()
        job_type = data["job_type"]
        enabled = data["enabled"]
        
        # Predefined ambient jobs
        parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID", "")
        logger.info(f"DEBUG: Reading NOTION_PARENT_PAGE_ID in toggle_ambient_job: '{parent_page_id}'")

        AMBIENT_JOBS = {
            "knowledge_cards": {
                "name": "Knowledge Reinforcement Cards",
                "job_type": "ambient",
                "schedule": "30 7 * * *",
                "params": {"max_cards": 5}
            },
            "daily_briefing": {
                "name": "Daily Briefing Report",
                "job_type": "ambient",
                "schedule": "0 7 * * *",  # 07:00 KST daily
                "params": {
                    "services": ["gmail", "slack", "notion"],
                    "hours": 24,
                    "parent_page_id": parent_page_id,
                    "notion_database_id": os.getenv("NOTION_DATABASE_ID", "")
                }
            }
        }
        
        if job_type not in AMBIENT_JOBS:
            return JSONResponse({"success": False, "error": "Unknown job type"})
        
        if enabled:
            job_config = AMBIENT_JOBS[job_type]
            job_id = await job_manager.create_or_enable_ambient_job(
                job_type=job_config["job_type"],
                name=job_config["name"],
                schedule=job_config["schedule"],
                params=job_config["params"]
            )
            message = f"{job_type} activated"
        else:
            job_config = AMBIENT_JOBS[job_type]
            await job_manager.disable_job_by_name(job_config["name"])
            message = f"{job_type} deactivated"
        
        return JSONResponse({
            "success": True,
            "message": message,
            "job_type": job_type,
            "enabled": enabled
        })
        
    except Exception as e:
        logger.error(f"Failed to toggle ambient job: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/api/jobs")
async def list_jobs(custom_only: bool = False, job_type: str = None):
    """List jobs"""
    try:
        if custom_only:
            jobs = await job_manager.list_custom_jobs()
            # Filter non-ambient jobs
            jobs = [job for job in jobs if not job.get("is_ambient", False)]
        else:
            jobs = await job_manager.list_jobs(job_type=job_type)
        
        return JSONResponse({
            "success": True,
            "jobs": jobs
        })
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/jobs")
async def create_job(request: Request):
    """Create custom job"""
    try:
        data = await request.json()
        
        job_id = await job_manager.create_job(
            name=data["name"],
            job_type="agent",  # All cron jobs are agent type
            params=data.get("params", {}),
            schedule=data.get("schedule"),
            is_ambient=False,
            created_by="backoffice_ui"
        )
        
        return JSONResponse({
            "success": True,
            "job_id": job_id,
            "message": "Job created successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete job"""
    try:
        success = await job_manager.delete_job(job_id)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Job deleted successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Job not found or already deleted"
            })
            
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.put("/api/jobs/{job_id}")
async def update_job(job_id: str, request: Request):
    """Update job"""
    try:
        data = await request.json()
        
        # Get current job info
        job_info = await job_manager.get_job_status(job_id)
        if "error" in job_info:
            return JSONResponse({"success": False, "error": "Job not found"})
        
        # Delete old job
        await job_manager.delete_job(job_id)
        
        # Create new job with updated parameters
        new_job_id = await job_manager.create_job(
            name=data.get("name", job_info["name"]),
            job_type="agent",  # All cron jobs are agent type
            params=data.get("params", job_info["params"]),
            schedule=data.get("schedule", job_info["schedule"]),
            is_ambient=False,
            created_by="backoffice_ui"
        )
        
        return JSONResponse({
            "success": True,
            "job_id": new_job_id,
            "message": "Job updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to update job: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/jobs/{job_id}/run")
async def run_job_now(job_id: str, background_tasks: BackgroundTasks):
    """Run job immediately"""
    try:
        async def run_job():
            try:
                result = await job_manager.trigger_job(job_id)
                logger.info(f"Job {job_id} completed: {result}")
            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
        
        background_tasks.add_task(run_job)
        
        return JSONResponse({
            "success": True,
            "message": f"Job {job_id} execution started",
            "job_id": job_id
        })
        
    except Exception as e:
        logger.error(f"Failed to trigger job: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get job status"""
    try:
        status = await job_manager.get_job_status(job_id)
        
        return JSONResponse({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/jobs/trigger-by-type")
async def trigger_job_by_type(request: Request, background_tasks: BackgroundTasks):
    """Trigger job by type (for MCP tool if needed)"""
    try:
        data = await request.json()
        job_type = data["job_type"]
        
        # Find first enabled job of this type
        jobs = await job_manager.list_jobs(job_type=job_type, active_only=True)
        if not jobs:
            return JSONResponse({
                "success": False,
                "error": f"No active jobs found for type: {job_type}"
            })
        
        job = jobs[0]  # Take first active job
        
        async def run_job():
            try:
                result = await job_manager.trigger_job(job["id"])
                logger.info(f"Job {job['id']} completed: {result}")
            except Exception as e:
                logger.error(f"Job {job['id']} failed: {e}")
        
        background_tasks.add_task(run_job)
        
        return JSONResponse({
            "success": True,
            "message": f"Job {job['id']} execution started",
            "job_id": job["id"],
            "job_type": job_type
        })
        
    except Exception as e:
        logger.error(f"Failed to trigger job by type: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/api/ambient-jobs/status")
async def get_ambient_jobs_status():
    """Get ambient jobs status"""
    try:
        status = await job_manager.get_ambient_jobs_status()
        
        return JSONResponse({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        logger.error(f"Failed to get ambient jobs status: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/jobs/{job_id}/history", response_class=HTMLResponse)
async def job_history_page(job_id: str, request: Request):
    """Job execution history page"""
    try:
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        executions = await job_manager.get_job_executions(job_id, limit=50)
        
        return templates.TemplateResponse("job_history.html", {
            "request": request,
            "job": job,
            "executions": executions
        })
        
    except Exception as e:
        logger.error(f"Failed to get job history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}/executions")
async def get_job_executions_api(job_id: str, limit: int = 50):
    """Job execution history API"""
    try:
        executions = await job_manager.get_job_executions(job_id, limit)
        return JSONResponse({
            "success": True,
            "executions": executions
        })
    except Exception as e:
        logger.error(f"Failed to get job executions: {e}")
        return JSONResponse({"success": False, "error": str(e)})

async def main():
    """Main entry point"""
    logger.info("Starting Backoffice UI")
    
    # Start the server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8003,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
