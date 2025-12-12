#!env python3
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# --- CONFIGURATION PATHS ---
APP_NAME = 'headerize'
GLOBAL_CONFIG_DIR = Path.home() / '.config' / APP_NAME
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / 'config.json'
REPO_CONFIG_FILE = Path('.headerize.config')
GITIGNORE_FILE = Path('.gitignore')

# --- FILE TYPE MAPPINGS (Unchanged) ---
# Maps extension to (line_comment, block_start, block_end, shebang_template)
FILE_TYPE_MAP: Dict[str, Tuple[str, str, str, Optional[str]]] = {
    # Scripts
    '.py': ('#', '"""', '"""', '#!/usr/bin/env python3'),
    '.sh': ('#', '#', '#', '#!/usr/bin/env bash'),
    '.bash': ('#', '#', '#', '#!/usr/bin/env bash'),
    # C-like languages
    '.c': ('//', '/*', '*/', None),
    '.bsv': ('//', '/*', '*/', None),
    '.rs': ('//', '/*', '*/', None),
    '.cpp': ('//', '/*', '*/', None),
    '.h': ('//', '/*', '*/', None),
    '.hpp': ('//', '/*', '*/', None),
    '.java': ('//', '/*', '*/', None),
    '.cs': ('//', '/*', '*/', None),
    '.go': ('//', '/*', '*/', None),
    '.js': ('//', '/*', '*/', None),
    '.ts': ('//', '/*', '*/', None),
    # Web/Markup
    '.html': ('', None),
    '.xml': ('', None),
    '.md': ('', None),
    '.yaml': ('#', '#', '#', None),
    '.yml': ('#', '#', '#', None),
}

# --- UTILITIES ---

def find_git_root(path: Path) -> Optional[Path]:
    """Traverse up the directory tree to find the .git directory."""
    current = path.resolve()
    while current != current.parent:
        if (current / '.git').is_dir():
            return current
        current = current.parent
    return None

def get_comment_style(filepath: Path) -> Tuple[str, str, str, Optional[str]]:
    """Determines the comment style and shebang based on file extension."""
    ext = filepath.suffix.lower()
    # Default to generic line comment if unknown
    return FILE_TYPE_MAP.get(ext, ('#', '#', '#', None))

# --- CONFIGURATION MANAGEMENT ---

def _init_global_config() -> Dict[str, Any]:
    """Initializes global config if it doesn't exist. Now only prompts for company name."""
    print(f"👋 First run initialization: Creating global config at {GLOBAL_CONFIG_FILE}")
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Prompt for Default Company
    print("\n--- Default Company Setup ---")
    company_name = input("Enter the name for your default company/profile (e.g., Acme Corp): ").strip()
    # We no longer prompt for copyright text, as it is derived from the company name
    author_name = input("Enter your default Author Name: ").strip()
    author_email = input("Enter your default Author Email: ").strip()

    config_data = {
        "default_company": company_name,
        "profiles": {
            company_name: {
                "company_name": company_name, # Storing company name explicitly
                "default_author_name": author_name,
                "default_author_email": author_email
            }
        }
    }

    with open(GLOBAL_CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=2)
    print(f"✅ Global configuration saved.")
    return config_data

def _get_global_config() -> Dict[str, Any]:
    """Loads global config, or initializes it if missing."""
    if not GLOBAL_CONFIG_FILE.exists():
        return _init_global_config()
    with open(GLOBAL_CONFIG_FILE, 'r') as f:
        return json.load(f)

