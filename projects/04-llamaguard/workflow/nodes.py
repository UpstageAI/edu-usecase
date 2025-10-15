#!/usr/bin/env python3
"""
nodes.py

LangGraph workflow nodes for LlamaGuard vulnerability analysis system.
"""

import os
import sys
import re
from typing import Dict, Any, Literal

# Add parent directory to path
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'llama-model'))

# Import configuration
from config import config

# Import services
from services.llama_service import load_model, analyze_code, load_cve_db, search_cves
from services.patch_service import process_input, generate_security_report

# Import CVE classes (needed for pickle deserialization)
from CVE.cve_vectordb import CVEEntry

# Import state definitions
from state import AgentState

# Import LLaMA utilities
from llama_predict import resolve_dtype

# ============================================================================
# Global model instances (lazy loading)
# ============================================================================
_llama_tokenizer = None
_llama_model = None
_cve_db = None


def _get_llama_model():
    """
    Lazy load LLaMA model (singleton pattern).

    Returns:
        Tuple of (tokenizer, model)

    Raises:
        RuntimeError: If model loading fails
    """
    global _llama_tokenizer, _llama_model
    if _llama_tokenizer is None or _llama_model is None:
        try:
            dtype = resolve_dtype(config.MODEL_DTYPE)
            _llama_tokenizer, _llama_model = load_model(config.MODEL_PATH, dtype)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLaMA model: {e}")
    return _llama_tokenizer, _llama_model


def _get_cve_db():
    """
    Lazy load CVE database (singleton pattern).

    Returns:
        CVEVectorDB instance or None if database files not found

    Raises:
        RuntimeError: If database loading fails
    """
    global _cve_db
    if _cve_db is None:
        try:
            _cve_db = load_cve_db(config.CVE_INDEX_PATH, config.CVE_DATA_PATH)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CVE database: {e}")
    return _cve_db


# ============================================================================
# NODE IMPLEMENTATIONS
# ============================================================================

def initial_analysis_node(state: AgentState) -> Dict[str, Any]:
    """
    Initial vulnerability analysis using fine-tuned LLaMA model.
    Uses analyze.py::analyze_code() function.

    Updates:
        - initial_analysis: LLaMA's vulnerability analysis text
        - is_detected: Boolean flag indicating if vulnerabilities were found
    """
    print("\n--- INITIAL ANALYSIS NODE ---")

    input_code = state.get("input_code", "")
    if not input_code:
        print("WARNING: No code provided")
        return {
            "initial_analysis": "No code provided for analysis.",
            "is_detected": False,
        }

    # Load LLaMA model
    tokenizer, llama_model = _get_llama_model()

    # Analyze code
    print(f"Analyzing code ({len(input_code)} chars)...")
    analysis_result = analyze_code(input_code, tokenizer, llama_model, max_new_tokens=config.MAX_NEW_TOKENS)

    # Determine if vulnerability detected using configured keywords
    analysis_lower = analysis_result.lower()
    is_vulnerable = any(keyword in analysis_lower for keyword in config.VULN_KEYWORDS)

    # Also check for explicit "no vulnerabilities" or "safe" indicators
    if any(keyword in analysis_lower for keyword in config.SAFE_KEYWORDS):
        is_vulnerable = False

    print(f"Analysis complete. Vulnerabilities detected: {is_vulnerable}")

    return {
        "initial_analysis": analysis_result,
        "is_detected": is_vulnerable,
    }


