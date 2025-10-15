"""
Services module for LlamaGuard vulnerability analysis.

Modules:
    llama_service: LLaMA model operations and CVE search
    patch_service: Security patch and report generation via Upstage API
"""

from .llama_service import (
    load_model,
    analyze_code,
    load_cve_db,
    search_cves,
)
from .patch_service import (
    process_input,
    generate_security_report,
)

__all__ = [
    # LLaMA Service
    'load_model',
    'analyze_code',
    'load_cve_db',
    'search_cves',
    # Patch Service
    'process_input',
    'generate_security_report',
]