def _init_repo_config(git_root: Path, global_config: Dict[str, Any]) -> Dict[str, str]:
    """Guides the user through setting up the repository-specific config."""
    profiles = global_config['profiles']
    repo_config_path = git_root / REPO_CONFIG_FILE

    print(f"\n--- Repository Setup at {git_root} ---")
    
    # 1. Company Selection
    print("Please select a company profile for this repository:")
    company_options = list(profiles.keys())
    company_options.append("Add New Company")
    company_options.append("Continue Without Company")

    for i, name in enumerate(company_options):
        print(f"[{i+1}] {name}")

    while True:
        try:
            choice = int(input(f"Enter choice (1-{len(company_options)}): ")) - 1
            if 0 <= choice < len(company_options):
                break
            else:
                raise ValueError
        except ValueError:
            print("Invalid choice. Please try again.")

    selected_key = company_options[choice]
    repo_config = {}

    if selected_key == "Continue Without Company":
        print("ℹ️ Continuing without saving a company profile for this repo.")
        default_key = global_config['default_company']
        default_profile = profiles[default_key]
        
        # Must prompt for Author/Email if not linked to a saved profile
        repo_config = {
            "company_name": input("Enter Company Name for Copyright: ").strip(),
            "author_name": input(f"Enter Author Name (Default: {default_profile['default_author_name']}): ") or default_profile['default_author_name'],
            "author_email": input(f"Enter Author Email (Default: {default_profile['default_author_email']}): ") or default_profile['default_author_email'],
        }
        return repo_config # Do not save .headerize.config or update global

    elif selected_key == "Add New Company":
        print("\n--- New Company Profile Setup ---")
        new_company_name = input("Enter NEW Company Name: ").strip()
        author_name = input("Enter Author Name: ").strip()
        author_email = input("Enter Author Email: ").strip()

        # Update Global Config
        profiles[new_company_name] = {
            "company_name": new_company_name,
            "default_author_name": author_name,
            "default_author_email": author_email
        }
        with open(GLOBAL_CONFIG_FILE, 'w') as f:
            json.dump(global_config, f, indent=2)
        print(f"✅ New company '{new_company_name}' added to global config.")

        # Create Repo Config
        repo_config = {
            "company_name": new_company_name,
            "author_name": author_name,
            "author_email": author_email,
        }
    else: # Existing Company Selected: Use defaults and do not prompt
        profile = profiles[selected_key]
        print(f"Selected existing profile: **{selected_key}**")
        
        repo_config = {
            "company_name": profile['company_name'],
            "author_name": profile['default_author_name'],
            "author_email": profile['default_author_email'],
        }
    
    # --- Shared Saving Logic for Git Repos (Not "Continue Without Company") ---
    
    # 2. Save Repo Config
    with open(repo_config_path, 'w') as f:
        json.dump(repo_config, f, indent=2)
    print(f"✅ Repository config saved to {REPO_CONFIG_FILE}. **Do not check this file into Git.**")

    # 3. Update .gitignore
    gitignore_path = git_root / GITIGNORE_FILE
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            content = f.read()
        if REPO_CONFIG_FILE.name not in content:
            with open(gitignore_path, 'a') as f:
                f.write(f"\n# Ignore headerize private config\n{REPO_CONFIG_FILE.name}\n")
            # print(f"✅ Added {REPO_CONFIG_FILE.name} to {GITIGNORE_FILE}.") # Commented for cleaner output

    # 4. Create COPYRIGHT.md
    copyright_md_path = git_root / 'COPYRIGHT.md'
    copyright_text = f"Copyright (c) {date.today().year} {repo_config['company_name']}. All rights reserved."
    if not copyright_md_path.exists():
        with open(copyright_md_path, 'w') as f:
            f.write(f"# Copyright Notice\n\n{copyright_text}\n")
        print("✅ Created `COPYRIGHT.md` at repo root.")
    
    return repo_config

def get_config(filepath: Path) -> Dict[str, str]:
    """Retrieves the appropriate configuration for the given file context."""
    global_config = _get_global_config()
    git_root = find_git_root(filepath.parent)
    
    if git_root:
        repo_config_path = git_root / REPO_CONFIG_FILE
        if repo_config_path.exists():
            with open(repo_config_path, 'r') as f:
                return json.load(f)
        else:
            return _init_repo_config(git_root, global_config)
    else:
        # Not in a Git repository, use global default
        default_key = global_config['default_company']
        profile = global_config['profiles'][default_key]
        print(f"ℹ️ Outside of Git repo. Using default profile: {default_key}")
        return {
            "company_name": profile['company_name'],
            "author_name": profile['default_author_name'],
            "author_email": profile['default_author_email'],
        }

# --- HEADER GENERATION ---