def rag_node(state: AgentState) -> Dict[str, Any]:
    """
    Retrieve similar CVEs from vector database using RAG.
    Uses analyze.py::search_cves() function.

    Updates:
        - retrieved_vulnerabilities: List of similar CVE entries
        - matched_vulnerabilities: List of vulnerability type names
    """
    print("\n--- RAG NODE ---")

    initial_analysis = state.get("initial_analysis", "")
    if not initial_analysis:
        print("WARNING: No initial analysis available")
        return {
            "retrieved_vulnerabilities": [],
            "matched_vulnerabilities": [],
        }

    # Load CVE database
    cve_db = _get_cve_db()
    if cve_db is None:
        print("ERROR: CVE database not available")
        return {
            "retrieved_vulnerabilities": [],
            "matched_vulnerabilities": [],
        }

    # Search for similar CVEs
    print(f"Searching CVE database with query: {initial_analysis[:100]}...")
    cve_results = search_cves(initial_analysis, cve_db, top_k=config.CVE_TOP_K)

    # Format retrieved vulnerabilities
    retrieved_vulns = []
    matched_vuln_names = set()

    for cve_entry, similarity in cve_results:
        # Get CWE from metadata or extract from text
        cwe_from_meta = cve_entry.metadata.get("cwe", "")
        cwe_from_text = ""

        # Try to find CWE in the CVE text if not in metadata
        if not cwe_from_meta and cve_entry.text:
            cwe_matches = re.findall(r'CWE-\d+:?\s*([^,\n]+)', cve_entry.text)
            if cwe_matches:
                cwe_from_text = ", ".join(cwe_matches[:3])  # Take first 3 matches

        final_cwe = cwe_from_meta or cwe_from_text

        vuln_dict = {
            "cve_id": cve_entry.cve_id,
            "cvss": cve_entry.metadata.get("cvss", ""),
            "cwe": final_cwe,
            "similarity": similarity,
            "text": cve_entry.text[:config.CVE_TEXT_TRUNCATE_LENGTH] + "..."  # Truncate for state
        }
        retrieved_vulns.append(vuln_dict)

        # Extract vulnerability type from CWE
        if final_cwe:
            # Extract vulnerability name from CWE (e.g., "CWE-89: SQL Injection" -> "SQL Injection")
            if ":" in final_cwe:
                vuln_name = final_cwe.split(":", 1)[1].strip()
                matched_vuln_names.add(vuln_name)
            else:
                # If no colon, use the whole CWE string
                matched_vuln_names.add(final_cwe.strip())

    # Fallback: extract common vulnerability types from initial_analysis if CWE extraction failed
    if not matched_vuln_names and initial_analysis:
        for pattern, vuln_name in config.VULN_PATTERNS:
            if re.search(pattern, initial_analysis, re.IGNORECASE):
                matched_vuln_names.add(vuln_name)

    matched_vuln_list = list(matched_vuln_names)

    print(f"Retrieved {len(retrieved_vulns)} CVEs")
    print(f"Matched vulnerabilities: {matched_vuln_list}")

    return {
        "retrieved_vulnerabilities": retrieved_vulns,
        "matched_vulnerabilities": matched_vuln_list,
    }


def cvss_calculation_node(state: AgentState) -> Dict[str, Any]:
    """
    Calculate average CVSS score from retrieved CVEs.
    Uses analyze.py::calculate_cvss_score() function.

    Separated as standalone node to allow future replacement with LLM-based analysis.

    Updates:
        - final_severity: String representation of CVSS score (0-10)
    """
    print("\n--- CVSS CALCULATION NODE ---")

    retrieved_vulns = state.get("retrieved_vulnerabilities", [])
    if not retrieved_vulns:
        print("WARNING: No retrieved vulnerabilities for CVSS calculation")
        return {"final_severity": "0"}

    # Extract CVSS scores
    cvss_scores = []
    for vuln in retrieved_vulns:
        cvss_str = vuln.get("cvss", "")
        if cvss_str:
            try:
                # Parse "7.5 (HIGH)" or "7.5" -> 7.5
                score_part = cvss_str.split()[0]
                score = float(score_part)
                cvss_scores.append(score)
            except (ValueError, IndexError):
                print(f"WARNING: Could not parse CVSS: {cvss_str}")

    if not cvss_scores:
        print("WARNING: No valid CVSS scores found")
        avg_cvss = 0.0
    else:
        avg_cvss = sum(cvss_scores) / len(cvss_scores)

    # Round to integer for severity_branch compatibility
    final_severity = str(int(round(avg_cvss)))

    print(f"CVSS scores: {cvss_scores}")
    print(f"Average CVSS: {avg_cvss:.2f} -> final_severity: {final_severity}")

    return {
        "final_severity": final_severity,
    }


def vulnerability_fix_node(state: AgentState) -> Dict[str, Any]:
    """
    Generate fixed code using vuln_processor.py integration.

    Uses process_input() from vuln_processor which handles:
    - Code sanitization
    - External LLM API calls
    - Score-based decision making

    Updates:
        - fixed_code: Patched source code
    """
    print("\n--- VULNERABILITY FIX NODE ---")

    input_code = state.get("input_code", "") or ""
    matched = state.get("matched_vulnerabilities", []) or []
    final_severity = state.get("final_severity", "0")

    # Prepare parameters for process_input
    vuln_name = ", ".join(matched) if matched else "UNKNOWN_VULNERABILITY"

    # Convert CVSS (0-10) to score (0-1)
    try:
        cvss_score = float(final_severity)
        normalized_score = cvss_score / 10.0
    except:
        normalized_score = 0.0

    # Detect language using configured patterns
    language = "python"  # Default
    for lang, patterns in config.LANG_PATTERNS.items():
        if any(pattern in input_code for pattern in patterns):
            language = lang
            break

    print(f"Processing vulnerability: {vuln_name}")
    print(f"CVSS: {final_severity} -> normalized score: {normalized_score:.2f}")
    print(f"Detected language: {language}")

    # Call vuln_processor
    try:
        result = process_input(
            original_code=input_code,
            vuln=vuln_name,
            score=normalized_score,
            language=language
        )

        print(f"vuln_processor result: {result.get('decision', 'patched')}")

        # Extract fixed code from result
        if "decision" in result and result["decision"] == "ok":
            # Low severity - no patch needed
            fixed_code = ""
            print(f"Low severity - no patch generated")
        elif "patched_code" in result:
            # High severity - patch generated
            fixed_code = result["patched_code"].get("code_snippet", "")
            print(f"Patch generated ({len(fixed_code)} chars)")
        else:
            fixed_code = ""
            print(f"WARNING: Unexpected result format from vuln_processor")

    except Exception as e:
        print(f"ERROR: vuln_processor failed: {e}")
        fixed_code = ""

    if fixed_code and len(fixed_code) < 50:
        print(f"WARNING: Fixed code seems too short!")
        print(f"Fixed code: {fixed_code}")

    return {
        "fixed_code": fixed_code,
    }


