#!/usr/bin/env python3
"""
CVE Database Downloader
Downloads CVE data from NVD (National Vulnerability Database) and saves as plain text.
Enhanced with CVSS/CWE filtering, recent-first sorting, and reference scraping.
"""

import json
import requests
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse


# Common CWE ID to name mappings
CWE_NAMES = {
    "CWE-20": "Improper Input Validation",
    "CWE-22": "Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')",
    "CWE-79": "Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')",
    "CWE-89": "Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')",
    "CWE-94": "Improper Control of Generation of Code ('Code Injection')",
    "CWE-119": "Improper Restriction of Operations within the Bounds of a Memory Buffer",
    "CWE-120": "Buffer Copy without Checking Size of Input ('Classic Buffer Overflow')",
    "CWE-125": "Out-of-bounds Read",
    "CWE-190": "Integer Overflow or Wraparound",
    "CWE-200": "Exposure of Sensitive Information to an Unauthorized Actor",
    "CWE-269": "Improper Privilege Management",
    "CWE-276": "Incorrect Default Permissions",
    "CWE-287": "Improper Authentication",
    "CWE-295": "Improper Certificate Validation",
    "CWE-297": "Improper Validation of Certificate with Host Mismatch",
    "CWE-306": "Missing Authentication for Critical Function",
    "CWE-311": "Missing Encryption of Sensitive Data",
    "CWE-312": "Cleartext Storage of Sensitive Information",
    "CWE-319": "Cleartext Transmission of Sensitive Information",
    "CWE-326": "Inadequate Encryption Strength",
    "CWE-352": "Cross-Site Request Forgery (CSRF)",
    "CWE-362": "Concurrent Execution using Shared Resource with Improper Synchronization ('Race Condition')",
    "CWE-400": "Uncontrolled Resource Consumption",
    "CWE-401": "Missing Release of Memory after Effective Lifetime",
    "CWE-416": "Use After Free",
    "CWE-434": "Unrestricted Upload of File with Dangerous Type",
    "CWE-476": "NULL Pointer Dereference",
    "CWE-502": "Deserialization of Untrusted Data",
    "CWE-522": "Insufficiently Protected Credentials",
    "CWE-611": "Improper Restriction of XML External Entity Reference",
    "CWE-732": "Incorrect Permission Assignment for Critical Resource",
    "CWE-787": "Out-of-bounds Write",
    "CWE-798": "Use of Hard-coded Credentials",
    "CWE-862": "Missing Authorization",
    "CWE-863": "Incorrect Authorization",
    "CWE-918": "Server-Side Request Forgery (SSRF)",
    "CWE-94": "Improper Control of Generation of Code ('Code Injection')",
    "CWE-77": "Improper Neutralization of Special Elements used in a Command ('Command Injection')",
    "CWE-78": "Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')",
    "CWE-91": "XML Injection (aka Blind XPath Injection)",
    "CWE-434": "Unrestricted Upload of File with Dangerous Type",
    "CWE-601": "URL Redirection to Untrusted Site ('Open Redirect')",
    "CWE-667": "Improper Locking",
    "CWE-770": "Allocation of Resources Without Limits or Throttling",
    "CWE-772": "Missing Release of Resource after Effective Lifetime",
    "CWE-805": "Buffer Access with Incorrect Length Value",
    "CWE-909": "Missing Initialization of Resource",
    "CWE-1021": "Improper Restriction of Rendered UI Layers or Frames",
    "CWE-1236": "Improper Neutralization of Formula Elements in a CSV File",
}


