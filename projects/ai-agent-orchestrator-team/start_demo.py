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
import os
import requests
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

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

def check_ollama_setup():
    """Check if Ollama is installed and model is available (for LLM_PROVIDER=llama)"""
    # Only check if using llama provider
    llm_provider = os.getenv("LLM_PROVIDER", "llama").lower()
    if llm_provider != "llama":
        return True  # Skip check for other providers
    
    logger.info("Checking Ollama setup...")
    
    # 1. Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            version_info = response.json()
            logger.info(f"✓ Ollama is running (version: {version_info.get('version', 'unknown')})")
        else:
            raise Exception("Ollama API returned non-200 status")
    except Exception as e:
        logger.error("✗ Ollama is not running!")
        logger.error("")
        logger.error("Please install and start Ollama:")
        logger.error("  1. Download: https://ollama.com/download/windows")
        logger.error("  2. Install the downloaded file")
        logger.error("  3. Ollama will start automatically in the background")
        logger.error("")
        return False
    
    # 2. Check if required model is available
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if model_name in result.stdout:
            logger.info(f"✓ Model '{model_name}' is available")
            return True
        else:
            logger.warning(f"✗ Model '{model_name}' not found")
            logger.info(f"Downloading model '{model_name}'... (this may take a few minutes)")
            
            # Auto-download the model
            pull_result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=False,  # Show progress to user
                timeout=600  # 10 minutes timeout
            )
            
            if pull_result.returncode == 0:
                logger.info(f"✓ Model '{model_name}' downloaded successfully")
                return True
            else:
                logger.error(f"✗ Failed to download model '{model_name}'")
                return False
                
    except FileNotFoundError:
        logger.error("✗ 'ollama' command not found in PATH")
        logger.error("Please ensure Ollama is properly installed")
        return False
    except subprocess.TimeoutExpired:
        logger.error("✗ Model download timed out")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking model: {e}")
        return False

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
    
    # Check Ollama setup if using llama provider
    if not check_ollama_setup():
        logger.error("Ollama setup check failed. Please fix the issues above and try again.")
        sys.exit(1)
    
    logger.info("All prerequisites satisfied, starting components...")
    
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