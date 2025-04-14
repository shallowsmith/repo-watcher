#!/usr/bin/env python3

import requests
import json
import os
import time
import ansible_runner
import logging
import argparse
from datetime import datetime
from tools.reset_state import reset_state

DEFAULT_CONFIG_PATH = "/opt/repo-watcher/configs/dcgm_exporter.json"
LOCK_TIMEOUT = 600

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
    return True

def trigger_pipeline(event_type, value, owner_repo_name, repo_name, lock):
    print(f"[ACTION] Trigger: {event_type} detected - {value} ({owner_repo_name})")
    logging.info(f"Triggering pipeline for {event_type} in {owner_repo_name}: {value}")
        
    acquire_with_timeout(lock, LOCK_TIMEOUT, owner_repo_name)

    if event_type == "release":
        version = f"{value}-{time.strftime('%Y%m%d')}"
    elif event_type == "commit":
        short_sha = value[:7]
        version = f"commit{short_sha}-{time.strftime('%Y%m%d')}"
    else:
        version = "unknown"

    runner_path = f"/opt/repo-watcher/pipeline/"
    os.makedirs(runner_path, exist_ok=True)

    try:
        r = ansible_runner.run(
            private_data_dir=runner_path,
            playbook='test.yml',
            envvars={"PACKAGE_VERSION": version,
                     "OWNER_REPO_NAME": owner_repo_name,
                     "REPO_NAME": repo_name,
                     "EVENT_TYPE": event_type}
        )

        if r.rc != 0:
            logging.error(f"[{owner_repo_name}] Pipeline failed! Status: {r.status}, RC: {r.rc}")
        else:
            logging.info(f"[{owner_repo_name}] Pipeline finished: {r.status}")

    except Exception as e:
        logging.error(f"[{owner_repo_name}] Pipeline execution error: {e}")

    finally:
        lock.release()
        logging.info(f"[{owner_repo_name}] Released lock")

def monitor_single_repo(config, lock):
    OWNER = config["owner"]
    REPO = config["repo"]
    CHECK_INTERVAL = config["check_interval"]
    STATE_FILE = config["state_file"]
    LOG_FILE = "log/repo-watcher.log"

    OWNER_REPO_NAME = f"{OWNER}/{REPO}"
    REPO_NAME = f"{REPO}"
    RELEASES_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    COMMITS_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/commits?sha={config.get('branch','main')}&per_page=1"

    # Ensure log path exists before logging starts
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

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
        r = requests.get(RELEASES_URL)
        r.raise_for_status()
        data = r.json()
        return data["tag_name"], data.get("published_at", "unknown")

    def check_commit():
        r = requests.get(COMMITS_URL)
        r.raise_for_status()
        data = r.json()[0]
        return data["sha"], data["commit"]["committer"]["date"]

    def run_check(state):
        try:
            latest_release, raw_release_date = check_release()
            latest_commit, raw_commit_date = check_commit()

            release_date = format_date(raw_release_date)
            commit_date = format_date(raw_commit_date)

            if latest_release != state["latest_release"]:
                logging.info(f"[{OWNER_REPO_NAME}] New release detected: {latest_release} (published: {release_date})")
                print(f"[INFO] [{OWNER_REPO_NAME}] New release detected: {latest_release} (published: {release_date})")
                trigger_pipeline("release", latest_release, OWNER_REPO_NAME, REPO_NAME, lock)
                state["latest_release"] = latest_release
                state["latest_commit"] = latest_commit
                save_state(state)

            elif latest_commit != state["latest_commit"]:
                logging.info(f"[{OWNER_REPO_NAME}] New commit detected on main: {latest_commit} (date: {commit_date})")
                print(f"[INFO] [{OWNER_REPO_NAME}] New commit detected on main: {latest_release} (published: {release_date})")
                trigger_pipeline("commit", latest_commit, OWNER_REPO_NAME, REPO_NAME, lock)
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
    while True:
        run_check(state)
        time.sleep(CHECK_INTERVAL)

# ───────── CLI ENTRY POINT ─────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Github repo watcher")
    parser.add_argument("--config", "-c", help="Path to config file", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--once", action="store_true", help="Run a single check cycle and exit")
    parser.add_argument("--reset", action="store_true", help="Reset state/log files and exit")
    args = parser.parse_args()

    if args.reset:
        reset_state()
        exit(0)

    with open(args.config) as f:
        config = json.load(f)

    # Allow a single-run check for test/debug
    if args.once:
        def one_time_run():
            OWNER = config["owner"]
            REPO = config["repo"]
            CHECK_INTERVAL = config["check_interval"]
            STATE_FILE = config["state_file"]
            state = {}
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    state = json.load(f)
            else:
                state = {"latest_release": "", "latest_commit": ""}
            monitor_single_repo(config)
        one_time_run()
    else:
        monitor_single_repo(config)
