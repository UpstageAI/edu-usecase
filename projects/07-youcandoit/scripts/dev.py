#!/usr/bin/env python3
"""
Development utilities script
Provides common development tasks using uv
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)

def install_deps():
    """Install dependencies using uv"""
    run_cmd(["uv", "sync"])

def run_demo():
    """Start the demo application"""
    run_cmd(["uv", "run", "python", "start_demo.py"])

def run_tests():
    """Run tests using pytest"""
    run_cmd(["uv", "run", "pytest", "-v"])

def lint():
    """Run linting tools"""
    print("Running black...")
    run_cmd(["uv", "run", "black", "."])
    
    print("Running isort...")
    run_cmd(["uv", "run", "isort", "."])
    
    print("Running flake8...")
    run_cmd(["uv", "run", "flake8", "."])

def type_check():
    """Run type checking with mypy"""
    run_cmd(["uv", "run", "mypy", "."])

def clean():
    """Clean up build artifacts and cache"""
    import shutil
    
    patterns = [
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        ".mypy_cache",
        "*.egg-info",
        "build",
        "dist",
        ".coverage"
    ]
    
    root = Path(".")
    for pattern in patterns:
        for path in root.rglob(pattern):
            if path.is_dir():
                print(f"Removing directory: {path}")
                shutil.rmtree(path)
            elif path.is_file():
                print(f"Removing file: {path}")
                path.unlink()

def dev_server(component: str = "all"):
    """Start development server for specific component"""
    if component == "all":
        run_demo()
    elif component == "mcp":
        run_cmd(["uv", "run", "python", "mcp_server/server.py"])
    elif component == "orchestrator":
        run_cmd(["uv", "run", "python", "agent_orchestrator/orchestrator.py"])
    elif component == "registry":
        run_cmd(["uv", "run", "python", "context_registry/registry.py"])
    elif component == "backoffice":
        run_cmd(["uv", "run", "python", "backoffice/app.py"])
    else:
        print(f"Unknown component: {component}")
        print("Available components: all, mcp, orchestrator, registry, backoffice")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Development utilities for AI Agent Orchestrator")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Install command
    subparsers.add_parser("install", help="Install dependencies")
    
    # Demo command
    subparsers.add_parser("demo", help="Start the demo application")
    
    # Test command
    subparsers.add_parser("test", help="Run tests")
    
    # Lint command
    subparsers.add_parser("lint", help="Run linting tools")
    
    # Type check command
    subparsers.add_parser("typecheck", help="Run type checking")
    
    # Clean command
    subparsers.add_parser("clean", help="Clean up build artifacts")
    
    # Dev server command
    dev_parser = subparsers.add_parser("dev", help="Start development server")
    dev_parser.add_argument("component", nargs="?", default="all", 
                           help="Component to start (all, mcp, orchestrator, registry, backoffice)")
    
    args = parser.parse_args()
    
    if args.command == "install":
        install_deps()
    elif args.command == "demo":
        run_demo()
    elif args.command == "test":
        run_tests()
    elif args.command == "lint":
        lint()
    elif args.command == "typecheck":
        type_check()
    elif args.command == "clean":
        clean()
    elif args.command == "dev":
        dev_server(args.component)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()