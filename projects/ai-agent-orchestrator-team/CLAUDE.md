# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Agent Orchestrator with MCP (Model Context Protocol) integration - A fully functional hackathon demo system featuring LangGraph-based agent orchestration, persistent context management, and automated job scheduling. Built for Meta Llama Academy Workshop 2025.

### Core Features
- **Cross-Platform Conversation Continuity**: Save conversations from Cursor and retrieve them in Claude Desktop
- **Automated Daily Briefing**: Scheduled jobs with LangGraph workflow execution
- **Context Management**: SQLite-based persistent storage with Context Registry
- **Job Scheduling**: Cron-based background jobs with execution history tracking
- **Web-Based Management**: Complete backoffice UI for monitoring and control

### Current Status
✅ **All components fully implemented and operational** (feature/hjw/backoffice branch)
- MCP Server with conversation_log and extract tools
- Agent Orchestrator with LangGraph StateGraph workflow
- Context Registry with SQLite storage
- Backoffice UI with job scheduling and monitoring

## Commands

### Development Setup
```bash
# Install uv package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev
```

### Running the Application
```bash
# Start all components at once (recommended for demo)
uv run python start_demo.py

# Or start individual components manually:
cd mcp_server && uv run python server.py           # MCP Server (stdio)
cd agent_orchestrator && uv run python orchestrator.py  # Agent Orchestrator  
cd context_registry && uv run python registry.py        # Context Registry
cd backoffice && uv run python app.py                   # Backoffice UI

# Using dev script (alternative approach):
python scripts/dev.py demo              # Start all components
python scripts/dev.py dev mcp          # Start MCP server only
python scripts/dev.py dev orchestrator # Start orchestrator only
python scripts/dev.py dev registry     # Start registry only
python scripts/dev.py dev backoffice   # Start backoffice only
```

### Testing and Quality Assurance
```bash
# Run comprehensive test suite
uv run pytest -v
python scripts/dev.py test

# Code formatting and linting (run before committing)
uv run black .                          # Format code
uv run isort .                          # Sort imports
uv run flake8 .                         # Check style
python scripts/dev.py lint             # Run all linting tools

# Type checking (run before committing)
uv run mypy .
python scripts/dev.py typecheck

# Development utilities
python scripts/dev.py clean            # Clean build artifacts
python scripts/dev.py install          # Install dependencies
```

## Architecture

### Core Components (All Fully Implemented)

**MCP Server** (`mcp_server/server.py`)
- FastMCP-based protocol handler for client connections via stdio
- Exposes tools: `conversation_log`, `extract`
- Direct integration with Agent Orchestrator via async calls
- JSON-based request/response format with error handling

**Agent Orchestrator (AO)** (`agent_orchestrator/orchestrator.py`)
- LangGraph StateGraph workflow engine with 4-node pipeline:
  - `plan`: Analyzes requests and determines processing strategy
  - `cr_read`: Retrieves relevant context from Context Registry
  - `summarize`: Processes and summarizes conversation content (LLM-ready)
  - `cr_write`: Stores results back to Context Registry
- Supports request types: conversation_log, extract
- Full async/await implementation with error tracking

**Context Registry (CR)** (`context_registry/registry.py`)
- SQLite storage with three main tables:
  - `conversation`: Stores conversation metadata and messages array
  - `extract_result`: Stores processed extraction results with confidence scores
  - `action_log`: Tracks all system actions and operations
- Transactional writes with automatic action logging
- Query methods with filtering by channel, source, type
- Database statistics and health monitoring

**Backoffice** (`backoffice/app.py`)
- FastAPI-based web UI with Jinja2 templates
- Features:
  - Dashboard with Context Registry statistics
  - Registry viewer with conversation management
  - Job management with CRUD operations
  - Job execution history with detailed logs
  - Ambient jobs (Knowledge Cards) with toggle control
- Background job scheduler using APScheduler
  - Cron-based scheduling (e.g., Daily Digest @07:00 KST)
  - Manual job triggering ("Run Now")
  - Execution history tracking
- Direct SQLite access for Context Registry management

### Data Flow
1. **Conversation Logging**: Cursor Rules trigger conversation_log per turn
2. **MCP Relay**: MCP Client relays tool calls to MCP Server
3. **Agent Processing**: MCP Server invokes Agent Orchestrator
4. **State Processing**: AO processes through generalized state graph nodes
5. **Storage**: Results stored in Context Registry
6. **Retrieval**: Claude Desktop uses extract tool with query.text
7. **Management**: Backoffice provides UI for monitoring and management

