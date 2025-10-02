#!/usr/bin/env python3
"""
Context Registry (CR) - SQLite-based storage for conversations and extract results
Implements the three main tables: conversation, extract_result, action_log
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConversationRecord:
    """Data model for conversation table"""
    id: Optional[str]
    record_type: str = "conversation"
    source: str = "unknown"
    channel: str = ""
    payload: Dict[str, Any] = None  # messages array
    timestamp: str = ""
    actor: str = "ao"
    deleted: bool = False
    created_at: Optional[str] = None

@dataclass
class ExtractResultRecord:
    """Data model for extract_result table"""
    id: Optional[str]
    content: str
    extract_type: str
    result_data: Dict[str, Any]
    confidence: float
    context_refs: Optional[List[str]] = None
    timestamp: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class ActionLogRecord:
    """Data model for action_log table"""
    id: Optional[str]
    action_type: str
    description: str
    actor: str  # "agent", "user", "system"
    target_id: Optional[str] = None
    target_type: Optional[str] = None  # "conversation", "extract_result"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

@dataclass
class DailyBriefingLogRecord:
    """Data model for daily_briefing_log table"""
    id: Optional[str]
    execution_date: str
    start_time: str
    end_time: Optional[str] = None
    status: str = "running"
    services_data: Optional[Dict[str, Any]] = None
    analysis_result: Optional[Dict[str, Any]] = None
    notion_page_url: Optional[str] = None
    error_message: Optional[str] = None
    execution_duration: Optional[int] = None
    created_at: Optional[str] = None

class ContextRegistry:
    """Main Context Registry class with SQLite storage"""
    
    def __init__(self, db_path: str = "context_registry.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create conversation table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation (
                    id TEXT PRIMARY KEY,
                    record_type TEXT DEFAULT 'conversation',
                    source TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    payload TEXT NOT NULL,  -- JSON string (messages array)
                    timestamp TEXT NOT NULL,
                    actor TEXT DEFAULT 'ao',
                    deleted BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for conversation table
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_channel ON conversation(channel)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_source ON conversation(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_timestamp ON conversation(timestamp)")
            
            # Create extract_result table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS extract_result (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    extract_type TEXT NOT NULL,
                    result_data TEXT NOT NULL,  -- JSON string
                    confidence REAL NOT NULL,
                    context_refs TEXT,  -- JSON array of reference IDs
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for extract_result table
            conn.execute("CREATE INDEX IF NOT EXISTS idx_extract_type ON extract_result(extract_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_extract_timestamp ON extract_result(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_extract_confidence ON extract_result(confidence)")
            
            # Create action_log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_log (
                    id TEXT PRIMARY KEY,
                    action_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    target_id TEXT,
                    target_type TEXT,
                    metadata TEXT,  -- JSON string
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for action_log table
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_type ON action_log(action_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_actor ON action_log(actor)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_target_type ON action_log(target_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_timestamp ON action_log(timestamp)")
            
            # Create daily_briefing_log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_briefing_log (
                    id TEXT PRIMARY KEY,
                    execution_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL, -- 'running', 'completed', 'failed'
                    services_data TEXT, -- JSON string of collected raw data
                    analysis_result TEXT, -- JSON string of LLaMA analysis
                    notion_page_url TEXT,
                    error_message TEXT,
                    execution_duration INTEGER, -- seconds
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for daily_briefing_log table
            conn.execute("CREATE INDEX IF NOT EXISTS idx_briefing_execution_date ON daily_briefing_log(execution_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_briefing_status ON daily_briefing_log(status)")
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def _generate_id(self, prefix: str = "cr") -> str:
        """Generate unique ID with timestamp"""
        return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def store_conversation(self, record: ConversationRecord) -> str:
        """Store conversation record and return generated ID"""
        if not record.id:
            record.id = self._generate_id("conv")
        
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute("""
                    INSERT INTO conversation 
                    (id, record_type, source, channel, payload, timestamp, actor, deleted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.id,
                    record.record_type,
                    record.source,
                    record.channel,
                    json.dumps(record.payload) if record.payload else '[]',
                    record.timestamp,
                    record.actor,
                    record.deleted
                ))
                
                # Log the action using same connection
                self._log_action_with_conn(
                    conn=conn,
                    action_type="conversation_stored",
                    description=f"Stored conversation from {record.source}",
                    actor="agent",
                    target_id=record.id,
                    target_type="conversation"
                )
                
                conn.commit()
                logger.info(f"Conversation stored: {record.id}")
                return record.id
                
        except Exception as e:
            logger.error(f"Failed to store conversation: {str(e)}")
            raise
    
    def store_extract_result(self, record: ExtractResultRecord) -> str:
        """Store extract result record and return generated ID"""
        if not record.id:
            record.id = self._generate_id("ext")
        
        if not record.timestamp:
            record.timestamp = datetime.now().isoformat()
        
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute("""
                    INSERT INTO extract_result 
                    (id, content, extract_type, result_data, confidence, context_refs, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.id,
                    record.content,
                    record.extract_type,
                    json.dumps(record.result_data),
                    record.confidence,
                    json.dumps(record.context_refs) if record.context_refs else None,
                    record.timestamp
                ))
                
                # Log the action using same connection
                self._log_action_with_conn(
                    conn=conn,
                    action_type="extract_result_stored",
                    description=f"Stored {record.extract_type} extraction result",
                    actor="agent",
                    target_id=record.id,
                    target_type="extract_result"
                )
                
                conn.commit()
                logger.info(f"Extract result stored: {record.id}")
                return record.id
                
        except Exception as e:
            logger.error(f"Failed to store extract result: {str(e)}")
            raise
    
    def store_daily_briefing_log(self, record: DailyBriefingLogRecord) -> str:
        """Store daily briefing log record and return generated ID"""
        if not record.id:
            record.id = self._generate_id("brief")

        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute("""
                    INSERT INTO daily_briefing_log
                    (id, execution_date, start_time, end_time, status, services_data,
                     analysis_result, notion_page_url, error_message, execution_duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.id,
                    record.execution_date,
                    record.start_time,
                    record.end_time,
                    record.status,
                    json.dumps(record.services_data) if record.services_data else None,
                    json.dumps(record.analysis_result) if record.analysis_result else None,
                    record.notion_page_url,
                    record.error_message,
                    record.execution_duration
                ))

                # Log the action using same connection
                self._log_action_with_conn(
                    conn=conn,
                    action_type="daily_briefing_log_stored",
                    description=f"Stored daily briefing log for {record.execution_date} with status {record.status}",
                    actor="agent",
                    target_id=record.id,
                    target_type="daily_briefing_log"
                )

                conn.commit()
                logger.info(f"Daily briefing log stored: {record.id}")
                return record.id

        except Exception as e:
            logger.error(f"Failed to store daily briefing log: {str(e)}")
            raise

    def _log_action_with_conn(self, conn, action_type: str, description: str, actor: str, 
                             target_id: str = None, target_type: str = None, 
                             metadata: Dict[str, Any] = None):
        """Internal method to log actions using existing connection"""
        action_id = self._generate_id("act")
        
        try:
            conn.execute("""
                INSERT INTO action_log 
                (id, action_type, description, actor, target_id, target_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                action_id,
                action_type,
                description,
                actor,
                target_id,
                target_type,
                json.dumps(metadata) if metadata else None
            ))
        except Exception as e:
            logger.error(f"Failed to log action: {str(e)}")
    
    def _log_action(self, action_type: str, description: str, actor: str, 
                   target_id: str = None, target_type: str = None, 
                   metadata: Dict[str, Any] = None):
        """Internal method to log actions (creates new connection)"""
        action_id = self._generate_id("act")
        
        try:
            # Use timeout to prevent database lock issues
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute("""
                    INSERT INTO action_log 
                    (id, action_type, description, actor, target_id, target_type, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    action_id,
                    action_type,
                    description,
                    actor,
                    target_id,
                    target_type,
                    json.dumps(metadata) if metadata else None
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log action: {str(e)}")
    
    def get_conversations(self, channel: str = None, source: str = None, 
                         limit: int = 100) -> List[ConversationRecord]:
        """Retrieve conversations with optional filtering"""
        query = "SELECT * FROM conversation WHERE deleted = FALSE"
        params = []
        
        if channel:
            query += " AND channel = ?"
            params.append(channel)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                conversations = []
                for row in rows:
                    conv = ConversationRecord(
                        id=row["id"],
                        record_type=row["record_type"],
                        source=row["source"],
                        channel=row["channel"],
                        payload=json.loads(row["payload"]) if row["payload"] else [],
                        timestamp=row["timestamp"],
                        actor=row["actor"],
                        deleted=bool(row["deleted"]),
                        created_at=row["created_at"]
                    )
                    conversations.append(conv)
                
                return conversations
                
        except Exception as e:
            logger.error(f"Failed to retrieve conversations: {str(e)}")
            return []

    def delete_conversation(self, conversation_id: str, actor: str = "system") -> bool:
        """Soft delete a conversation record"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE conversation
                    SET deleted = TRUE
                    WHERE id = ?
                """, (conversation_id,))

                if cursor.rowcount == 0:
                    logger.warning(f"Conversation not found for deletion: {conversation_id}")
                    return False

                # Log the action
                self._log_action(
                    action_type="conversation_deleted",
                    description=f"Soft deleted conversation {conversation_id}",
                    actor=actor,
                    target_id=conversation_id,
                    target_type="conversation"
                )

                logger.info(f"Soft deleted conversation: {conversation_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {str(e)}")
            raise
    
    def get_extract_results(self, extract_type: str = None, 
                           limit: int = 100) -> List[ExtractResultRecord]:
        """Retrieve extract results with optional filtering"""
        query = "SELECT * FROM extract_result WHERE 1=1"
        params = []
        
        if extract_type:
            query += " AND extract_type = ?"
            params.append(extract_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    result = ExtractResultRecord(
                        id=row["id"],
                        content=row["content"],
                        extract_type=row["extract_type"],
                        result_data=json.loads(row["result_data"]),
                        confidence=row["confidence"],
                        context_refs=json.loads(row["context_refs"]) if row["context_refs"] else None,
                        timestamp=row["timestamp"],
                        created_at=row["created_at"]
                    )
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to retrieve extract results: {str(e)}")
            return []
    
    def get_action_logs(self, action_type: str = None, actor: str = None, 
                       limit: int = 100) -> List[ActionLogRecord]:
        """Retrieve action logs with optional filtering"""
        query = "SELECT * FROM action_log WHERE 1=1"
        params = []
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        if actor:
            query += " AND actor = ?"
            params.append(actor)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                logs = []
                for row in rows:
                    log = ActionLogRecord(
                        id=row["id"],
                        action_type=row["action_type"],
                        description=row["description"],
                        actor=row["actor"],
                        target_id=row["target_id"],
                        target_type=row["target_type"],
                        metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                        timestamp=row["timestamp"]
                    )
                    logs.append(log)
                
                return logs
                
        except Exception as e:
            logger.error(f"Failed to retrieve action logs: {str(e)}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count conversations
                cursor.execute("SELECT COUNT(*) FROM conversation")
                conv_count = cursor.fetchone()[0]
                
                # Count extract results
                cursor.execute("SELECT COUNT(*) FROM extract_result")
                extract_count = cursor.fetchone()[0]
                
                # Count action logs
                cursor.execute("SELECT COUNT(*) FROM action_log")
                action_count = cursor.fetchone()[0]
                
                # Get source distribution
                cursor.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM conversation 
                    WHERE deleted = FALSE
                    GROUP BY source
                """)
                source_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Get extract type distribution
                cursor.execute("""
                    SELECT extract_type, COUNT(*) as count 
                    FROM extract_result 
                    GROUP BY extract_type
                """)
                extract_type_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                return {
                    "conversations": conv_count,
                    "extract_results": extract_count,
                    "action_logs": action_count,
                    "source_distribution": source_stats,
                    "extract_type_distribution": extract_type_stats,
                    "database_path": str(self.db_path),
                    "updated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {"error": str(e)}

# Global registry instance with absolute path
_registry_dir = Path(__file__).parent
_db_path = _registry_dir / "context_registry.db"
registry = ContextRegistry(str(_db_path))

async def main():
    """Main entry point for testing the registry"""
    logger.info("Starting Context Registry")
    
    # Test conversation storage
    test_conv = ConversationRecord(
        id=None,
        record_type="conversation",
        source="claude",
        channel="claude_session_20250929_1430",
        payload={
            "messages": [
                {"role": "user", "text": "What is machine learning?", "timestamp": datetime.now().isoformat()},
                {"role": "assistant", "text": "Machine learning is a subset of artificial intelligence...", "timestamp": datetime.now().isoformat()}
            ]
        },
        timestamp=datetime.now().isoformat(),
        actor="ao",
        deleted=False
    )
    
    conv_id = registry.store_conversation(test_conv)
    print(f"Stored conversation: {conv_id}")
    
    # Test extract result storage
    test_extract = ExtractResultRecord(
        id=None,
        content="The meeting covered budget planning and team restructuring.",
        extract_type="summary",
        result_data={
            "key_points": ["Budget planning", "Team restructuring"],
            "action_items": ["Review budget", "Schedule interviews"],
            "entities": ["Budget", "Team"]
        },
        confidence=0.95,
        context_refs=[conv_id]
    )
    
    extract_id = registry.store_extract_result(test_extract)
    print(f"Stored extract result: {extract_id}")
    
    # Get statistics
    stats = registry.get_stats()
    print("Registry stats:", json.dumps(stats, indent=2))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())