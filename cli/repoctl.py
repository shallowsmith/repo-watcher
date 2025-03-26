import argparse
import os
import shutil
import logging
import json
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="repoctl: manage staged .deb package")
    subparsers = parser.add_subparsers(dest="command")
    
    # list
    subparsers.add_parser("list", help="List staged .deb packages")

    args = parser.parse_args()

    if args.command == "list":
        list_package()
    else:
        parser.print_help()