## Team Responsibilities

### 🟡 이재범님 - Agent Orchestrator
- LangGraph StateGraph workflow implementation (4-node pipeline)
- Agent tools (CR Query/Read, Write/Insert)
- LLaMA model integration for summarization (planned)

### 🟢 이지민님 · 최현님 - MCP Server & Context Registry
- MCP protocol implementation with FastMCP
- Tool exposure: conversation_log, extract
- Context Registry SQLite storage and data models
- Webhook ingestion for Notion integration (planned)

### 🔵 황중원님 - Backoffice
- Web UI with FastAPI and Jinja2 templates
- Job management system (JobManager, JobExecutor)
- Background job scheduling with APScheduler
- Execution history tracking and monitoring
- Context Registry viewer and management interface

## API Contracts

### MCP Tool: `conversation_log`
**Input:**
```json
{
  "channel": "cursor_session_20250929_1430",
  "messages": [{"role": "user", "text": "...", "timestamp": "..."}],
  "meta": {}
}
```
**Output:**
```json
{"ok": true, "stored_ids": ["conv_id_1"]}
```

### MCP Tool: `extract`
**Input:**
```json
{
  "channel": "cursor_session_20250929_1430",
  "query": {
    "text": "피보나치 함수 시간복잡도 개선 관련 대화",
    "limit": 20
  },
  "meta": {}
}
```
**Output:**
```json
{
  "ok": true,
  "messages": [{"role": "user", "text": "...", "timestamp": "..."}],
  "metadata": {"total_count": 8, "filtered_count": 4}
}
```

## Client Configuration

Configure AI clients to connect to the MCP server:

```json
{
  "mcpServers": {
    "ai-agent-orchestrator": {
      "command": "uv",
      "args": ["run", "python", "mcp_server/server.py"],
      "env": {}
    }
  }
}
```

Place configuration in:
- Claude Desktop: See `client_configs/claude_desktop.json`
- ChatGPT Desktop: See `client_configs/chatgpt_desktop.json`
- Cursor: See `client_configs/cursor.json`

## Key Implementation Details

### Channel ID Format
- Format: `{source}_session_{timestamp}`
- Example: `cursor_session_20250929_1430` or `claude_session_20251001_0900`
- Source can be: cursor, claude, chatgpt, gemini
- Used for conversation grouping and retrieval

### MCP Tool Integration
**conversation_log tool**:
```python
# Called from AI clients to store conversations
await conversation_log(
    channel="cursor_session_20250929_1430",
    messages='[{"role": "user", "text": "...", "timestamp": "..."}]',  # JSON string
    meta='{"source": "cursor"}'  # Optional JSON string
)
```

**extract tool**:
```python
# Called to retrieve conversations by query
await extract(
    channel="cursor_session_20250929_1430",
    query='{"text": "피보나치 함수", "limit": 20}',  # JSON string
    meta='{}'  # Optional JSON string
)
```

### Agent Orchestrator Workflow
```
conversation_log: MCP → plan → cr_write → END
extract: MCP → plan → cr_read → summarize → cr_write → END
```

Each node updates AgentState with results:
- `plan`: Sets processing strategy
- `cr_read`: Retrieves context_data
- `summarize`: Generates summary_result
- `cr_write`: Stores final_result

### Job Scheduling System
**Job Types**:
- `agent`: Regular scheduled jobs (e.g., Daily Digest @07:00 KST)
- `ambient`: Background jobs (e.g., Knowledge Cards)

**Cron Schedule Format**:
```python
"30 7 * * *"  # Daily at 07:30
"0 */6 * * *"  # Every 6 hours
"0 9 * * 1-5"  # Weekdays at 09:00
```

**Job Execution Flow**:
1. APScheduler triggers job at scheduled time
2. JobManager retrieves job from jobs.db
3. JobExecutor executes job based on job_type
4. Execution record created in job_executions table
5. Job status updated with result/error

### Backoffice UI Pages
- **Dashboard** (`/`): System overview with stats
- **Registry** (`/registry`): Context Registry viewer with filters
- **Jobs** (`/jobs`): Job management with CRUD and execution
- **Job History** (`/jobs/{job_id}/history`): Detailed execution logs

## Service URLs

