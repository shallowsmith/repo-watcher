# repo-watcher
## Overview
This is a Python-based systemd watcher service that monitors an upstream GitHub repository for new releases and commits to the main branch. Automation pipeline will be triggered via Ansible to build, package, and deploy the binaries onto local Ubuntu repository.

## TODO
1. 
- [x] Build Python script to monitor GitHub repo for new commits/releases
- [x] Externalize configuration (config.json)
- Integrate Ansible Runner or subprocess trigger to call automation pipeline
- Deploy watcher service on lab VM
- Switch to config.yaml (optional)

2. 
- Create or finalize Ansible playbook for:
    - Cloning repo
    - Building binary (make install)
    - Packaging .deb using dpkg-deb or fpm
- Make config file path configurable via a --config CLI argument
- Implement version tagging for .deb files

3. 
- Define staging directory for review
- Add approval step before publish
- Push .deb to APT repo, validate installation on target machines
- Slurm (in the future)

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

## Flowchart:
<img src="./flowchart.svg" alt="Mermaid Chart" style="max-width: 20%;">