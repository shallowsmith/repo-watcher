#!/usr/bin/env python3

import os
import json
import threading
import time
import logging
from pathlib import Path
from monitor_test import monitor_single_repo

CONFIG_DIR = Path("configs")  
DEFAULT_INTERVAL = 30 
LOG_FILE = "log/repo-watcher.log"

lock = threading.Lock()

def setup_log():
    # Ensure log path exists before logging starts
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

def monitor_worker(config_path):
    with open(config_path) as f:
        config = json.load(f)
    repo_name = f"{config['owner']}/{config['repo']}"
    msg = f"[Thread] [{repo_name}] Starting watcher for {repo_name} (every {config.get('check_interval')}s)"
    print(f"{msg}")
    logging.info(f"{msg}")
    monitor_single_repo(config, lock)

def main():
    setup_log()

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
