#!/usr/bin/env python3

import os
import json
import threading
import time
import logging
from pathlib import Path
from monitor_test import monitor_single_repo

CONFIG_DIR = Path("configs")  
DEFAULT_INTERVAL = 120 

lock = threading.Lock()

def monitor_worker(config_path):
    with open(config_path) as f:
        config = json.load(f)

    owner = config["owner"]
    repo = config["repo"]
    repo_name = f"{owner}/{repo}"
    sanitized_repo = repo.replace('/', '_').replace('-', '_')
    
    log_file_path = f"log/{sanitized_repo}.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    config["log_file"] = log_file_path  

    print(f"[Thread] [{repo_name}] Starting watcher for {repo_name} (every {config.get('check_interval', DEFAULT_INTERVAL)}s)")

    monitor_single_repo(config, lock)

def main():

    config_files = list(CONFIG_DIR.glob("*.json"))
    if not config_files:
        msg = "[ERROR] No config files found in configs/"
        print(f"{msg}")
        logging.error(f"{msg}")
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
