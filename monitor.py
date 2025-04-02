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


DEFAULT_CONFIG_PATH = "/opt/repo-watcher/monitor-config.json"

parser = argparse.ArgumentParser(description="Github repo watcher")
parser.add_argument("--config", "-c", help="Path to config file", default=DEFAULT_CONFIG_PATH)
parser.add_argument("--once", action="store_true", help="Run a single check cycle and exit")
parser.add_argument("--reset", action="store_true", help="Reset state/log files and exit")

args = parser.parse_args()

# Load config file
with open(args.config) as f:
    config = json.load(f)

OWNER = config["owner"]
REPO = config["repo"]
CHECK_INTERVAL = config["check_interval"]
STATE_FILE = config["state_file"]
LOG_FILE = config["log_file"]

RELEASES_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
COMMITS_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/commits?sha=main&per_page=1"

# Logging setup
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
    sha = data["sha"]
    date = data["commit"]["committer"]["date"]
    return sha, date

def trigger_pipeline(event_type, value):
    print(f"[ACTION] Trigger: {event_type} detected - {value}")
    
    logging.info(f"Triggering pipeline for {event_type}: {value}")

    if event_type == "release":
        version = f"{value}-{time.strftime('%Y%m%d')}"
    elif event_type == "commit":
        short_sha = value[:7]
        version = f"commit{short_sha}-{time.strftime('%Y%m%d')}"
    else:
        version = "unknown"
    
    r = ansible_runner.run(
        private_data_dir = '/opt/repo-watcher/pipeline',
        playbook = 'build-and-package.yml',
        envvars={"PACKAGE_VERSION": version}
    )

    if r.rc != 0:
        logging.error(f"Pipeline failed! Status: {r.status}, RC: {r.rc}")
    else:
        logging.info(f"Pipeline finished: {r.status}")

def format_date(iso_str):
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%b %d, %Y @ %I:%M %p")
    except Exception:
        return iso_str or "unknown"

def run_check(state):
    try:
        latest_release, raw_release_date = check_release()
        latest_commit, raw_commit_date = check_commit()

        release_date = format_date(raw_release_date)
        commit_date = format_date(raw_commit_date)

        # Trigger release pipeline first
        if latest_release != state["latest_release"]:
            logging.info(f"New release detected: {latest_release} (published: {release_date})")
            trigger_pipeline("release", latest_release)
            state["latest_release"] = latest_release
            state["latest_commit"] = latest_commit
            save_state(state)

        # Only trigger commit pipeline if no new release is found
        elif latest_commit != state["latest_commit"]:
            logging.info(f"New commit detected on main: {latest_commit} (date: {commit_date})")
            trigger_pipeline("commit", latest_commit)
            state["latest_commit"] = latest_commit
            save_state(state)
        
        else:
            msg = (f"No new release or commit detected.\n"
                f"Latest release: {state['latest_release']} (published: {release_date})\n"
                f"Latest commit: {state['latest_commit']} (date: {commit_date})")
            print(f"[INFO] {msg}")
            logging.info(msg)

    except Exception as e:
        logging.error(f"Error occurred: {e}")

def main():
    logging.info("Repo watcher service started.")
    state = load_state()

    if args.once:
        run_check(state)
    elif args.reset:
        reset_state()
        exit(0)
    else:
        while True:
            run_check(state)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()