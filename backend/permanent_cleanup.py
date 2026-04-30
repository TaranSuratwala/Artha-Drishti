"""
Permanent Cleanup Script
========================
Removes all commented-out legacy code blocks from IntegratedPostGreSQL.py and FeatureEngineering.py.
These files accumulated multiple old, fully-commented-out versions of the code at the top.
This script keeps ONLY the active (uncommented) code.

Run once and delete this script afterwards.
"""

import os
import shutil

BASE_DIR = r"c:\Users\Lenovo\Documents\VS CODE codes(files)\helloworld\Project sem-6\backend"


def find_active_start(lines, primary_marker, secondary_marker):
    """
    Find the first UNCOMMENTED line matching `primary_marker`,
    verified by checking that a nearby subsequent line matches `secondary_marker`.
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == primary_marker:
            # Verify by checking next few lines for secondary marker
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() == secondary_marker:
                    return i
    return None


def cleanup_file(filename, primary_marker, secondary_marker):
    filepath = os.path.join(BASE_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"  SKIP: {filename} not found")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    original_count = len(lines)
    original_size = os.path.getsize(filepath)
    
    start_index = find_active_start(lines, primary_marker, secondary_marker)
    
    if start_index is None:
        print(f"  SKIP: Could not find active code marker in {filename}")
        return
    
    if start_index == 0:
        print(f"  OK: {filename} is already clean ({original_count} lines)")
        return
    
    # Create backup before modifying
    backup_path = filepath + '.backup'
    shutil.copy2(filepath, backup_path)
    
    # Write back only the active code
    active_lines = lines[start_index:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(active_lines)
    
    new_size = os.path.getsize(filepath)
    removed_lines = start_index
    remaining_lines = len(active_lines)
    
    print(f"  CLEANED: {filename}")
    print(f"    Removed: {removed_lines} lines of commented-out legacy code")
    print(f"    Remaining: {remaining_lines} lines of active code")
    print(f"    Size: {original_size:,} bytes -> {new_size:,} bytes ({(1 - new_size/original_size)*100:.0f}% reduction)")
    print(f"    Backup: {backup_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("PERMANENT CLEANUP - Removing legacy commented code")
    print("=" * 60)
    print()
    
    cleanup_file(
        'IntegratedPostGreSQL.py',
        primary_marker='import yfinance as yf',
        secondary_marker='import pandas as pd'
    )
    print()
    
    cleanup_file(
        'FeatureEngineering.py',
        primary_marker='import pandas as pd',
        secondary_marker='import pandas_ta as ta'
    )
    
    print()
    print("=" * 60)
    print("DONE! Backups created as .backup files.")
    print("Delete backups once you verify everything works:")
    print(f"  del \"{os.path.join(BASE_DIR, 'IntegratedPostGreSQL.py.backup')}\"")
    print(f"  del \"{os.path.join(BASE_DIR, 'FeatureEngineering.py.backup')}\"")
    print("=" * 60)