When all components are running:
- **Backoffice UI**: http://localhost:8003
  - Dashboard: http://localhost:8003/
  - Registry: http://localhost:8003/registry
  - Jobs: http://localhost:8003/jobs
  - API Docs: http://localhost:8003/docs (FastAPI auto-generated)
- **MCP Server**: stdio transport (for client connections via AI platforms)
- **Agent Orchestrator**: Port 8001 (internal service, no HTTP endpoints exposed)
- **Context Registry**: Port 8002 (internal service, no HTTP endpoints exposed)

## Current Branch & Development Status

**Active Branch**: `feature/hjw/backoffice`
- All core components implemented and functional
- Backoffice UI with job scheduling complete
- Context Registry with full CRUD operations
- MCP Server with conversation_log and extract tools
- Agent Orchestrator with LangGraph StateGraph

**Git Workflow**:
```bash
# Current branch
git branch  # → feature/hjw/backoffice

# Working tree status
git status  # → clean

# View implementation
git log --oneline -10  # Recent commits
```

## Meta Llama Academy Workshop 2025

**Workshop Dates**: 2025년 9월 30일 ~ 10월 2일 (3일간)
**Team**: AI Agent Orchestrator Team (5명)
**Project Goal**: MCP와 LangGraph를 활용한 실용적인 AI 에이전트 시스템 개발

### Workshop Schedule
- **Day 1 (9/30)**: Solar 기반 에이전트 설계 및 실습
- **Day 2 (10/1)**: Llama 모델 로컬 실행 및 튜닝, 프로젝트 1차 제출
- **Day 3 (10/2)**: 팀 프로젝트 수행, 멘토링, 최종 발표 및 시상

### Evaluation Criteria
- Project Impact (20점): MCP를 활용한 실용적 솔루션
- Innovation & Creativity (20점): LangGraph 기반 혁신적 워크플로우
- Technical Implementation (25점): 시스템 완성도 및 안정성
- Effective Use of AI (25점): LLaMA 모델의 효과적 활용
- Presentation & Documentation (10점): 명확한 아키텍처 설명

## Development Notes

### Project Structure
```
├── mcp_server/          # MCP protocol implementation (🟢)
│   └── server.py        # FastMCP server with conversation_log and extract tools
├── agent_orchestrator/  # LangGraph StateGraph logic (🟡)
│   └── orchestrator.py  # 4-node workflow: plan → cr_read → summarize → cr_write
├── context_registry/    # SQLite storage and models (🟢)
│   ├── registry.py      # Context Registry with 3 tables
│   └── context_registry.db  # SQLite database file
├── backoffice/         # Web UI for management (🔵)
│   ├── app.py          # FastAPI application with lifespan management
│   ├── job_manager.py  # Job scheduling with APScheduler
│   ├── job_executor.py # Job execution logic
│   ├── jobs.db         # Job database
│   └── templates/      # Jinja2 HTML templates
├── client_configs/     # AI client configurations
├── scripts/           # Development utilities
│   ├── dev.py         # Unified development commands
│   └── kill_ports.py  # Port cleanup utility
├── docs/              # Documentation and guides
│   ├── PROJECT_SPECIFICATION.md
│   ├── BACKOFFICE_IMPLEMENTATION_REVIEW.md
│   └── TEAM_GUIDE.md
├── logs/              # Application logs (auto-generated)
├── pyproject.toml     # uv package configuration
└── start_demo.py      # Demo startup orchestration
```

### Build System
- **Package Manager**: uv (modern Python package management)
- **Dependencies**: Defined in `pyproject.toml` with optional dev group
  - fastapi, uvicorn, langgraph, mcp, apscheduler, pytz
  - Dev: pytest, black, isort, flake8, mypy
- **Development Script**: `scripts/dev.py` provides unified command interface
- **Code Quality**: Black, isort, flake8, mypy configured with consistent settings
- **Logging**: Component logs stored in `logs/` directory during demo execution
- **Process Management**: `start_demo.py` handles graceful startup/shutdown of all services

### Database Schema

#### Context Registry (`context_registry.db`)
**conversation table**:
- `id`, `record_type`, `source`, `channel`, `payload` (JSON messages array)
- `timestamp`, `actor`, `deleted`, `created_at`
- Indexes: channel, source, timestamp

**extract_result table**:
- `id`, `content`, `extract_type`, `result_data` (JSON)
- `confidence`, `context_refs` (JSON array), `timestamp`, `created_at`
- Indexes: extract_type, timestamp, confidence

