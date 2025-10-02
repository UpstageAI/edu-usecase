#!/usr/bin/env python3
"""
Demo startup script for AI Agent Orchestrator
Starts all components in the correct order
"""

import asyncio
import subprocess
import time
import logging
import signal
import sys
import atexit
from pathlib import Path
from datetime import datetime

# Setup logs directory
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure logging with file and console handlers
log_file = logs_dir / f"start_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global process list for cleanup
processes = []
cleanup_in_progress = False

def cleanup_processes():
    """Cleanup all subprocess - called on exit"""
    global cleanup_in_progress, processes
    
    if cleanup_in_progress:
        return
    
    cleanup_in_progress = True
    logger.info("Cleaning up subprocesses...")
    
    for name, process in processes:
        try:
            if process.returncode is None:  # Process is still running
                logger.info(f"Stopping {name} (PID: {process.pid})...")
                try:
                    # Try graceful termination first
                    process.terminate()
                    # Wait a bit for graceful shutdown
                    import time
                    time.sleep(1)
                    
                    # Force kill if still running
                    if process.returncode is None:
                        logger.warning(f"Force killing {name}...")
                        process.kill()
                except Exception as e:
                    logger.error(f"Error terminating {name}: {e}")
        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")
    
    processes.clear()
    logger.info("Cleanup complete")

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    cleanup_processes()
    sys.exit(0)

# Register cleanup handlers
atexit.register(cleanup_processes)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def log_stream(stream, prefix: str, log_file: Path):
    """Read and log subprocess output to both console and file"""
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            async for line in stream:
                line_str = line.decode('utf-8', errors='replace').rstrip()
                if line_str:
                    log_msg = f"{prefix}: {line_str}"
                    f.write(f"{datetime.now().isoformat()} - {log_msg}\n")
                    f.flush()
                    logger.info(log_msg)
    except Exception as e:
        logger.error(f"Error reading stream for {prefix}: {e}")

async def start_component(name: str, command: list, cwd: Path = None):
    """Start a component as a subprocess"""
    global processes
    
    try:
        logger.info(f"Starting {name}...")
        
        # Create log file for this component
        component_log = logs_dir / f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Add to global process list for cleanup
        processes.append((name, process))
        
        # Start logging tasks for stdout and stderr
        asyncio.create_task(log_stream(process.stdout, f"{name}", component_log))
        asyncio.create_task(log_stream(process.stderr, f"{name}", component_log))
        
        logger.info(f"{name} started with PID {process.pid}, logs: {component_log}")
        return process
        
    except Exception as e:
        logger.error(f"Failed to start {name}: {str(e)}")
        return None

async def main():
    """Start all demo components"""
    logger.info("Starting AI Agent Orchestrator Demo")
    
    base_path = Path(__file__).parent
    
    # Start components
    components = [
        {
            "name": "Context Registry",
            "command": ["uv", "run", "python", "registry.py"],
            "cwd": base_path / "context_registry"
        },
        {
            "name": "Agent Orchestrator", 
            "command": ["uv", "run", "python", "orchestrator.py"],
            "cwd": base_path / "agent_orchestrator"
        },
        {
            "name": "MCP Server",
            "command": ["uv", "run", "python", "server.py"],
            "cwd": base_path / "mcp_server"
        },
        {
            "name": "Backoffice UI",
            "command": ["uv", "run", "python", "app.py"],
            "cwd": base_path / "backoffice"
        }
    ]
    
    for component in components:
        process = await start_component(
            component["name"],
            component["command"],
            component["cwd"]
        )
        
        if process:
            # Small delay between starts
            await asyncio.sleep(2)
    
    logger.info("All components started successfully!")
    logger.info("Demo URLs:")
    logger.info("- Backoffice UI: http://localhost:8003")
    logger.info("- MCP Server: stdio (for client connections)")
    logger.info("- Agent Orchestrator: http://localhost:8001")
    logger.info("- Context Registry: http://localhost:8002")
    logger.info("")
    logger.info("Press Ctrl+C to stop all services")
    
    try:
        # Wait for all processes
        while True:
            await asyncio.sleep(1)
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down demo...")
        # Cleanup will be handled by atexit and signal handlers
        pass

if __name__ == "__main__":
    asyncio.run(main())