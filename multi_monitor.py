#!/usr/bin/env python3

import os
import json
import threading
import time
from pathlib import Path
import monitor_test

CONFIG_DIR = Path("configs")  
DEFAULT_INTERVAL = 30 

def monitor_worker(config_path):
    with open(config_path) as f:
        config = json.load(f)

    # Inject dynamic config into monitor_test.py
    monitor_test.config = config
    monitor_test.STATE_FILE = config.get("state_file")
    monitor_test.LOG_FILE = config.get("log_file")
    state = monitor_test.load_state()

    interval = config.get("check_interval", DEFAULT_INTERVAL)
    repo_id = f"{config['owner']}/{config['repo']}"

    print(f"[Thread] Starting watcher for {repo_id} (every {interval}s)")

    while True:
        monitor_test.run_check(state)
        time.sleep(interval)

def main():
    config_files = list(CONFIG_DIR.glob("*.json"))
    if not config_files:
        print("[ERROR] No config files found in configs/")
        return

    threads = []
    for cfg in config_files:
        t = threading.Thread(target=monitor_worker, args=(cfg,))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
