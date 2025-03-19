#!/usr/bin/env python3

import requests
import json
import os
import time
# import subprocess
import logging

# Load config file
with open("/opt/repo-watcher/config.json", "r") as f:
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
    format='%(asctime)s [%(levelname)s] %(messages)s'
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
    return r.json()["tag_name"]

def check_commit():
    r = requests.get(COMMITS_URL)
    r.raise_for_status()
    return r.json()[0]["sha"]

def trigger_pipeline(event_type, value):
    logging.info(f"Triggering pipeline for {event_type}: {value}")
    # Placeholder automation
    print(f"[ACTION] Trigger: {event_type} detected - {value}")
    # subprocess.run(["ansible-playbook", "/opt/repo-watcher/build-and-package.yml"])

def main():
    logging.info("Repo watcher service started.")
    state = load_state()

    while True:
        try:
            latest_release = check_release()
            if latest_release != state["latest_release"]:
                logging.info(f"New release detected: {latest_release}")
                trigger_pipeline("release", latest_release)
                state["latest_release"] = latest_release

            latest_commit = check_commit()
            if latest_commit != state["latest_commit"]:
                logging.info(f"New commit detected on main: {latest_commit}")
                trigger_pipeline("commit", latest_commit)
                state["latest_commit"] = latest_commit

            save_state(state)

        except Exception as e:
            logging.error(f"Error occurred: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()