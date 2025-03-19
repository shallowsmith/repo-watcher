# repo-watcher
## Overview
This is a Python-based systemd watcher service that monitors an upstream GitHub repository for new releases and commits to the main branch. Automation pipeline will be triggered via Ansible to build, package, and deploy the binaries onto local Ubuntu repository.

## TODO
- Define trigger pipeline.
- Switch to config.yaml (optional).
- Make config file path configurable via a --config CLI argument.
- Implement confirmation mechanism before deployment

## Usage
### Requirements:
- Python 3.x (built on Python 3.11)
- requests module (install via `pip install requests`)

### Config: 
Edit `config.json`

### Running: 
```bash
python3 monitor.py --config /path/to/config.json
```
(`*--config` flag will be implemented in the future)

### Testing on local environment:
- Navigate to /test

### Notes:
Designed for internal use.
