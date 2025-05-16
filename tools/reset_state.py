import os
import glob
import argparse

STATE_DIR = "/opt/repo-watcher/state"
LOG_DIR = "/opt/repo-watcher/log"
REPOCTL_LOG_FILE = os.path.join(LOG_DIR, "repoctl.log")

def reset_state(confirm=True):
    """
    Reset all state files and logs for repo-watcher.
    
    This deletes:
    1. All .json files in the state directory
    2. All .log files in the log directory
    3. The repoctl.log file specifically
    """
    # Collect state files
    state_files = glob.glob(os.path.join(STATE_DIR, "*.json"))
    
    # Collect log files
    log_files = glob.glob(os.path.join(LOG_DIR, "*.log"))
    
    # Create a dictionary of files to delete
    files_to_delete = {
        "State files": state_files,
        "Log files": log_files
    }
    
    if confirm:
        print("This will delete the following files:")
        total_files = 0
        
        for category, file_list in files_to_delete.items():
            if file_list:
                print(f"\n{category}:")
                for file_path in file_list:
                    print(f"  - {file_path}")
                    total_files += 1
        
        if total_files == 0:
            print("No files found to delete.")
            return
            
        confirm_input = input("\nAre you sure you want to continue? (y/N): ").strip().lower()
        if confirm_input != "y":
            print("[CANCELLED] No changes made.")
            return

    # Delete all files in each category
    deleted_count = 0
    skipped_count = 0
    
    for category, file_list in files_to_delete.items():
        for file_path in file_list:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"[OK] Removed {file_path}")
                    deleted_count += 1
                else:
                    print(f"[INFO] File not found: {file_path}")
                    skipped_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to remove {file_path}: {e}")
                skipped_count += 1
    
    # Print summary
    if deleted_count > 0 or skipped_count > 0:
        print(f"\nSummary: {deleted_count} files deleted, {skipped_count} files skipped")
    
    # Recreate empty directories if they were deleted
    for directory in [STATE_DIR, LOG_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"[INFO] Recreated directory: {directory}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset monitor state and log files.")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    reset_state(confirm=not args.yes)