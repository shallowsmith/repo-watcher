#!/usr/bin/env python3

import os
import json
import threading
import time
from pathlib import Path
from monitor_test import monitor_single_repo

CONFIG_DIR = Path("configs")  
DEFAULT_INTERVAL = 30 

def monitor_worker(config_path):
    with open(config_path) as f:
        config = json.load(f)
    repo_name = f"{config['owner']}/{config['repo']}"
    print(f"[Thread] Starting watcher for {repo_name} (every {config.get('check_interval')}s)")
    monitor_single_repo(config)

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
