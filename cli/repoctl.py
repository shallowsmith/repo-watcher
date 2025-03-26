import argparse
import os
import shutil
import logging
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Source: https://docs.python.org/3.11/howto/argparse.html#argparse-tutorial

# Load config file 
CONFIG_FILE = Path(__file__).resolve().parent.parent / "cli-config.json"
if CONFIG_FILE.exists():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
else: 
    raise FileNotFoundError(f"Missing config: {CONFIG_FILE}")

# Fall back to default if config does not exist
STAGING_DIR = cfg.get("staging_dir", "/opt/staging")
REPO_DIR = cfg.get("repo_dir", "/opt/published")
LOG_FILE = cfg.get("log_file", "/opt/repo-watcher/log/repoctl.log")

# Ensure log directory and file exist
log_path = Path(LOG_FILE)
log_path.parent.mkdir(parents=True, exist_ok=True)
log_path.touch(exist_ok=True)

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def list_package():
    print("Available .deb package(s) in staging")
    for f in os.listdir(STAGING_DIR):
        if f.endswith(".deb"):
            print(f" - {f}")

def view_metadata(package_name):
    pkg_path = os.path.join(STAGING_DIR, package_name)
    if not os.path.exists(pkg_path):
        print(f"[ERROR] Package not found in staging: {package_name}")
        return

    try:
        output = subprocess.check_output(["dpkg-deb", "-I", pkg_path], text=True)
        print(f"\nMetadata for {package_name}:\n")
        print(output)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to extract metadata: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="repoctl: manage staged .deb package")
    subparsers = parser.add_subparsers(dest="command")
    
    # Subcommands
    subparsers.add_parser("list", help="List staged .deb packages")
    metadata_parser = subparsers.add_parser("meta", help="View metadata of a .deb file")
    metadata_parser.add_argument("package", help="The .deb file to inspect")

    # Optional flags
    parser.add_argument("--list", "-l", action="store_true", help="List staged .deb packages")
    parser.add_argument("--meta", "-m", metavar="PACKAGE", help="View metadata of a .deb file")

    args = parser.parse_args()

    if args.command == "list" or args.list:
        list_package()
    else:
        parser.print_help()