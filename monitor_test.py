#!/usr/bin/env python3

import requests
import json
import os
import time
import ansible_runner
import logging
import argparse
import threading
from datetime import datetime
from pathlib import Path

DEFAULT_CONFIG_PATH = "/opt/repo-watcher/configs/dcgm_exporter.json"
LOCK_TIMEOUT = 600

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
)

def format_date(iso_str):
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%b %d, %Y @ %I:%M %p")
    except Exception:
        return iso_str or "unknown"
    
def acquire_with_timeout(lock, timeout, name=""):
    logging.info(f"[{name}] Waiting to acquire lock (timeout: {timeout}s)...")
    acquired = lock.acquire(timeout=timeout)
    if not acquired:
        logging.error(f"[{name}] Timed out after {timeout}s waiting for lock.")
    else:
        logging.info(f"[{name}] Acquired lock - starting pipeline")
    return acquired

def trigger_pipeline(event_type, value, repo_config, lock):
    """Trigger Ansible pipeline for a repository release or commit change."""
    repo_name = repo_config['repo'].lower()
    owner_name = repo_config['owner'].lower()
    exporter_name = repo_name.replace('-', '_')
    owner_repo_name = f"{owner_name}/{repo_name}"
    
    print(f"[ACTION] Trigger: {event_type} detected - {value} ({owner_repo_name})")
    logging.info(f"[ACTION] Triggering pipeline for {event_type} in {owner_repo_name}: {value}")
    
    if not acquire_with_timeout(lock, LOCK_TIMEOUT, owner_repo_name):
        return False

    # Determine version and git reference
    if event_type == "release":
        version = f"{value.strip('v')}-{time.strftime('%Y%m%d')}"
        git_ref = value
    elif event_type == "commit":
        short_sha = value[:7]
        version = f"commit-{short_sha}-{time.strftime('%Y%m%d')}"
        git_ref = value
    else:
        version = "unknown"
        git_ref = "HEAD"
    
    # Run ansible pipeline
    try:
        runner_path = "/opt/repo-watcher/pipeline"
        os.makedirs(runner_path, exist_ok=True)
        
        r = ansible_runner.run(
            private_data_dir=runner_path,
            project_dir = '/opt/repo-watcher/ansible',
            playbook='playbooks/build-packages.yml',
            extravars={
                "exporter_name": exporter_name,
                "version": version,
                "git_ref": git_ref,
                "repo_url": repo_config["repo_url"],
                "service_user": "james",
                "service_group": "james",
                "maintainer": "james@stninc.com",
                "description": f"{repo_name} exporter for monitoring {owner_name} components",
                "build_root": "/tmp/build",
                "staging_dir": "/opt/staging"
            }
        )

        if r.rc != 0:
            logging.error(f"[{owner_repo_name}] Pipeline failed! Status: {r.status}, RC: {r.rc}")
            return False
        else:
            logging.info(f"[{owner_repo_name}] Pipeline finished successfully: {r.status}")
            return True

    except Exception as e:
        logging.error(f"[{owner_repo_name}] Pipeline execution error: {e}")
        return False
    finally:
        lock.release()
        logging.info(f"[{owner_repo_name}] Released lock")

