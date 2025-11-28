#!/usr/bin/env python3
"""
Add standard file headers to all Python and JavaScript files.
Run this script to ensure all files have proper attribution.

Author: Brett Turner (ntounix-prog)
Created: November 2024
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Standard Python header template
PYTHON_HEADER = '''"""
{description}

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

'''

# Standard JavaScript header template  
JS_HEADER = '''/**
 * {description}
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2024
 * @copyright (c) 2024 Brett Turner. All rights reserved.
 */

'''

def get_file_description(filepath):
    """Generate a description based on file path and name."""
    name = Path(filepath).stem
    parent = Path(filepath).parent.name
    
    # Common patterns
    if 'api' in str(filepath):
        return f"API endpoints for {name}"
    elif 'platforms' in str(filepath):
        return f"Platform client for {name.replace('_client', '').replace('_', ' ').title()}"
    elif 'pages' in str(filepath):
        return f"{name.replace('_', ' ').title()} page component"
    elif 'components' in str(filepath):
        return f"{name.replace('_', ' ').title()} component"
    elif 'hooks' in str(filepath):
        return f"React hook: {name}"
    elif 'workers' in str(filepath):
        return f"Celery worker for {name}"
    else:
        return f"{name.replace('_', ' ').title()} module"

def has_header(content, filetype):
    """Check if file already has a header."""
    if filetype == 'python':
        return content.strip().startswith('"""') and 'Author:' in content[:500]
    elif filetype == 'js':
        return content.strip().startswith('/**') and '@author' in content[:500]
    return False

def add_header_to_file(filepath, dry_run=True):
    """Add header to a single file."""
    ext = Path(filepath).suffix
    
    if ext == '.py':
        filetype = 'python'
        template = PYTHON_HEADER
    elif ext in ['.js', '.jsx']:
        filetype = 'js'
        template = JS_HEADER
    else:
        return False, "Unsupported file type"
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        return False, f"Read error: {e}"
    
    if has_header(content, filetype):
        return False, "Already has header"
    
    # Skip empty files
    if not content.strip():
        return False, "Empty file"
    
    # Skip __init__.py files that are mostly empty
    if Path(filepath).name == '__init__.py' and len(content.strip()) < 50:
        return False, "Minimal init file"
    
    description = get_file_description(filepath)
    header = template.format(description=description)
    
    # Handle existing docstrings/comments
    if filetype == 'python' and content.strip().startswith('"""'):
        # Replace existing docstring
        end = content.find('"""', 3) + 3
        old_doc = content[:end]
        new_content = header.rstrip() + content[end:]
    elif filetype == 'python' and content.strip().startswith('#'):
        # Add before shebang/comments
        new_content = header + content
    else:
        new_content = header + content
    
    if not dry_run:
        with open(filepath, 'w') as f:
            f.write(new_content)
    
    return True, "Header added"

def process_directory(root_dir, dry_run=True):
    """Process all files in directory."""
    results = {'added': [], 'skipped': [], 'errors': []}
    
    exclude_dirs = {'venv', 'node_modules', '__pycache__', '.git', '_deprecated', 'dist'}
    
    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith(('.py', '.js', '.jsx')):
                filepath = os.path.join(root, file)
                success, msg = add_header_to_file(filepath, dry_run)
                
                if success:
                    results['added'].append((filepath, msg))
                elif 'error' in msg.lower():
                    results['errors'].append((filepath, msg))
                else:
                    results['skipped'].append((filepath, msg))
    
    return results

def main():
    dry_run = '--apply' not in sys.argv
    
    if dry_run:
        print("DRY RUN - No files will be modified")
        print("Run with --apply to make changes")
        print()
    
    # Process glassdome Python package
    print("Processing glassdome/ ...")
    py_results = process_directory('glassdome', dry_run)
    
    # Process frontend
    print("Processing frontend/src/ ...")
    js_results = process_directory('frontend/src', dry_run)
    
    # Combine results
    all_added = py_results['added'] + js_results['added']
    all_skipped = py_results['skipped'] + js_results['skipped']
    all_errors = py_results['errors'] + js_results['errors']
    
    print(f"\n{'Would add' if dry_run else 'Added'} headers to {len(all_added)} files:")
    for f, msg in all_added[:20]:
        print(f"  ✅ {f}")
    if len(all_added) > 20:
        print(f"  ... and {len(all_added) - 20} more")
    
    print(f"\nSkipped {len(all_skipped)} files (already have headers or minimal)")
    
    if all_errors:
        print(f"\nErrors: {len(all_errors)}")
        for f, msg in all_errors:
            print(f"  ❌ {f}: {msg}")

if __name__ == '__main__':
    os.chdir(Path(__file__).parent.parent)
    main()

