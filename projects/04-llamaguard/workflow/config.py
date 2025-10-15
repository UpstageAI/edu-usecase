"""
Configuration settings for LlamaGuard vulnerability analysis workflow.

All hardcoded values and magic numbers should be defined here.
"""

import os


class Config:
    """Main configuration class for LlamaGuard workflow."""

    # ============================================================================
    # PATH SETTINGS
    # ============================================================================

    # Base directories
    WORKFLOW_DIR = os.path.dirname(__file__)
    PROJECT_DIR = os.path.join(WORKFLOW_DIR, '..')

    # Model paths
    MODEL_DIR = os.path.join(PROJECT_DIR, "llama-model")
    MODEL_PATH = os.path.join(MODEL_DIR, "merged-vuln-detector")

    # CVE database paths
    CVE_DIR = os.path.join(PROJECT_DIR, "CVE")
    CVE_INDEX_PATH = os.path.join(CVE_DIR, "cve_index.faiss")
    CVE_DATA_PATH = os.path.join(CVE_DIR, "cve_data.pkl")

    # ============================================================================
    # MODEL SETTINGS
    # ============================================================================

    # LLaMA model settings
    MODEL_DTYPE = "fp16"
    MAX_NEW_TOKENS = 512
    TEMPERATURE = None  # None for greedy decoding
    DO_SAMPLE = False   # False for deterministic output
    TOP_P = None

    # ============================================================================
    # CVE & RAG SETTINGS
    # ============================================================================

    # Number of similar CVEs to retrieve
    CVE_TOP_K = 5

    # Maximum CVE text length for state storage (characters)
    CVE_TEXT_TRUNCATE_LENGTH = 200

    # ============================================================================
    # VULNERABILITY DETECTION
    # ============================================================================

    # Keywords for vulnerability detection heuristic
    VULN_KEYWORDS = [
        'vulnerability', 'vulnerable', 'injection', 'xss', 'csrf',
        'insecure', 'unsafe', 'exploit', 'cwe-', 'cve-',
        'sql injection', 'command injection', 'path traversal'
    ]

    # Keywords indicating safe code
    SAFE_KEYWORDS = [
        'no vulnerabilities', 'safe', 'secure', 'no issues detected',
        'no security concerns'
    ]

    # Vulnerability type detection patterns (for fallback extraction)
    VULN_PATTERNS = [
        (r'SQL\s+[Ii]njection', 'SQL Injection'),
        (r'XSS|Cross[- ]Site\s+Scripting', 'Cross-Site Scripting'),
        (r'CSRF|Cross[- ]Site\s+Request\s+Forgery', 'Cross-Site Request Forgery'),
        (r'Command\s+Injection', 'Command Injection'),
        (r'Path\s+Traversal', 'Path Traversal'),
        (r'Buffer\s+Overflow', 'Buffer Overflow'),
        (r'Code\s+Injection', 'Code Injection'),
        (r'Deserialization', 'Insecure Deserialization'),
    ]

    # ============================================================================
    # SEVERITY & SCORING
    # ============================================================================

    # CVSS severity threshold (0-10)
    # Vulnerabilities >= this score will trigger patch generation
    SEVERITY_THRESHOLD = 7

    # Normalized score threshold (0-1) for patch generation
    PATCH_SCORE_THRESHOLD = 0.7

    # ============================================================================
    # REPORT GENERATION
    # ============================================================================

    # Number of related CVEs to include in LLM report context
    REPORT_MAX_RELATED_CVES = 3

    # ============================================================================
    # EXTERNAL API SETTINGS
    # ============================================================================

    # Upstage API settings (read from environment)
    UPSTAGE_API_KEY = os.environ.get('UPSTAGE_API_KEY')
    UPSTAGE_BASE_URL = os.environ.get('UPSTAGE_BASE_URL', 'https://api.upstage.ai/v1')
    UPSTAGE_MODEL = os.environ.get('UPSTAGE_MODEL', 'solar-pro2')
    UPSTAGE_TEMPERATURE = 0.0
    UPSTAGE_MAX_TOKENS = 1200

    # ============================================================================
    # LANGUAGE DETECTION
    # ============================================================================

    # Programming language detection keywords
    LANG_PATTERNS = {
        'php': ['<?php', '<?='],
        'javascript': ['const', 'let', 'var', 'function'],
        'java': ['public class', 'private void', 'public static'],
        'python': ['def ', 'import ', 'class '],  # default
    }

    # ============================================================================
    # WORKFLOW SETTINGS
    # ============================================================================

    # Thread ID for checkpointing
    DEFAULT_THREAD_ID = "default"

    # Output encoding
    DEFAULT_ENCODING = "utf-8"


# Singleton instance
config = Config()
