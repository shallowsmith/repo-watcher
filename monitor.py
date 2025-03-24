#!/usr/bin/env python3

import requests
import json
import os
import time
import ansible_runner
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
    return r.json()["tag_name"]

def check_commit():
    r = requests.get(COMMITS_URL)
    r.raise_for_status()
    return r.json()[0]["sha"]

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
        logging.info(f"Pipeline finished successfully: {r.status}")
    

def main():
    logging.info("Repo watcher service started.")
    state = load_state()

    while True:
        try:
            latest_release = check_release()
            latest_commit = check_commit()

            # Trigger release pipeline first
            if latest_release != state["latest_release"]:
                logging.info(f"New release detected: {latest_release}")
                trigger_pipeline("release", latest_release)
                state["latest_release"] = latest_release
                state["latest_commit"] = latest_commit
                save_state(state)

            # Only trigger commit pipeline if no new release is found
            elif latest_commit != state["latest_commit"]:
                logging.info(f"New commit detected on main: {latest_commit}")
                trigger_pipeline("commit", latest_commit)
                state["latest_commit"] = latest_commit
                save_state(state)

        except Exception as e:
            logging.error(f"Error occurred: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()