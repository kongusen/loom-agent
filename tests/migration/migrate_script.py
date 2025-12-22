#!/usr/bin/env python3
"""
Loom v0.2.0 to v0.2.1 Migration Script (Test Version)
"""

import os
import re
import argparse
import sys
from pathlib import Path

def migrate_file(file_path: Path, dry_run: bool = False) -> bool:
    """Migrate a single file. Returns True if changes were made."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    original_content = content
    
    # 1. Update Imports
    content = re.sub(r'from loom import agent', r'from loom import Agent', content)
    # 2. Update Factory Method
    content = re.sub(r'loom\.agent\(', r'Agent(', content)
    # 3. Update Execution Method
    # Avoid replacing asyncio.run
    content = re.sub(r'(?<!asyncio)\.run\(', r'.invoke(', content)
    # 4. Update Crew Mode
    if 'mode="sequential"' in content:
        content = content.replace('mode="sequential"', 'workflow=Sequence([...]) # TODO: Fix arguments')
        if "from loom.patterns.composition import Sequence" not in content:
            content = "from loom.patterns.composition import Sequence\n" + content
    if 'mode="parallel"' in content:
         content = content.replace('mode="parallel"', 'workflow=Group(agents=[...]) # TODO: Fix arguments')
         if "from loom.patterns.composition import Group" not in content:
            content = "from loom.patterns.composition import Group\n" + content
    
    # 5. Message .reply()
    if '.reply(' in content:
        content = re.sub(r'(\.reply\()', r'.invoke( # TODO: Verify this was a reply ', content)

    if content != original_content:
        if dry_run:
            print(f"[Dry Run] Would modify {file_path}")
        else:
            print(f"Modifying {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Migrate Loom v0.2.0 projects to v0.2.1")
    parser.add_argument("path", help="Path to project directory or file")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write files")
    
    args = parser.parse_args()
    target_path = Path(args.path)
    
    if not target_path.exists():
        print(f"Path not found: {target_path}")
        sys.exit(1)
        
    if target_path.is_file():
        if target_path.suffix == '.py':
            migrate_file(target_path, args.dry_run)
    else:
        for file_path in target_path.rglob("*.py"):
            migrate_file(file_path, args.dry_run)

if __name__ == "__main__":
    main()
