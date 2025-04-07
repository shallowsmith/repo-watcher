#!/usr/bin/env python3

import os
import json
import threading
import time
from pathlib import Path
from monitor import run_check, load_state  

CONFIG_DIR = Path("configs")  
CHECK_INTERVAL = 30 # fallback interval 

def monitor_worker(config_path):
    with open(config_path) as f:
        config = json.load(f)

    state = load_state(config.get("state_file"))
    interval = config.get("check_interval", CHECK_INTERVAL)
    repo_name = f"{config['owner']}/{config['repo']}"

    print(f"[Thread] Starting monitor for {repo_name}")

    while True:
        run_check(config, state)
        time.sleep(interval)

def main():
    config_files = list(CONFIG_DIR.glob("*.json"))
    if not config_files:
        print("[ERROR] No config files found in configs/")
        return

    threads = []
    for config_path in config_files:
        t = threading.Thread(target=monitor_worker, args=(config_path,))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
