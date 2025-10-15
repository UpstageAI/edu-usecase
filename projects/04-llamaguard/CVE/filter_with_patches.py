#!/usr/bin/env python3
"""
Filter CVE database to extract only entries that have patch code.
"""

def filter_cves_with_patches(input_file, output_file):
    """
    Read CVE database and write only entries with patch code to output file.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by CVE entries (using the separator line)
    entries = content.split('=' * 80)

    # First entry is the header
    header = entries[0]

    filtered_entries = []
    cves_with_patches = 0

    # Process each CVE entry
    for entry in entries[1:]:
        if not entry.strip():
            continue

        # Check if this entry has patch code
        if '--- Code from' in entry:
            filtered_entries.append(entry)
            cves_with_patches += 1

    # Write filtered results
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header with updated count
        f.write("CVE Database Export (Filtered - With Patches Only)\n")
        f.write(f"Generated: {header.split('Generated: ')[1].split()[0] if 'Generated:' in header else 'N/A'}\n")
        f.write(f"Total CVEs with patches: {cves_with_patches}\n")
        f.write("=" * 80 + "\n")

        # Write each filtered entry
        for entry in filtered_entries:
            f.write(entry)
            f.write("=" * 80 + "\n")

    return cves_with_patches

if __name__ == '__main__':
    input_file = 'cve_database.txt'
    output_file = 'cve_database_with_patches.txt'

    print(f"Filtering CVEs from {input_file}...")
    count = filter_cves_with_patches(input_file, output_file)
    print(f"✓ Found {count} CVEs with patch code")
    print(f"✓ Saved to {output_file}")
