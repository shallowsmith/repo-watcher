# repo-watcher
## Overview
This project contains two components: `monitor.py` and `repoctl.py`, working together to monitor an upstream GitHub repository, automatically build and stage `.deb` packages, and allow for manual promotion to an internal APT repository.

- `monitor.py`: A Python-based systemd-compatible watcher service that monitors an upstream GitHub repository for new releases and commits to the main branch. It triggers an Ansible pipeline to build, package, and stage the binaries.
- `repoctl.py`: A CLI tool to review staged `.deb` packages, view metadata, check promotion status, and promote packages to the published APT repo.

## Getting Started
### Prerequisities
- Ubuntu 20.04
- Python 3.11+ (built on Python 3.11)

### Installation
Clone the Repo: <br/>
`git clone https://github.com/shallowsmith/repo-watcher.git`

Create, activate a virtual environment and install the required packages:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## GitHub Watcher Service: monitor.py  

`monitor.py` periodically queries the GitHub API for:
- The latest release tag
- The latest commit SHA on the `main` branch

If a new release or commit is detected:
- It triggers an Ansible Runner pipeline to build and stage a `.deb` package
- Saves state in a JSON file to avoid repeated builds
- Logs all actions and errors for traceability

### Example `config.json`
```json
{
  "owner": "NVIDIA",
  "repo": "dcgm-exporter",
  "check_interval": 1800,
  "state_file": "/opt/repo-watcher/repo_state.json",
  "log_file": "/opt/repo-watcher/log/monitor.log"
}
```

### Running monitor.py
```bash
python3 monitor.py  # uses deafult config
# or
python3 monitor.py --config /path/to/config.json
```


## CLI Tool: repoctl.py

`repoctl.py` is a lightweight CLI utility for interacting with staged `.deb` packages. It supports both subcommand-style and flag-based invocation.

### Example `cli-config.json`
```json
{
  "staging_dir": "/opt/staging",
  "repo_dir": "/opt/published",  // To be changed later
  "log_file": "/opt/repo-watcher/log/repoctl.log"
}
```

### Commands:

#### List staged packages
```bash
python3 cli/repoctl.py list
# or
python3 cli/repoctl.py --list
```

#### View package metadata
```bash
python3 cli/repoctl.py meta <package.deb>
# or
python3 cli/repoctl.py -m <package.deb>
```

#### Check promotion status
```bash
python3 cli/repoctl.py status <package.deb>
# or
python3 cli/repoctl.py -s <package.deb>
```

#### Promote package to repo
```bash
python3 cli/repoctl.py publish <package.deb>
# or
python3 cli/repoctl.py -p <package.deb>
```
#### Simulate promote without modifying (Dry run)
```bash
python3 cli/repoctl.py publish <package.deb> --check
```

### Remove a package
```bash
# Remove from staging (default)
python3 cli/repoctl.py remove dcgm-exporter_1.0.0.deb

# Remove from published repo
python3 cli/repoctl.py remove dcgm-exporter_1.0.0.deb --published

# Simulate removal (dry-run)
python3 cli/repoctl.py remove dcgm-exporter_1.0.0.deb --check
```

## TODO

### Watcher & Build Automation
- [x] Build Python script to monitor GitHub repo for new commits/releases
- [x] Externalize configuration (config.json)
- [x] Integrate Ansible Runner or subprocess trigger to call automation pipeline
- [x] Deploy watcher service on lab VM

### Ansible Build Pipeline
- [x] Finalize playbook to clone repo, build, and package
- [x] Separate between commit and release builds
- [x] Implement dynamic version tagging for `.deb` files
- [x] Make config path configurable via CLI flag

### Repo Flow
- [x] Define staging directory for review
- [x] Build CLI tool (repoctl.py)
- [x] Add a dry run flag to simulate actions without making changes
- [x] Integrate testing framework using GitHub Actions
- [ ] Push `.deb` to APT repo, validate on target machines
- [ ] Package monitor.py as systemd-managed service

## 📝 Logging
- `monitor.py`: Logs release/commit checks, errors, and pipeline triggers to `monitor.log`
- `repoctl.py`: Logs CLI actions like listing, publishing, metadata inspection to `repoctl.log`

### Testing on local environment:
- Navigate to /test

### Notes:
Designed for internal use.

## Flowchart:
<img src="./public/flowchart.svg" alt="Mermaid Chart" style="max-width: 20%;">