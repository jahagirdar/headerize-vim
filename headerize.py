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

# --- EXCLUSION LISTS ---
# Comprehensive list of folders/patterns that should never be modified.
EXCLUDE_FOLDERS = [
    '.git', '.svn', '.hg', 
    'node_modules', 'vendor', 'target', 'build', 'dist', 'bin', 'out', 
    '.idea', '.vscode', '__pycache__', 'venv', '.*', 'coverage', 'docs' # Added docs
]
EXCLUDE_FILE_PATTERNS = [
    # General files
    '*.log', '*.dat', '*.bak', '*.zip', '*.rar', '*.tar', '*.gz', 
    '*.iml', '*.swp', '*~',
    # System/IDE files
    '.DS_Store', 'Thumbs.db', '.Spotlight-V100', 
    # Compiled/Binary files
    '*.pyc', '*.class', '*.o', '*.a', '*.so', '*.dll', '*.exe', '*.bin',
    # **NEW REQUIREMENT: Exclude all dotfiles**
    '.*'
]

# --- FILE TYPE MAPPINGS ---
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
    '.yaml': ('#', '#', '#', None),
    '.yml': ('#', '#', '#', None),
}

SKIP_FILE_SIGNAL: Tuple[None, None, None, None] = (None, None, None, None) 


# --- UTILITIES ---

def find_git_root(path: Path) -> Optional[Path]:
    """Traverse up the directory tree to find the .git directory."""
    current = path.resolve()
    while current != current.parent:
        if (current / '.git').is_dir():
            return current
        current = current.parent
    return None

