#!/usr/bin/env python3

import os
import json
import threading
import time
import logging
from pathlib import Path
from monitor import monitor_single_repo

CONFIG_DIR = Path("configs")  
DEFAULT_INTERVAL = 120 

lock = threading.Lock()

def monitor_worker(config_path):
    with open(config_path) as f:
        config = json.load(f)

    owner = config["owner"]
    repo = config["repo"]
    repo_name = f"{owner}/{repo}"
    
    sanitized_repo = repo.replace('-', '_').replace('/', '_').lower()
    
    log_dir = "/opt/repo-watcher/log"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file_path = os.path.join(log_dir, f"{sanitized_repo}.log")
    config["log_file"] = log_file_path
    
    logger = logging.getLogger(repo_name)
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    
    if logger.handlers:
        logger.handlers.clear()
    
    logger.addHandler(file_handler)

    startup_msg = f"Starting watcher for {repo_name} (check interval: {config.get('check_interval', DEFAULT_INTERVAL)}s)"
    print(f"[Thread] [{repo_name}] {startup_msg}")
    logger.info(f"[Thread] [{repo_name}] {startup_msg}")
    
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