def report_generation_node(state: AgentState) -> Dict[str, Any]:
    """
    Generate final analysis report.

    Report content:
    - No vulnerability: simple safe message
    - CVSS < 7: basic analysis
    - CVSS >= 7: LLM-generated detailed professional security report

    Updates:
        - report: Final formatted report string
    """
    print("\n--- REPORT GENERATION NODE ---")

    is_detected = state.get("is_detected", False)
    initial_analysis = state.get("initial_analysis", "")
    final_severity = state.get("final_severity", "0")
    matched_vulnerabilities = state.get("matched_vulnerabilities", [])
    retrieved_vulnerabilities = state.get("retrieved_vulnerabilities", [])
    input_code = state.get("input_code", "")

    if not is_detected:
        # No vulnerability detected
        report = "# LlamaGuard Vulnerability Analysis Report\n\n"
        report += "## Status: SAFE\n\n"
        report += "No vulnerabilities detected in the provided code.\n\n"
        report += f"### Analysis:\n{initial_analysis}\n"
        print("Report: SAFE (no vulnerabilities)")
        print(f"Report length: {len(report)} chars")
        return {"report": report}

    # Vulnerability detected
    severity_int = int(final_severity) if final_severity.isdigit() else 0

    if severity_int < 7:
        # Low/Medium severity: basic report
        report = "# LlamaGuard Vulnerability Analysis Report\n\n"
        report += f"## Status: LOW/MEDIUM RISK (CVSS: {final_severity})\n\n"
        if matched_vulnerabilities:
            report += "### Detected Vulnerabilities:\n"
            for vuln in matched_vulnerabilities:
                report += f"- {vuln}\n"
            report += "\n"
        report += f"### Initial Analysis:\n{initial_analysis}\n\n"
        report += "**Recommendation:** Monitor this code and consider remediation during next security review.\n\n"
        print(f"Report: LOW/MEDIUM (severity={severity_int})")
        print(f"Report length: {len(report)} chars")
        return {"report": report}

    # High severity: LLM-generated detailed professional report
    from datetime import datetime

    # Extract primary vulnerability type
    primary_vuln = matched_vulnerabilities[0] if matched_vulnerabilities else "UNKNOWN_VULNERABILITY"

    # Detect language
    language = "python"  # Default
    for lang, patterns in config.LANG_PATTERNS.items():
        if any(pattern in input_code for pattern in patterns):
            language = lang
            break

    print(f"Calling LLM to generate detailed security report...")
    print(f"  Vulnerability: {primary_vuln}")
    print(f"  CVSS: {final_severity}")
    print(f"  Language: {language}")

    try:
        # Call SOLAR PRO 2 to generate complete report
        llm_report = generate_security_report(
            vuln=primary_vuln,
            code=input_code,
            language=language,
            cvss_score=float(final_severity),
            llama_analysis=initial_analysis
        )

        # Build formatted report from LLM response
        vuln_id = llm_report.get('vuln', primary_vuln).replace(" ", "_").upper()

        report = f"## {vuln_id}\n"
        report += f"**CVSS Score:** {llm_report.get('cvss_score', final_severity)}\n\n"
        report += f"**Description:** {initial_analysis}\n\n"

        # Executive Summary
        report += "### Executive summary\n"
        report += llm_report.get('executive_summary', 'No summary available') + "\n\n"

        # Potential Impact
        report += "### Potential impact\n"
        impacts = llm_report.get('potential_impact', [])
        if isinstance(impacts, list):
            for impact in impacts:
                report += f"- {impact}\n"
        else:
            report += f"{impacts}\n"

        attack_diff = llm_report.get('attack_difficulty', 'Unknown')
        req_priv = llm_report.get('required_privileges', 'Unknown')
        report += f"- Attack difficulty: {attack_diff}\n"
        report += f"- Required privileges: {req_priv}\n\n"

        # Recommended Mitigation
        report += "### Recommended quick mitigation\n"
        mitigation = llm_report.get('recommended_mitigation', {})
        if isinstance(mitigation, dict):
            report += f"1. **Immediate:** {mitigation.get('immediate', 'N/A')}\n"
            report += f"2. **Short-term (1-2 weeks):** {mitigation.get('short_term', 'N/A')}\n"
            report += f"3. **Long-term:** {mitigation.get('long_term', 'N/A')}\n\n"
        else:
            report += f"{mitigation}\n\n"

        # Implementation Steps
        report += "### Implementation steps\n"
        impl_steps = llm_report.get('implementation_steps', [])
        if isinstance(impl_steps, list):
            for step in impl_steps:
                report += f"- {step}\n"
        else:
            report += f"{impl_steps}\n"
        report += "\n"

        # Suggested Patch
        report += "### Suggested patch\n"
        patched_code_data = llm_report.get('patched_code', {})
        if isinstance(patched_code_data, dict):
            code_snippet = patched_code_data.get('code_snippet', '')
            code_lang = patched_code_data.get('language', language)
            if code_snippet and len(code_snippet) > 10:
                report += f"```{code_lang}\n{code_snippet}\n```\n\n"
            else:
                report += "*Automated patch generation failed. Manual code review and remediation required.*\n\n"
        else:
            report += "*Automated patch generation failed. Manual code review and remediation required.*\n\n"

        # Metadata footer
        effort_hours = llm_report.get('estimated_effort_hours', 10)
        confidence = llm_report.get('confidence', 0.80)

        report += f"**Estimated effort:** {effort_hours} hours  -  **Confidence:** {confidence:.2f}\n\n"
        report += f"*Generated: {datetime.utcnow().isoformat()}+00:00 UTC*\n"

        print(f"Report: HIGH RISK (severity={severity_int})")
        print(f"  Effort: {effort_hours} hours")
        print(f"  Confidence: {confidence:.2f}")
        print(f"Report length: {len(report)} chars")

        return {"report": report}

    except Exception as e:
        print(f"ERROR: LLM report generation failed: {e}")
        raise RuntimeError(f"Failed to generate security report using LLM: {e}")