**action_log table**:
- `id`, `action_type`, `description`, `actor`
- `target_id`, `target_type`, `metadata` (JSON), `timestamp`
- Indexes: action_type, actor, target_type, timestamp

#### Job Manager (`backoffice/jobs.db`)
**jobs table**:
- `id`, `name`, `job_type`, `params` (JSON), `schedule` (cron)
- `enabled`, `is_ambient`, `created_by`, `created_at`
- `last_run`, `last_success`, `next_run`, `status`, `result` (JSON)
- `error_count`, `max_retries`

**job_executions table**:
- `id`, `job_id`, `started_at`, `completed_at`
- `status`, `result` (JSON), `error_message`, `duration_seconds`

### Implementation Status
✅ **Production Ready Components**:
- MCP Server with stdio transport
- Agent Orchestrator with full StateGraph
- Context Registry with transactional writes
- Backoffice UI with all pages functional
- Job scheduling with cron and manual triggers
- Execution history with detailed logging

⏳ **Planned Enhancements**:
- LLaMA model integration for summarization
- Notion MCP tool integration
- Webhook ingestion for Notion
- Advanced analytics and insights

## Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Windows PowerShell
python scripts/kill_ports.py  # Kill processes on ports 8001-8003

# Or manually check and kill
netstat -ano | findstr :8003
taskkill /PID <PID> /F
```

**Database Locked Error**
```bash
# Stop all services first
# Delete database and restart
rm context_registry/context_registry.db
rm backoffice/jobs.db
uv run python start_demo.py
```

**MCP Server Connection Issues**
- Check client configuration in `client_configs/`
- Ensure MCP server is running with stdio transport
- Verify `uv` is in PATH for client commands
- Check logs in `logs/` directory

**Job Not Executing**
1. Check job is enabled: http://localhost:8003/jobs
2. Verify schedule format (cron expression)
3. Check execution history for errors
4. Review logs: `logs/backoffice_*.log`

**Import Errors**
```bash
# Reinstall dependencies
uv sync --force

# Check Python version (requires >=3.10)
python --version
```

### Logging

**Application Logs Location**: `logs/`
- `start_demo_*.log`: Main demo orchestration
- `mcp_server_*.log`: MCP Server operations
- `agent_orchestrator_*.log`: Agent workflow execution
- `context_registry_*.log`: Database operations
- `backoffice_*.log`: Web UI and job execution

**View Real-Time Logs**:
```bash
# Windows PowerShell
Get-Content logs\backoffice_*.log -Tail 50 -Wait

# Or use any text editor to open log files
```

### Performance Tips

**Database Optimization**:
- Regular VACUUM: `sqlite3 context_registry.db "VACUUM;"`
- Index maintenance is automatic
- Delete old conversations via Backoffice UI

**Job Scheduling**:
- Avoid overlapping job schedules
- Set appropriate timeout values
- Use `max_retries` for critical jobs
- Monitor execution history regularly

### Debug Mode

**Enable Debug Logging**:
```python
# In each component's main file, change:
logging.basicConfig(level=logging.DEBUG)  # Instead of INFO
```

**Test Individual Components**:
```bash
# Test Context Registry
uv run python context_registry/registry.py

# Test Agent Orchestrator
uv run python agent_orchestrator/orchestrator.py

# Test MCP Server (requires stdio input)
uv run python mcp_server/server.py
```

## Quick Reference

### Essential Commands
```bash
# Start everything
uv run python start_demo.py

# Stop all (Windows)
python scripts/kill_ports.py

# View status
# → Open http://localhost:8003

# Check logs
Get-Content logs\backoffice_*.log -Tail 50
```

### Key Files to Know
- `start_demo.py`: Main entry point
- `backoffice/app.py`: Web UI entry point
- `mcp_server/server.py`: MCP tool definitions
- `agent_orchestrator/orchestrator.py`: LangGraph workflow
- `context_registry/registry.py`: Database operations
- `pyproject.toml`: Dependencies and project config

### Useful URLs
- **Local Backoffice**: http://localhost:8003
- **API Docs**: http://localhost:8003/docs
- **Project Docs**: `docs/` directory
- **Team Guide**: `docs/TEAM_GUIDE.md`
- **Implementation Review**: `docs/BACKOFFICE_IMPLEMENTATION_REVIEW.md`