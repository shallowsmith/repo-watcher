import argparse
import os
import shutil
import logging
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Resource: https://docs.python.org/3.11/howto/argparse.html#argparse-tutorial

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

# List packages
def list_package():
    packages = [f for f in os.listdir(STAGING_DIR) if f.endswith(".deb")]
    logging.info(f"Listed staged packages: {packages if packages else 'None'}")
    print("Available .deb package(s) in staging:")
    for f in packages:
        print(f" - {f}")

# View metadata of the packages
def view_metadata(package_name):
    pkg_path = os.path.join(STAGING_DIR, package_name)
    if not os.path.exists(pkg_path):
        print(f"[ERROR] Package not found in staging: {package_name}")
        return

    try:
        output = subprocess.check_output(["dpkg-deb", "-I", pkg_path], text=True)
        print(f"\nMetadata for {package_name}:\n")
        print(output)
        logging.info(f"Viewed metadata for {package_name}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to extract metadata: {e}")

# Publish the package onto the repo
def publish_package(package_name, check_mode=False):
    src_path = os.path.join(STAGING_DIR, package_name)
    dest_path = os.path.join(REPO_DIR, package_name)

    if not os.path.exists(src_path):
        print(f"[ERROR] Package not found in staging: {package_name}")
        return
    
    if check_mode:
        print(f"[CHECK] would publish {package_name} to {REPO_DIR}")
        logging.info(f"[CHECK] would publish {package_name} to {REPO_DIR}")
        return
                     
    os.makedirs(REPO_DIR, exist_ok=True)
    shutil.copy2(src_path, dest_path)
    print(f"[OK] Published {package_name} to {REPO_DIR}")
    logging.info(f"Published {package_name} to {REPO_DIR}")

# Show status of the package
def show_status(package_name):
    dest_path = os.path.join(REPO_DIR, package_name)
    if os.path.exists(dest_path):
        print(f"[INFO] Package is already published: {package_name}")
    else:
        print(f"[INFO] Package is NOT published yet: {package_name}")
    logging.info(f"Checked status of {package_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="repoctl: manage staged .deb package")
    subparsers = parser.add_subparsers(dest="command")
    
    # Subcommands
    subparsers.add_parser("list", help="List staged .deb packages")
    metadata_parser = subparsers.add_parser("meta", help="View metadata of a .deb file")
    metadata_parser.add_argument("package", help="The .deb file to inspect")
    
    status_parser = subparsers.add_parser("status", help="Check publish status of a .deb file")
    status_parser.add_argument("package", help="The .deb file to check")

    publish_parser = subparsers.add_parser("publish", help="Publish a staged .deb package")
    publish_parser.add_argument("package", help="The .deb file to publish")
    publish_parser.add_argument("--check", action="store_true", help="Run in check mode")

    # Optional flags
    parser.add_argument("--list", "-l", action="store_true", help="List staged .deb packages")
    parser.add_argument("--meta", "-m", metavar="PACKAGE", help="View metadata of a .deb file")
    parser.add_argument("--status", "-s", metavar="PACKAGE", help="Check publish status of a .deb file")
    parser.add_argument("--publish", "-p", metavar="PACKAGE", help="Publish a staged .deb package")

    args = parser.parse_args()

    if args.command == "list" or args.list:
        list_package()
    elif args.command == "publish" or args.publish:
        publish_package(args.package, check_mode=args.check)
    elif args.command == "status" or args.status:
        show_status(args.status if args.status else args.package)
    elif args.command == "meta" or args.metadata:
        view_metadata(args.metadata if args.metadata else args.package)
    else:
        parser.print_help()