# ============================================================================
# BRANCH FUNCTIONS
# ============================================================================

def detection_branch(state: AgentState) -> Literal["rag_node", "report_generation_node"]:
    """
    Branch based on vulnerability detection.
    - If vulnerability detected: route to rag_node
    - If no vulnerability: route to report_generation_node
    """
    print("\n--- DETECTION BRANCH ---")

    raw = state.get("is_detected", None)

    def _truthy(x: Any) -> bool:
        if isinstance(x, bool):
            return x
        if x is None:
            return False
        if isinstance(x, (int, float)):
            return bool(x)
        s = str(x).strip().lower()
        if s in {"true", "1", "yes", "y", "t"}:
            return True
        if s in {"false", "0", "no", "n", "f", ""}:
            return False
        return False

    try:
        detected = _truthy(raw)
        print(f"is_detected: {raw} -> {detected}")
    except Exception as e:
        print(f"Error interpreting is_detected: {e}")
        detected = False

    if not detected:
        # Fallback: check matched_vulnerabilities
        mv = state.get("matched_vulnerabilities", [])
        if isinstance(mv, list) and len(mv) > 0:
            print("Matched vulnerabilities found despite is_detected=False -> routing to [rag_node]")
            return "rag_node"
        else:
            print("No vulnerabilities detected -> routing to [report_generation_node]")
            return "report_generation_node"

    print("Vulnerability detected -> routing to [rag_node]")
    return "rag_node"


def severity_branch(state: AgentState) -> Literal["vulnerability_fix_node", "report_generation_node"]:
    """
    Branch based on CVSS severity score.
    - If severity >= SEVERITY_THRESHOLD (High): route to vulnerability_fix_node
    - If severity < SEVERITY_THRESHOLD (Low/Medium): route to report_generation_node
    """
    print("\n--- SEVERITY BRANCH ---")

    severity_str = state.get("final_severity")

    if severity_str is None:
        print("Severity not found -> routing to [report_generation_node]")
        return "report_generation_node"

    try:
        severity_score = int(severity_str)
        print(f"Severity score: {severity_score}")

        if config.SEVERITY_THRESHOLD <= severity_score <= 10:
            print("High severity detected -> routing to [vulnerability_fix_node]")
            return "vulnerability_fix_node"
        else:
            print("Low/Medium severity detected -> routing to [report_generation_node]")
            return "report_generation_node"
    except (ValueError, TypeError):
        print(f"Invalid severity format: '{severity_str}' -> routing to [report_generation_node]")
        return "report_generation_node"
