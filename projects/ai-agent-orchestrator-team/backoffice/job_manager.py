#!/usr/bin/env python3
"""
Generic Job Manager for Backoffice
Handles local job scheduling with missed job detection
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz

if TYPE_CHECKING:
    from .job_executor import JobExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobManager:
    """Generic Job Manager with missed job detection"""
    
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = Path(db_path)
        self.scheduler = AsyncIOScheduler()
        self.executor: Optional['JobExecutor'] = None
        self.running_jobs: Dict[str, Dict] = {}
        
        # Initialize database
        self.init_db()
        
    def set_executor(self, executor: 'JobExecutor'):
        """Set job executor"""
        self.executor = executor
        
    async def start(self):
        """Start the job manager and scheduler"""
        # Start scheduler
        self.scheduler.start()
        logger.info("Job scheduler started")
        
        # Check for missed jobs on startup
        await self.check_missed_jobs_on_startup()
        
    def init_db(self):
        """Initialize job database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    params TEXT,  -- JSON
                    schedule TEXT,  -- cron expression or None
                    enabled BOOLEAN DEFAULT TRUE,
                    is_ambient BOOLEAN DEFAULT FALSE,
                    created_by TEXT DEFAULT 'backoffice_ui',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_run DATETIME,
                    last_success DATETIME,
                    next_run DATETIME,
                    status TEXT DEFAULT 'pending',
                    result TEXT,  -- JSON
                    error_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3
                )
            """)
            
            # Create job_executions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_executions (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    status TEXT NOT NULL, -- 'running', 'success', 'failed'
                    result TEXT,  -- JSON
                    error_message TEXT,
                    duration_seconds INTEGER,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_type ON jobs(job_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_enabled ON jobs(enabled)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule ON jobs(schedule)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_job_id ON job_executions(job_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_started_at ON job_executions(started_at)")
            
            conn.commit()
            logger.info("Job database initialized")
    
    async def check_missed_jobs_on_startup(self):
        """Check for missed jobs when server starts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    WHERE enabled = TRUE 
                    AND schedule IS NOT NULL 
                    AND schedule != ''
                """)
                jobs = cursor.fetchall()
            
            missed_jobs = []
            # Use timezone-aware datetime
            local_tz = pytz.timezone('Asia/Seoul')
            current_time = datetime.now(local_tz)
            today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            for job in jobs:
                last_run = None
                if job["last_success"]:
                    last_run = datetime.fromisoformat(job["last_success"])
                    # If last_run is naive, make it timezone-aware
                    if last_run.tzinfo is None:
                        last_run = local_tz.localize(last_run)
                
                # Parse cron schedule to check if job should have run today
                try:
                    cron_trigger = CronTrigger.from_crontab(job["schedule"], timezone=local_tz)
                    
                    # Get next scheduled time from today's start  
                    next_fire_time = cron_trigger.get_next_fire_time(None, today_start)
                    
                    # If scheduled time is in the past and we haven't run it today
                    if (next_fire_time and next_fire_time <= current_time and 
                        (not last_run or last_run.date() < current_time.date())):
                        
                        missed_jobs.append({
                            "id": job["id"],
                            "name": job["name"],
                            "job_type": job["job_type"],
                            "scheduled_time": next_fire_time,
                            "params": json.loads(job["params"]) if job["params"] else {}
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to parse schedule for job {job['id']}: {e}")
                    continue
            
            if missed_jobs:
                logger.info(f"Found {len(missed_jobs)} missed jobs, executing now...")
                for missed_job in missed_jobs:
                    logger.info(f"Executing missed job: {missed_job['name']} "
                              f"(scheduled at {missed_job['scheduled_time']})")
                    
                    # Execute missed job
                    await self._execute_job_internal(
                        missed_job["id"],
                        missed_job["job_type"],
                        missed_job["params"],
                        is_missed_job=True
                    )
                    
                    # Small delay between jobs
                    await asyncio.sleep(2)
            else:
                logger.info("No missed jobs found")
                
        except Exception as e:
            logger.error(f"Failed to check missed jobs: {e}")
    
    async def create_job(
        self,
        name: str,
        job_type: str,
        params: Dict[str, Any],
        schedule: Optional[str] = None,
        is_ambient: bool = False,
        created_by: str = "backoffice_ui",
        max_retries: int = 3
    ) -> str:
        """Create a new job"""
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Calculate next run time if scheduled
        next_run = None
        if schedule:
            try:
                cron_trigger = CronTrigger.from_crontab(schedule)
                next_run = cron_trigger.get_next_fire_time(None, datetime.now())
            except Exception as e:
                logger.error(f"Invalid cron expression '{schedule}': {e}")
                raise ValueError(f"Invalid cron expression: {schedule}")
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (
                    id, name, job_type, params, schedule, is_ambient, 
                    created_by, next_run, max_retries
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id, name, job_type, json.dumps(params), schedule,
                is_ambient, created_by, next_run.isoformat() if next_run else None,
                max_retries
            ))
        
        # Add to scheduler if scheduled
        if schedule:
            self.scheduler.add_job(
                self._execute_job,
                CronTrigger.from_crontab(schedule),
                args=[job_id],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Job '{name}' scheduled: {schedule}")
        
        logger.info(f"Job created: {job_id} - {name}")
        return job_id
    
    async def create_or_enable_ambient_job(
        self,
        job_type: str,
        name: str,
        schedule: str,
        params: Dict[str, Any]
    ) -> str:
        """Create or enable ambient job (for toggle functionality)"""
        # Check if ambient job already exists (by name, not just job_type)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id FROM jobs WHERE name = ? AND is_ambient = TRUE",
                (name,)
            )
            existing_job = cursor.fetchone()

        if existing_job:
            # Enable existing job
            await self.enable_job(existing_job["id"])
            return existing_job["id"]
        else:
            # Create new ambient job
            return await self.create_job(
                name=name,
                job_type=job_type,
                params=params,
                schedule=schedule,
                is_ambient=True
            )
    
    async def disable_job_by_name(self, name: str):
        """Disable ambient job by name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id FROM jobs WHERE name = ? AND is_ambient = TRUE AND enabled = TRUE",
                (name,)
            )
            jobs = cursor.fetchall()

        for job in jobs:
            await self.disable_job(job["id"])

    async def disable_job_by_type(self, job_type: str):
        """Disable all jobs of specific type (legacy method)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id FROM jobs WHERE job_type = ? AND is_ambient = TRUE AND enabled = TRUE",
                (job_type,)
            )
            jobs = cursor.fetchall()

        for job in jobs:
            await self.disable_job(job["id"])
    
    async def enable_job(self, job_id: str):
        """Enable a job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE jobs SET enabled = TRUE WHERE id = ?",
                (job_id,)
            )
            
            # Get job info for rescheduling
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,)
            )
            job = cursor.fetchone()
        
        # Reschedule if has schedule
        if job and job["schedule"]:
            self.scheduler.add_job(
                self._execute_job,
                CronTrigger.from_crontab(job["schedule"]),
                args=[job_id],
                id=job_id,
                replace_existing=True
            )
            
        logger.info(f"Job enabled: {job_id}")
    
    async def disable_job(self, job_id: str):
        """Disable a job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE jobs SET enabled = FALSE WHERE id = ?",
                (job_id,)
            )
        
        # Remove from scheduler
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass  # Job might not be in scheduler
            
        logger.info(f"Job disabled: {job_id}")
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        try:
            # Remove from scheduler
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            
            # Remove from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM jobs WHERE id = ?",
                    (job_id,)
                )
                deleted = cursor.rowcount > 0
            
            if deleted:
                logger.info(f"Job deleted: {job_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    async def trigger_job(self, job_id: str) -> Dict[str, Any]:
        """Manually trigger a job"""
        # Get job info
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,)
            )
            job = cursor.fetchone()
        
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        params = json.loads(job["params"]) if job["params"] else {}
        
        # Execute job
        return await self._execute_job_internal(
            job_id, job["job_type"], params, is_manual=True
        )
    
    async def _execute_job(self, job_id: str):
        """Internal job execution for scheduler"""
        # Get job info
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE id = ? AND enabled = TRUE",
                (job_id,)
            )
            job = cursor.fetchone()
        
        if not job:
            logger.warning(f"Job not found or disabled: {job_id}")
            return
        
        params = json.loads(job["params"]) if job["params"] else {}
        await self._execute_job_internal(job_id, job["job_type"], params)
    
    async def _execute_job_internal(
        self,
        job_id: str,
        job_type: str,
        params: Dict[str, Any],
        is_manual: bool = False,
        is_missed_job: bool = False
    ) -> Dict[str, Any]:
        """Internal job execution logic"""
        if not self.executor:
            raise RuntimeError("Job executor not set")
        
        start_time = datetime.now()
        
        # Start execution tracking
        execution_id = await self.start_execution(job_id)
        
        # Update job status to running
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE jobs SET status = 'running' WHERE id = ?",
                (job_id,)
            )
        
        # Track running job
        self.running_jobs[job_id] = {
            "start_time": start_time,
            "is_manual": is_manual,
            "is_missed_job": is_missed_job,
            "execution_id": execution_id
        }
        
        try:
            logger.info(f"Executing job {job_id} (type: {job_type})")
            
            # Execute job
            result = await self.executor.execute(job_type, params)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Update job as successful
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE jobs SET 
                        status = 'completed',
                        last_run = ?,
                        last_success = ?,
                        result = ?,
                        error_count = 0
                    WHERE id = ?
                """, (
                    end_time.isoformat(),
                    end_time.isoformat(), 
                    json.dumps(result),
                    job_id
                ))
            
            # Complete execution tracking
            await self.complete_execution(execution_id, True, result)
            
            logger.info(f"Job {job_id} completed successfully in {duration:.1f}s")
            
            return {
                "success": True,
                "duration": duration,
                "result": result
            }
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"Job {job_id} failed: {e}")
            
            # Complete execution tracking with error
            await self.complete_execution(execution_id, False, error_message=str(e))
            
            # Update error count
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE jobs SET 
                        status = 'failed',
                        last_run = ?,
                        result = ?,
                        error_count = error_count + 1
                    WHERE id = ?
                """, (
                    end_time.isoformat(),
                    json.dumps({"error": str(e)}),
                    job_id
                ))
            
            return {
                "success": False,
                "duration": duration,
                "error": str(e)
            }
            
        finally:
            # Remove from running jobs
            self.running_jobs.pop(job_id, None)
    
    async def list_jobs(self, job_type: Optional[str] = None, active_only: bool = False) -> List[Dict]:
        """List jobs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type)
                
            if active_only:
                query += " AND enabled = TRUE"
            
            query += " ORDER BY created_at DESC"
            
            cursor = conn.execute(query, params)
            jobs = cursor.fetchall()
        
        result = []
        for job in jobs:
            job_dict = dict(job)
            job_dict["params"] = json.loads(job_dict["params"]) if job_dict["params"] else {}
            job_dict["result"] = json.loads(job_dict["result"]) if job_dict["result"] else None
            result.append(job_dict)
        
        return result
    
    async def list_custom_jobs(self) -> List[Dict]:
        """List only custom (non-ambient) jobs"""
        return await self.list_jobs(active_only=False)
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,)
            )
            job = cursor.fetchone()
        
        if not job:
            return {"error": "Job not found"}
        
        job_dict = dict(job)
        job_dict["params"] = json.loads(job_dict["params"]) if job_dict["params"] else {}
        job_dict["result"] = json.loads(job_dict["result"]) if job_dict["result"] else None
        job_dict["is_running"] = job_id in self.running_jobs
        
        if job_dict["is_running"]:
            running_info = self.running_jobs[job_id]
            job_dict["running_duration"] = (
                datetime.now() - running_info["start_time"]
            ).total_seconds()
        
        return job_dict
    
    def is_job_type_enabled(self, job_type: str) -> bool:
        """Check if job type is enabled"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE job_type = ? AND is_ambient = TRUE AND enabled = TRUE",
                (job_type,)
            )
            count = cursor.fetchone()[0]
        
        return count > 0
    
    async def get_ambient_jobs_status(self) -> Dict[str, bool]:
        """Get status of all ambient jobs"""
        status = {}

        # Check each ambient job individually by name
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Knowledge Cards
            cursor.execute("""
                SELECT COUNT(*) FROM jobs
                WHERE name = 'Knowledge Reinforcement Cards' AND enabled = 1 AND is_ambient = 1
            """)
            status["knowledge_cards"] = cursor.fetchone()[0] > 0

            # Daily Briefing
            cursor.execute("""
                SELECT COUNT(*) FROM jobs
                WHERE name = 'Daily Briefing Report' AND enabled = 1 AND is_ambient = 1
            """)
            status["daily_briefing"] = cursor.fetchone()[0] > 0

        return status
    
    async def start_execution(self, job_id: str) -> str:
        """Start execution tracking and return execution_id"""
        execution_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO job_executions (id, job_id, started_at, status)
                VALUES (?, ?, ?, 'running')
            """, (execution_id, job_id, started_at))
            conn.commit()
        
        logger.info(f"Started execution tracking for job {job_id}, execution_id: {execution_id}")
        return execution_id
    
    async def complete_execution(self, execution_id: str, success: bool, result: Any = None, error_message: str = None):
        """Complete execution tracking"""
        completed_at = datetime.now()
        status = "success" if success else "failed"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT started_at FROM job_executions WHERE id = ?",
                (execution_id,)
            )
            started_at_str = cursor.fetchone()
            
            if started_at_str:
                started_at = datetime.fromisoformat(started_at_str[0])
                duration = int((completed_at - started_at).total_seconds())
                
                conn.execute("""
                    UPDATE job_executions 
                    SET completed_at = ?, status = ?, result = ?, error_message = ?, duration_seconds = ?
                    WHERE id = ?
                """, (completed_at.isoformat(), status, json.dumps(result) if result else None, 
                      error_message, duration, execution_id))
                conn.commit()
        
        logger.info(f"Completed execution {execution_id} with status: {status}")
    
    async def get_job_executions(self, job_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM job_executions 
                WHERE job_id = ? 
                ORDER BY started_at DESC 
                LIMIT ?
            """, (job_id, limit))
            
            executions = []
            for row in cursor.fetchall():
                execution = dict(row)
                if execution["result"]:
                    try:
                        execution["result"] = json.loads(execution["result"])
                    except json.JSONDecodeError:
                        pass
                executions.append(execution)
            
            return executions
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,)
            )
            job = cursor.fetchone()
        
        if not job:
            return None
        
        job_dict = dict(job)
        job_dict["params"] = json.loads(job_dict["params"]) if job_dict["params"] else {}
        return job_dict