def monitor_single_repo(config, lock):
    OWNER = config["owner"]
    REPO = config["repo"]
    CHECK_INTERVAL = config["check_interval"]
    STATE_FILE = config["state_file"]
    LOG_FILE = config.get("log_file", "log/repo-watcher.log")
    BRANCH = config.get("branch", "main")

    OWNER_REPO_NAME = f"{OWNER}/{REPO}"
    REPO_NAME = f"{REPO}"
    RELEASES_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    COMMITS_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/commits?sha={BRANCH}&per_page=1"

    # Ensure log path exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def load_state():
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {"latest_release": "", "latest_commit": ""}

    def save_state(state):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)

    def check_release():
        try: 
            r = requests.get(RELEASES_URL)
            r.raise_for_status()
            data = r.json()
            return data["tag_name"], data.get("published_at", "unknown")
        except requests.exceptions.HTTPError as e:
            logging.error(f"[{OWNER_REPO_NAME}] GitHub API HTTP Error (release): {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"[{OWNER_REPO_NAME}] GitHub API Request Exception (release): {e}")
        return None, None

    def check_commit():
        try:
            r = requests.get(COMMITS_URL)
            r.raise_for_status()
            data = r.json()[0]
            return data["sha"], data["commit"]["committer"]["date"]
        except requests.exceptions.HTTPError as e:
            logging.error(f"[{OWNER_REPO_NAME}] GitHub API HTTP Error (commit): {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"[{OWNER_REPO_NAME}] GitHub API Request Exception (release): {e}")
        return None, None

    def run_check(state):
        try:
            latest_release, raw_release_date = check_release()
            latest_commit, raw_commit_date = check_commit()

            if not latest_release or not latest_commit:
                logging.warning(f"[{OWNER_REPO_NAME}] Skipping check cycle due to API error.")
                return

            release_date = format_date(raw_release_date)
            commit_date = format_date(raw_commit_date)

            if latest_release != state["latest_release"]:
                logging.info(f"[{OWNER_REPO_NAME}] New release detected: {latest_release} (published: {release_date})")
                print(f"[INFO] [{OWNER_REPO_NAME}] New release detected: {latest_release} (published: {release_date})")
                is_successful = trigger_pipeline("release", latest_release, config, lock)
                if is_successful:
                    state["latest_release"] = latest_release
                    state["latest_commit"] = latest_commit
                    save_state(state)

            elif latest_commit != state["latest_commit"]:
                logging.info(f"[{OWNER_REPO_NAME}] New commit detected on {BRANCH}: {latest_commit} (date: {commit_date})")
                print(f"[INFO] [{OWNER_REPO_NAME}] New commit detected on {BRANCH}: {latest_commit} (date: {commit_date})")
                is_successful = trigger_pipeline("commit", latest_commit, config, lock)
                if is_successful:
                    state["latest_commit"] = latest_commit
                    save_state(state)

            else:
                msg = (f"No new release or commit detected.\n"
                       f"Latest release: {state['latest_release']} (published: {release_date})\n"
                       f"Latest commit: {state['latest_commit']} (date: {commit_date})")
                print(f"[{OWNER_REPO_NAME}]: {msg}")
                logging.info(f"[{OWNER_REPO_NAME}]: {msg}")

        except Exception as e:
            logging.error(f"[{OWNER_REPO_NAME}] Error occurred: {e}")

    state = load_state()
    logging.info(f"[{OWNER_REPO_NAME}] Starting monitoring with check interval: {CHECK_INTERVAL}s")
    
    while True:
        run_check(state)
        time.sleep(CHECK_INTERVAL)

def reset_state(confirm=True):
    STATE_FILES_DIR = "/opt/repo-watcher/state"
    LOG_FILES_DIR = "/opt/repo-watcher/log"
    
    if confirm:
        print("This will delete all state and log files. Continue? (y/N):")
        confirm_input = input().strip().lower()
        if confirm_input != "y":
            print("[CANCELLED] No changes made.")
            return
    
    # Clean state files
    if os.path.exists(STATE_FILES_DIR):
        for file in os.listdir(STATE_FILES_DIR):
            if file.endswith(".json"):
                os.remove(os.path.join(STATE_FILES_DIR, file))
                print(f"[OK] Removed state file: {file}")
    
    # Clean log files
    if os.path.exists(LOG_FILES_DIR):
        for file in os.listdir(LOG_FILES_DIR):
            if file.endswith(".log"):
                os.remove(os.path.join(LOG_FILES_DIR, file))
                print(f"[OK] Removed log file: {file}")
    
    print("[OK] Reset complete.")

# ───────── CLI ENTRY POINT ─────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Github repo watcher")
    parser.add_argument("--config", "-c", help="Path to config file", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--once", action="store_true", help="Run a single check cycle and exit")
    parser.add_argument("--reset", action="store_true", help="Reset state/log files and exit")
    parser.add_argument("--multi", action="store_true", help="Monitor multiple repos from configs directory")
    args = parser.parse_args()

    if args.reset:
        reset_state()
        exit(0)

    # Global lock for ansible operations
    lock = threading.Lock()

    if args.multi:
        # Monitor multiple repositories
        CONFIG_DIR = Path("/opt/repo-watcher/configs")
        config_files = list(CONFIG_DIR.glob("*.json"))
        
        if not config_files:
            logging.error("No config files found in configs/")
            exit(1)
        
        threads = []
        for cfg_file in config_files:
            with open(cfg_file) as f:
                config = json.load(f)
            
            t = threading.Thread(target=monitor_single_repo, args=(config, lock))
            t.daemon = True
            t.start()
            threads.append(t)
            
        # Wait for threads
        for t in threads:
            t.join()
    else:
        # Monitor single repository
        with open(args.config) as f:
            config = json.load(f)
        
        if args.once:
            # Single run for testing
            state = load_state(config["state_file"])
            run_check = getattr(monitor_single_repo, "run_check", None)
            if callable(run_check):
                run_check(state)
            else:
                logging.error("Single run mode not available")
        else:
            # Continuous monitoring
            monitor_single_repo(config, lock)