class CVEDownloader:
    """Downloads CVE data from NVD API and saves to plain text format."""

    BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, output_file: str = "cve_database.txt", api_key: str = None,
                 scrape_references: bool = True):
        """
        Initialize CVE downloader.

        Args:
            output_file: Path to output text file
            api_key: Optional NVD API key for higher rate limits
            scrape_references: Whether to scrape references for code examples
        """
        self.output_file = output_file
        self.api_key = api_key
        self.scrape_references = scrape_references
        self.headers = {}
        if api_key:
            self.headers["apiKey"] = api_key

        # Cache for scraped content to avoid duplicate requests
        self.reference_cache = {}

    def get_cwe_name(self, cwe_id: str) -> str:
        """
        Get human-readable name for a CWE ID.

        Args:
            cwe_id: CWE identifier (e.g., "CWE-120")

        Returns:
            CWE name or the ID if not found
        """
        return CWE_NAMES.get(cwe_id, cwe_id)

    def has_cvss_and_cwe(self, cve_data: Dict) -> bool:
        """
        Check if CVE has both CVSS score and CWE category.

        Args:
            cve_data: CVE data dictionary

        Returns:
            True if both CVSS and CWE are present
        """
        cve = cve_data.get("cve", {})

        # Check for CVSS score
        metrics = cve.get("metrics", {})
        has_cvss = bool(metrics.get("cvssMetricV31") or metrics.get("cvssMetricV30") or
                       metrics.get("cvssMetricV2"))

        # Check for CWE
        weaknesses = cve.get("weaknesses", [])
        has_cwe = False
        for weakness in weaknesses:
            for desc in weakness.get("description", []):
                if desc.get("lang") == "en" and desc.get("value", "").startswith("CWE-"):
                    has_cwe = True
                    break
            if has_cwe:
                break

        return has_cvss and has_cwe

    def download_cves(self,
                      start_index: int = 0,
                      results_per_page: int = 2000,
                      max_results: int = None,
                      days_back: int = 120) -> List[Dict]:
        """
        Download CVE data from NVD API, filtered by CVSS and CWE availability.
        Downloads recent CVEs first.

        Args:
            start_index: Starting index for pagination
            results_per_page: Number of results per page (max 2000)
            max_results: Maximum number of CVEs to download (None for all)
            days_back: Number of days back to search (max 120 per NVD API limit)

        Returns:
            List of CVE dictionaries with CVSS and CWE
        """
        all_cves = []

        # NVD API v2.0 has a 120-day maximum range limit
        # Split into 120-day chunks if needed
        max_days_per_request = 120
        end_date = datetime.now()
        total_days = min(days_back, 120)  # Cap at 120 days
        start_date = end_date - timedelta(days=total_days)

        print(f"Starting CVE download from NVD...")
        print(f"Filtering for CVEs with CVSS scores and CWE categories")
        print(f"Date range: {start_date.date()} to {end_date.date()}")

        current_index = start_index

        while True:
            if max_results and len(all_cves) >= max_results:
                break

            params = {
                "startIndex": current_index,
                "resultsPerPage": results_per_page,
                "pubStartDate": start_date.strftime("%Y-%m-%dT00:00:00.000Z"),
                "pubEndDate": end_date.strftime("%Y-%m-%dT23:59:59.999Z")
            }

            try:
                response = requests.get(
                    self.BASE_URL,
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()

                data = response.json()
                vulnerabilities = data.get("vulnerabilities", [])

                if not vulnerabilities:
                    break

                # Filter for CVEs with both CVSS and CWE
                filtered = [v for v in vulnerabilities if self.has_cvss_and_cwe(v)]

                # Respect max_results limit
                if max_results:
                    remaining = max_results - len(all_cves)
                    filtered = filtered[:remaining]

                all_cves.extend(filtered)

                print(f"Downloaded {len(vulnerabilities)} CVEs, {len(filtered)} match filters (Total: {len(all_cves)})...")

                # Stop if we've reached the limit
                if max_results and len(all_cves) >= max_results:
                    print(f"Reached max_results limit of {max_results}")
                    break

                # Check if there are more results
                total_results = data.get("totalResults", 0)
                if current_index + results_per_page >= total_results:
                    break

                current_index += results_per_page

                # Rate limiting: wait between requests
                # With API key: 50 requests per 30 seconds
                # Without API key: 5 requests per 30 seconds
                sleep_time = 0.6 if self.api_key else 6
                time.sleep(sleep_time)

            except requests.exceptions.RequestException as e:
                print(f"Error downloading CVEs: {e}")
                print(f"Response: {response.text if 'response' in locals() else 'No response'}")
                break

        # Sort by publication date (most recent first)
        all_cves.sort(key=lambda x: x.get("cve", {}).get("published", ""), reverse=True)

        print(f"Total CVEs with CVSS and CWE: {len(all_cves)}")
        return all_cves

    def scrape_github_commit(self, url: str) -> Optional[str]:
        """
        Scrape code diff from GitHub commit URL.

        Args:
            url: GitHub commit URL

        Returns:
            Code diff text or None
        """
        if url in self.reference_cache:
            return self.reference_cache[url]

        try:
            # Convert to patch format for easier parsing
            if '/commit/' in url:
                patch_url = url + '.patch'
            else:
                return None

            response = requests.get(patch_url, timeout=10)
            response.raise_for_status()

            content = response.text
            # Limit size to avoid huge diffs
            if len(content) > 50000:
                content = content[:50000] + "\n... [truncated]"

            self.reference_cache[url] = content
            time.sleep(1)  # Be nice to GitHub
            return content

        except Exception as e:
            print(f"  Warning: Could not scrape {url}: {e}")
            return None

    def scrape_reference_content(self, url: str) -> Optional[str]:
        """
        Attempt to scrape code examples from reference URLs.

        Args:
            url: Reference URL

        Returns:
            Scraped content or None
        """
        if not self.scrape_references:
            return None

        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # GitHub commits and pull requests
        if 'github.com' in hostname and ('/commit/' in url or '/pull/' in url):
            return self.scrape_github_commit(url)

        # For other URLs, try to extract code blocks from HTML
        if url in self.reference_cache:
            return self.reference_cache[url]

        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Security Research Bot)'
            })
            response.raise_for_status()

            content = response.text

            # Look for code blocks in common formats
            code_blocks = []

            # Markdown code blocks
            md_blocks = re.findall(r'```[\w]*\n(.*?)```', content, re.DOTALL)
            code_blocks.extend(md_blocks)

            # HTML pre/code tags
            html_blocks = re.findall(r'<(?:pre|code)>(.*?)</(?:pre|code)>', content, re.DOTALL)
            code_blocks.extend(html_blocks)

            if code_blocks:
                result = "\n\n".join(code_blocks[:3])  # Limit to first 3 blocks
                if len(result) > 10000:
                    result = result[:10000] + "\n... [truncated]"
                self.reference_cache[url] = result
                time.sleep(1)  # Rate limiting
                return result

        except Exception as e:
            print(f"  Warning: Could not scrape {url}: {e}")

        return None

    def format_cve_text(self, cve_data: Dict) -> str:
        """
        Format CVE data as plain text with enhanced CVSS, CWE, and code examples.

        Args:
            cve_data: CVE data dictionary

        Returns:
            Formatted text string
        """
        cve = cve_data.get("cve", {})
        cve_id = cve.get("id", "N/A")

        # Description
        descriptions = cve.get("descriptions", [])
        description = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            "No description available"
        )

        # Published and modified dates
        published = cve.get("published", "N/A")
        modified = cve.get("lastModified", "N/A")

        # Enhanced CVSS scores with vector (prefer v3, fallback to v2)
        metrics = cve.get("metrics", {})
        cvss_v3 = metrics.get("cvssMetricV31", []) or metrics.get("cvssMetricV30", [])
        cvss_v2 = metrics.get("cvssMetricV2", [])
        cvss_score = "N/A"
        cvss_severity = "N/A"
        cvss_vector = "N/A"
        cvss_version = ""

        if cvss_v3:
            cvss_data = cvss_v3[0].get("cvssData", {})
            cvss_score = cvss_data.get("baseScore", "N/A")
            cvss_severity = cvss_data.get("baseSeverity", "N/A")
            cvss_vector = cvss_data.get("vectorString", "N/A")
            cvss_version = "v3.1" if "cvssMetricV31" in metrics else "v3.0"
        elif cvss_v2:
            cvss_data = cvss_v2[0].get("cvssData", {})
            cvss_score = cvss_data.get("baseScore", "N/A")
            cvss_severity = cvss_v2[0].get("baseSeverity", "N/A")
            cvss_vector = cvss_data.get("vectorString", "N/A")
            cvss_version = "v2.0"

        # Weaknesses (CWE) with full list and names
        weaknesses = cve.get("weaknesses", [])
        cwe_data = []
        for weakness in weaknesses:
            for desc in weakness.get("description", []):
                if desc.get("lang") == "en":
                    cwe_id = desc.get("value", "")
                    cwe_name = self.get_cwe_name(cwe_id)
                    cwe_data.append((cwe_id, cwe_name))

        # References with categorization
        references = cve.get("references", [])

        # Format as text
        text = f"CVE ID: {cve_id}\n"
        text += f"Published: {published}\n"
        text += f"Modified: {modified}\n"
        if cvss_version:
            text += f"CVSS Score: {cvss_score} ({cvss_severity}) [{cvss_version}]\n"
            text += f"CVSS Vector: {cvss_vector}\n"
        else:
            text += f"CVSS Score: {cvss_score} ({cvss_severity})\n"

        if cwe_data:
            text += f"\nCWE Categories:\n"
            for cwe_id, cwe_name in cwe_data:
                text += f"  - {cwe_id}: {cwe_name}\n"

        text += f"\nDescription:\n{description}\n"

        # References with types
        if references:
            text += f"\nReferences ({len(references)}):\n"
            for i, ref in enumerate(references[:10], 1):  # Limit to 10 refs
                url = ref.get("url", "")
                tags = ref.get("tags", [])
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                text += f"  {i}. {url}{tag_str}\n"

        # Scrape code examples from references
        if self.scrape_references and references:
            text += f"\nAttempting to extract code examples from references...\n"
            code_found = False

            for ref in references[:5]:  # Try first 5 references
                url = ref.get("url", "")
                print(f"  Scraping {url}...")

                code_content = self.scrape_reference_content(url)
                if code_content:
                    text += f"\n--- Code from {url} ---\n"
                    text += code_content + "\n"
                    code_found = True
                    break  # Only include one code example per CVE to avoid bloat

            if not code_found:
                text += "  No code examples found in references.\n"

        text += "\n" + "="*80 + "\n\n"

        return text

    def save_to_file(self, cve_list: List[Dict]):
        """
        Save CVE data to plain text file.

        Args:
            cve_list: List of CVE dictionaries
        """
        print(f"Saving to {self.output_file}...")

        with open(self.output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"CVE Database Export\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total CVEs: {len(cve_list)}\n")
            f.write("="*80 + "\n\n")

            # Write each CVE
            for cve_data in cve_list:
                text = self.format_cve_text(cve_data)
                f.write(text)

        print(f"Successfully saved {len(cve_list)} CVEs to {self.output_file}")

    def run(self, max_results: int = None, days_back: int = 120):
        """
        Download CVEs and save to file.

        Args:
            max_results: Maximum number of CVEs to download (None for all)
            days_back: Number of days back to search (max 120 per NVD API limit)
        """
        cves = self.download_cves(max_results=max_results, days_back=days_back)
        if cves:
            self.save_to_file(cves)
        else:
            print("No CVEs downloaded")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download CVE database from NVD with CVSS/CWE filtering and reference scraping"
    )
    parser.add_argument(
        "--output", "-o",
        default="cve_database.txt",
        help="Output file path (default: cve_database.txt)"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="NVD API key for higher rate limits"
    )
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        help="Maximum number of CVEs to download (default: all matching filters)"
    )
    parser.add_argument(
        "--days-back", "-d",
        type=int,
        default=120,
        help="Number of days back to search (max 120 per NVD API limit, default: 120)"
    )
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        help="Disable reference scraping for code examples"
    )

    args = parser.parse_args()

    downloader = CVEDownloader(
        output_file=args.output,
        api_key=args.api_key,
        scrape_references=not args.no_scrape
    )
    downloader.run(max_results=args.max_results, days_back=args.days_back)