def generate_header(filepath: Path, config: Dict[str, str], description: str = "A brief description of the file's purpose.") -> str:
    """Generates the boilerplate header string with standardized copyright."""
    line_c, block_start, block_end, shebang_template = get_comment_style(filepath)

    current_year = date.today().year
    
    # **STANDARD COPYRIGHT FORMAT**
    copyright_line = f"Copyright (c) {current_year} {config['company_name']}. All rights reserved."

    # 1. Format the core content
    header_content = [
        f"Copyright: {copyright_line}",
        f"Author: {config['author_name']} <{config['author_email']}>",
        f"Created on: {date.today().isoformat()}",
        f"Description: {description}",
    ]

    # 2. Apply comment styling
    if block_start == line_c:
        # Line comments only (e.g., # or //)
        header_lines = [f"{line_c} {line}" for line in header_content]
        header_lines.insert(0, line_c)
        header_lines.append(line_c)
        header_text = "\n".join(header_lines) + "\n"
    else:
        # Block comments (e.g., /* */ or """ """)
        padded_content = "\n".join([f" {line}" for line in header_content])
        header_text = f"{block_start}\n{padded_content}\n{block_end}\n"
    
    return header_text

# --- APPLICATION CORE (No changes needed here) ---

def process_file(filepath: Path, config: Dict[str, str]):
    """Checks file, inserts header if absent, handling shebang."""
    if not filepath.is_file():
        return

    # Skip files that are likely config/data and not source code
    if filepath.name.startswith('.') or filepath.suffix.lower() in (
        '.json', '.log', '.png', '.jpg', '.gif', '.zip', '.gitignore', ''):
        return

    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️ Could not read {filepath}: {e}")
        return

    # Check for existing header (simple check: look for 'Copyright' in the first 10 lines)
    header_found = any('copyright' in line.lower() for line in lines[:10])

    if header_found:
        print(f"ℹ️ {filepath} already has a header. Skipping.")
        return

    # Generate the header block
    header_block = generate_header(filepath, config)
    
    # Handle Shebang
    shebang_line = None
    content_start_index = 0
    
    if lines and lines[0].startswith('#!'):
        shebang_line = lines[0]
        content_start_index = 1
    
    line_c, _, _, shebang_template = get_comment_style(filepath)
    
    # Insert shebang if missing and template exists
    if not shebang_line and shebang_template:
        # Insert generic shebang for the filetype
        new_content = [f"{shebang_template}\n", header_block] + lines
    else:
        # Shebang exists OR no shebang required, insert header after existing shebang (if any)
        new_content = lines[:content_start_index] + [header_block] + lines[content_start_index:]

    # Write the file
    with open(filepath, 'w') as f:
        f.writelines(new_content)
    
    print(f"✅ Inserted header into {filepath}")


def main():
    """Main function to parse arguments and drive the application."""
    parser = argparse.ArgumentParser(description="Automated boilerplate copyright header insertion tool.")
    parser.add_argument("path", nargs='?', default='.', help="File or directory to process.")
    parser.add_argument("-ft", "--filetype", help="Print header for a specific file type (e.g., script.py) to stdout and exit.", metavar="FILENAME")
    
    args = parser.parse_args()
    
    if args.filetype:
        # Mode: Print header to stdout
        filepath_dummy = Path(args.filetype)
        try:
            # Get config based on the current directory, but don't require file existence
            config = get_config(Path.cwd() / args.filetype) 
            header = generate_header(filepath_dummy, config)
            sys.stdout.write(header)
            return
        except Exception as e:
            sys.stderr.write(f"Error generating header: {e}\n")
            sys.exit(1)

    # Mode: Process file(s) in path
    target_path = Path(args.path)
    if not target_path.exists():
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)

    try:
        # Load configuration once based on the execution path
        config = get_config(target_path) 
    except Exception as e:
        print(f"🚨 Configuration Error: {e}")
        sys.exit(1)

    if target_path.is_file():
        process_file(target_path, config)
    elif target_path.is_dir():
        print(f"🔍 Processing directory: {target_path}")
        for filepath in target_path.rglob('*'):
            if filepath.is_file():
                process_file(filepath, config)


if __name__ == "__main__":
    main()
