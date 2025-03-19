#!/usr/bin/env python3

import requests
import json
import os
import time
import logging

# ===================================================
# NOTE: PORTABLE VERSION FOR LOCAL TESTING
# ===================================================

# ============== Local Config ==============
OWNER = "NVIDIA"
REPO = "dcgm-exporter"
CHECK_INTERVAL = 30 
STATE_FILE = "repo_state.json" 
# ===================================================

RELEASES_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
COMMITS_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/commits?sha=main&per_page=1"

# ============== Console Logging ====================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
)
# ===================================================

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
    return r.json()["tag_name"]

def check_commit():
    r = requests.get(COMMITS_URL)
    r.raise_for_status()
    commit_data = r.json()[0]

    return {
        "sha": commit_data["sha"],
        "message": commit_data["commit"]["message"]
    }

def trigger_pipeline(event_type, value):
    logging.info(f"[ACTION] Detected {event_type} change → {value}")

def main():
    logging.info("🟢 Repo watcher started (testing mode)")
    state = load_state()

    while True:
        try:
            latest_release = check_release()
            if latest_release != state["latest_release"]:
                logging.info(f"New release detected: {latest_release}")
                trigger_pipeline("release", latest_release)
                state["latest_release"] = latest_release

            commit_info = check_commit()
            if commit_info["sha"] != state.get("latest_commit", ""):
                logging.info(f"New commit detected: {commit_info['sha']}")
                logging.info(f"Commit message: {commit_info['message']}")
                trigger_pipeline("commit", commit_info)
                state["latest_commit"] = commit_info["sha"]

            save_state(state)

        except Exception as e:
            logging.error(f"Error occurred: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