def get_comment_style(filepath: Path) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Determines the comment style and shebang based on file extension.
    Returns SKIP_FILE_SIGNAL if the file should be ignored.
    """
    ext = filepath.suffix.lower()

    # Check for files without an extension (like 'README' or 'LICENSE')
    if not ext and filepath.name.count('.') == 0:
        # Whitelist common files without extensions to use '#' comment style
        if filepath.name.upper() in ('README', 'LICENSE', 'INSTALL', 'MAKEFILE'):
            return ('#', '#', '#', None)
        
        # Files without extensions that are not whitelisted are ignored
        return SKIP_FILE_SIGNAL

    # Use the .get() method with SKIP_FILE_SIGNAL as the default fallback
    return FILE_TYPE_MAP.get(ext, SKIP_FILE_SIGNAL)

# --- CONFIGURATION MANAGEMENT (No changes) ---

def _init_global_config() -> Dict[str, Any]:
    """Initializes global config if it doesn't exist. Now only prompts for company name."""
    print(f"👋 First run initialization: Creating global config at {GLOBAL_CONFIG_FILE}")
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Prompt for Default Company
    print("\n--- Default Company Setup ---")
    company_name = input("Enter the name for your default company/profile (e.g., Acme Corp): ").strip()
    author_name = input("Enter your default Author Name: ").strip()
    author_email = input("Enter your default Author Email: ").strip()

    config_data = {
        "default_company": company_name,
        "profiles": {
            company_name: {
                "company_name": company_name,
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
        
        repo_config = {
            "company_name": input("Enter Company Name for Copyright: ").strip(),
            "author_name": input(f"Enter Author Name (Default: {default_profile['default_author_name']}): ") or default_profile['default_author_name'],
            "author_email": input(f"Enter Author Email (Default: {default_profile['default_author_email']}): ") or default_profile['default_author_email'],
        }
        return repo_config 

    elif selected_key == "Add New Company":
        print("\n--- New Company Profile Setup ---")
        new_company_name = input("Enter NEW Company Name: ").strip()
        author_name = input("Enter Author Name: ").strip()
        author_email = input("Enter Author Email: ").strip()

        profiles[new_company_name] = {
            "company_name": new_company_name,
            "default_author_name": author_name,
            "default_author_email": author_email
        }
        with open(GLOBAL_CONFIG_FILE, 'w') as f:
            json.dump(global_config, f, indent=2)
        print(f"✅ New company '{new_company_name}' added to global config.")

        repo_config = {
            "company_name": new_company_name,
            "author_name": author_name,
            "author_email": author_email,
        }
    else: 
        profile = profiles[selected_key]
        print(f"Selected existing profile: **{selected_key}**")
        
        repo_config = {
            "company_name": profile['company_name'],
            "author_name": profile['default_author_name'],
            "author_email": profile['default_author_email'],
        }
    
    # --- Shared Saving Logic for Git Repos ---
    
    with open(repo_config_path, 'w') as f:
        json.dump(repo_config, f, indent=2)
    print(f"✅ Repository config saved to {REPO_CONFIG_FILE}. **Do not check this file into Git.**")

    gitignore_path = git_root / GITIGNORE_FILE
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            content = f.read()
        if REPO_CONFIG_FILE.name not in content:
            with open(gitignore_path, 'a') as f:
                f.write(f"\n# Ignore headerize private config\n{REPO_CONFIG_FILE.name}\n")

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

# --- HEADER GENERATION (No changes) ---

def generate_header(filepath: Path, config: Dict[str, str], description: str = "A brief description of the file's purpose.") -> str:
    """Generates the boilerplate header string with standardized copyright."""
    line_c, block_start, block_end, _ = get_comment_style(filepath)

    current_year = date.today().year
    
    copyright_line = f"Copyright (c) {current_year} {config['company_name']}. All rights reserved."

    header_content = [
        f"Copyright: {copyright_line}",
        f"Author: {config['author_name']} <{config['author_email']}>",
        f"Created on: {date.today().isoformat()}",
        f"Description: {description}",
    ]

    if block_start == line_c and block_start is not None:
        header_lines = [f"{line_c} {line}" for line in header_content]
        header_lines.insert(0, line_c)
        header_lines.append(line_c)
        header_text = "\n".join(header_lines) + "\n"
    elif block_start is not None and block_end is not None:
        padded_content = "\n".join([f" {line}" for line in header_content])
        header_text = f"{block_start}\n{padded_content}\n{block_end}\n"
    else:
        sys.stderr.write(f"Warning: Invalid comment style for {filepath.suffix}. Defaulting to Python docstring.\n")
        header_text = '"""\n' + '\n'.join([f" {line}" for line in header_content]) + '\n"""\n'
    
    return header_text

# --- APPLICATION CORE ---

def process_file(filepath: Path, config: Dict[str, str]):
    """Checks file, inserts header if absent, handling shebang."""
    if not filepath.is_file():
        return

    # Check the file type logic before opening the file
    comment_style = get_comment_style(filepath)
    if comment_style == SKIP_FILE_SIGNAL:
        return

    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️ Could not read {filepath}: {e}")
        return

    # Check for existing header
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
    
    line_c, _, _, shebang_template = comment_style
    
    if not shebang_line and shebang_template:
        new_content = [f"{shebang_template}\n", header_block] + lines
    else:
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
        # Mode: Print header to stdout (Vim Plugin Mode)
        filepath_dummy = Path(args.filetype)
        
        # Must check for dotfiles here, as the full exclusion list is only processed in the batch mode below.
        if filepath_dummy.name.startswith('.'):
            return

        if get_comment_style(filepath_dummy) == SKIP_FILE_SIGNAL:
            return 

        try:
            config = get_config(Path.cwd() / args.filetype) 
            header = generate_header(filepath_dummy, config)
            sys.stdout.write(header)
            return
        except EOFError:
            sys.stderr.write("Configuration Error: Please run 'headerize.py' manually in your terminal to complete the setup for this project/repo.\n")
            sys.exit(1)
        except Exception as e:
            sys.stderr.write(f"Error generating header: {e}\n")
            sys.exit(1)

    # Mode: Process file(s) in path (Interactive/Batch Mode)
    target_path = Path(args.path)
    if not target_path.exists():
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)

    try:
        config = get_config(target_path) 
    except EOFError:
        print("🚨 Configuration setup required. Please complete the interactive prompts above.")
        sys.exit(1)
    except Exception as e:
        print(f"🚨 Configuration Error: {e}")
        sys.exit(1)

    if target_path.is_file():
        # Check exclusions even for single file mode
        if any(Path(target_path.name).match(pattern) for pattern in EXCLUDE_FILE_PATTERNS):
            print(f"➖ Ignoring {target_path}: Matches exclusion pattern.")
            return

        if any(folder in target_path.parts for folder in EXCLUDE_FOLDERS):
            print(f"➖ Ignoring {target_path}: Located in an excluded folder.")
            return

        process_file(target_path, config)
        
    # ... (inside the main function) ...
    elif target_path.is_dir():
        print(f"🔍 Processing directory: {target_path}")

        # Get the absolute path of the directory we are processing to check for top-level exclusions
        abs_target_path = target_path.resolve()

        for filepath in target_path.rglob('*'):
            if not filepath.is_file():
                continue

            # --- FULL EXCLUSION LOGIC ---

            # 1. Check for Excluded Folders (Checks if the absolute path contains any excluded folder part)
            # This is the most reliable way to catch e.g., /project/repo/.venv/file.py
            filepath_parts = [p.lower() for p in filepath.parts]
            if any(folder.lower() in filepath_parts for folder in EXCLUDE_FOLDERS):
                continue

            # 2. Check for Excluded File Patterns (Dotfiles, compiled, etc.)
            filename = filepath.name
            if any(Path(filename).match(pattern) for pattern in EXCLUDE_FILE_PATTERNS):
                continue

            # 3. Process file only if it passed all exclusions
            process_file(filepath, config)
# ...


if __name__ == "__main__":
    main()
