import os
import argparse

MONITOR_LOG_FILE = "/opt/repo-watcher/log/monitor.log"
REPOCTL_LOG_FILE = "/opt/repo-watcher/log/repoctl.log"
STATE_FILE = "/opt/repo-watcher/repo_state.json"

FILES_TO_DELETE = {
    "Monitor log": MONITOR_LOG_FILE,
    "Repoctl log": REPOCTL_LOG_FILE,
    "Repo state": STATE_FILE
}

def reset_state(confirm=True):
    if confirm:
        print("This will delete the following files:")
        for label, path in FILES_TO_DELETE.items():
            print(f" - {label}: {path}")
        confirm_input = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if confirm_input != "y":
            print("[CANCELLED] No changes made.")
            return

    for label, path in FILES_TO_DELETE.items():
        if os.path.exists(path):
            os.remove(path)
            print(f"[OK] Removed {label} ({path})")
        else:
            print(f"[INFO] {label} not found. Skipped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset monitor state and log files.")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    reset_state(confirm=not args.yes)
