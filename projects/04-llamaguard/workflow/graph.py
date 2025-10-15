#!/usr/bin/env python3
"""
graph.py

LangGraph workflow construction and execution for LlamaGuard vulnerability analysis.
"""

import sys
import os
import argparse
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from state import AgentState

# Import CVE classes for pickle deserialization compatibility
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(parent_dir)
from CVE.cve_vectordb import CVEEntry

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Make CVEEntry available in __main__ namespace for pickle compatibility
# (needed when pickle file was created from a script run as __main__)
sys.modules['__main__'].CVEEntry = CVEEntry
from nodes import (
    initial_analysis_node,
    rag_node,
    cvss_calculation_node,
    vulnerability_fix_node,
    report_generation_node,
    detection_branch,
    severity_branch,
)


def build_graph():
    """
    Build the LangGraph StateGraph for vulnerability analysis workflow.

    Workflow:
        START
          ↓
        initial_analysis_node
          ↓
        detection_branch
          ↓ (is_detected?)
          ├─ False → report_generation_node → END
          └─ True → rag_node
                      ↓
                    cvss_calculation_node
                      ↓
                    severity_branch
                      ↓ (final_severity >= 7?)
                      ├─ False → report_generation_node → END
                      └─ True → vulnerability_fix_node
                                  ↓
                                report_generation_node → END
    """
    # Create StateGraph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("initial_analysis_node", initial_analysis_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("cvss_calculation_node", cvss_calculation_node)
    workflow.add_node("vulnerability_fix_node", vulnerability_fix_node)
    workflow.add_node("report_generation_node", report_generation_node)

    # Set entry point
    workflow.set_entry_point("initial_analysis_node")

    # Add edges
    # initial_analysis_node -> detection_branch
    workflow.add_conditional_edges(
        "initial_analysis_node",
        detection_branch,
        {
            "rag_node": "rag_node",
            "report_generation_node": "report_generation_node",
        }
    )

    # rag_node -> cvss_calculation_node
    workflow.add_edge("rag_node", "cvss_calculation_node")

    # cvss_calculation_node -> severity_branch
    workflow.add_conditional_edges(
        "cvss_calculation_node",
        severity_branch,
        {
            "vulnerability_fix_node": "vulnerability_fix_node",
            "report_generation_node": "report_generation_node",
        }
    )

    # vulnerability_fix_node -> report_generation_node
    workflow.add_edge("vulnerability_fix_node", "report_generation_node")

    # report_generation_node -> END
    workflow.add_edge("report_generation_node", END)

    # Compile graph
    memory = InMemorySaver()
    graph = workflow.compile(checkpointer=memory)

    return graph


def run_analysis(input_code: str, thread_id: str = "default"):
    """
    Run vulnerability analysis on the provided code.

    Args:
        input_code: Source code to analyze
        thread_id: Thread ID for checkpointing (default: "default")

    Returns:
        Final state dictionary with analysis results
    """
    print("\n" + "=" * 80)
    print("LlamaGuard Vulnerability Analysis")
    print("=" * 80)

    # Build graph
    graph = build_graph()

    # Initial state
    initial_state = {
        "input_code": input_code,
    }

    # Run graph
    config = {"configurable": {"thread_id": thread_id}}
    final_state = None

    for state in graph.stream(initial_state, config):
        # state is a dict: {node_name: node_output}
        for node_name, node_output in state.items():
            print(f"\n[{node_name}] completed")
            final_state = node_output

    print("\n" + "=" * 80)
    print("Analysis Complete")
    print("=" * 80)

    return final_state


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="LlamaGuard Vulnerability Analysis Workflow")
    parser.add_argument("--code", type=str, help="Code to analyze (direct input)")
    parser.add_argument("--code_file", type=str, help="Path to code file to analyze")
    parser.add_argument("--output", type=str, default=None, help="Path to save report")
    args = parser.parse_args()

    # Get input code
    if args.code:
        code = args.code
        print("[Input] Direct code input")
    elif args.code_file:
        with open(args.code_file, "r", encoding="utf-8") as f:
            code = f.read()
        print(f"[Input] Code from {args.code_file}")
    else:
        # Default example
        code = (
            "def login(username, password):\n"
            "    query = f\"SELECT * FROM users WHERE username='{username}' AND password='{password}'\"\n"
            "    cursor.execute(query)\n"
            "    return cursor.fetchone()\n"
        )
        print("[Input] Using default example (SQL Injection)")

    # Run analysis
    final_state = run_analysis(code)

    # Print report
    if final_state and "report" in final_state:
        print("\n" + "=" * 80)
        print("FINAL REPORT")
        print("=" * 80)
        print(final_state["report"])

        # Save to file if requested
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(final_state["report"])
            print(f"\nReport saved to: {args.output}")
    else:
        print("\nERROR: No report generated")


if __name__ == "__main__":
    main()
