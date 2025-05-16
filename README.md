# repo-watcher ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)![Ansible](https://img.shields.io/badge/Ansible-000000?style=for-the-badge&logo=ansible&logoColor=white)![Jinja](https://img.shields.io/badge/Jinja2-B41717?style=for-the-badge&logo=jinja&logoColor=white)

<p align="center">
<img src="./public/stninc.png" alt="stninc" width="200"> <br/>
</p>

## Overview
This project contains two components: `monitor.py` and `repoctl.py`, working together to monitor an upstream GitHub repository, automatically build and stage `.deb` packages, and allow for manual promotion to an internal APT repository.

- `multi_monitor.py`: This is the entry point of the project that is an extension to the `monitor.py` allowing multi-repo support utilizing multi-threading.
- `monitor.py`: A Python-based systemd-compatible watcher service that monitors an upstream GitHub repository for new releases and commits to the main branch. It triggers an Ansible pipeline to build, package, and stage the binaries.
- `repoctl.py`: A CLI tool to review staged `.deb` packages, view metadata, check promotion status, and promote packages to the published APT repo.

## Getting Started
### Prerequisities
- Ubuntu 20.04
- Python 3.11+ (built on Python 3.11)

### Installation
1. Clone the Repo: <br/>
`git clone https://github.com/shallowsmith/repo-watcher.git`

2. Create, activate a virtual environment and install the required packages:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Create the necessary directories:
```bash
sudo mkdir -p /opt/staging /opt/published /opt/repo-watcher/log /opt/repo-watcher/state
sudo chmod 755 /opt/staging /opt/published /opt/repo-watcher/log /opt/repo-watcher/state
```

4. Copy the configuration files to the configs directory:
```bash
sudo mkdir -p /opt/repo-watcher/configs
sudo cp *.json /opt/repo-watcher/configs/
```

- A sample configuration file looks like:
```json
{
  "owner": "NVIDIA",
  "repo": "dcgm-exporter",
  "check_interval": 120,
  "state_file": "/opt/repo-watcher/state/dcgm_exporter_state.json",
  "log_file": "/opt/repo-watcher/log/dcgm_exporter.log",
  "branch": "main",
  "repo_url": "https://github.com/NVIDIA/dcgm-exporter"
}
```
## Multi-Repository Monitoring: `multi_monitor.py`
The `multi_monitor.py` script allows monitoring multiple repositories simultaneously. It reads all JSON configuration files from the `/opt/repo-watcher/configs/` directory and creates a separate thread for each repository.

To run:
```bash
python3 multi_monitor.py
```
- This is the recommended entry point for this project instead of `monitor.py`.

## GitHub Watcher Service: `monitor.py`  

`monitor.py` periodically queries the GitHub API for:
- The latest release tag or tag
- The latest commit SHA on the configured branch

If a new release, tag, or commit is detected:
- It triggers an Ansible pipeline to build and stage a `.deb` package
- Saves state in a JSON file to avoid repeated builds
- Logs all actions and errors for traceability

### Running monitor.py
```bash
# Run with default config
python3 monitor.py

# Run with specific config file
python3 monitor.py --config /path/to/config.json

# Run once and exit (useful for testing)
python3 monitor.py --once

# Reset state and log files
python3 monitor.py --reset
```


## CLI Tool: `repoctl.py`

`repoctl.py` is a CLI tool for interacting with staged `.deb` packages. It supports both subcommand-style and flag-based invocation.

### Configuration
The CLI tool uses a configuration file located at the project root `cli-config.json`:

```json
{
  "staging_dir": "/opt/staging",
  "repo_dir": "/opt/published", 
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

#### Remove a package
```bash
# Remove from staging (default)
python3 cli/repoctl.py remove dcgm-exporter_1.0.0.deb

# Remove from published repo
python3 cli/repoctl.py remove dcgm-exporter_1.0.0.deb --published

# Simulate removal (dry-run)
python3 cli/repoctl.py remove dcgm-exporter_1.0.0.deb --check
```

#### Reset repo state and log files
```bash
python3 tools/reset_state.py
#or
python3 monitor.py reset
```

## Ansible Pipeline

The project includes an Ansible-based pipeline that handles: 

1. Cloning the target repository
2. Building the software from source
3. Packaging it as a `.deb` file with proper metadata
4. Staging the package for review

### Pipeline Structure Details
#### Directory Structure
```
pipeline/
├── ansible.cfg                  # Ansible configuration
├── inventory/                   # Host definitions
│   ├── group_vars/
│   │   └── all.yml             # Common variables shared across playbooks
│   └── hosts                    # Inventory file (primarily localhost)
├── playbooks/                   # Orchestration playbooks
│   ├── build-packages.yml       # Main build process coordinator
│   ├── setup-dependencies.yml   # Installs system dependencies
│   └── test.yml                 # Test playbook
└── roles/                       # Modular components for specific tasks
    ├── common/                  # Shared tasks for all build processes
    │   └── tasks/
    │       └── main.yml         # Common build preparation tasks
    ├── dcgm/                    # NVIDIA DCGM specific build logic
    │   ├── tasks/
    │   │   └── main.yml         # DCGM build and package tasks
    │   └── templates/
    │       └── dcgm.service.j2  # DCGM service template
    ├── dcgm-exporter/           # NVIDIA DCGM Exporter specific build logic
    │   ├── tasks/
    │   │   └── main.yml         # DCGM Exporter build tasks
    │   └── templates/
    │       └── dcgm-exporter.service.j2  # Service template
    ├── node-exporter/           # Prometheus Node Exporter build logic
    │   ├── tasks/
    │   │   └── main.yml         # Node Exporter build tasks
    │   └── templates/
    │       └── node-exporter.service.j2  # Service template
    └── package-builder/         # Creates Debian packages
        ├── tasks/
        │   └── main.yml         # Packaging tasks
        └── templates/
            ├── control.j2       # Package control file template
            └── postinst.j2      # Post-installation script template
```

#### Execution Flow
1. Initialization: The main playbook `build-packages.yml` is triggered by `monitor.py` when a new release or commit is detected.

2. Common: The `common` role prepares the build enviornment, cloning the repository and ensuring directories exist. 

3. Role Based Build: Depending on the target software, the appropriate role is invoked to build the software. 

4. Packaging: The `package-builder` role packages the built binary into a `.deb` package with:
    - `DEBIAN/control` file with dependency information
    - Post-installation scripts for service startup
    - Systemd unit files for running service

## Scale the Project
To add support for a new type of repository:
1. Create a new configuration file in `/opt/repo-watcher/configs/`
2. Add a corresponding role in `/pipeline/roles/`
3. Implement the build logic specific to that repository
4. Reuse the common packaging infrastructure

## Logging
- `monitor.py`: Logs release/commit checks, errors, and pipeline triggers to configured log files
- `cli/repoctl.py`: Logs CLI actions like listing, publishing, metadata inspection to `/log/repoctl.log`

## Flowchart:
<img src="./public/flowchart.svg" alt="Mermaid Chart" style="max-width: 90%;">

### Notes:
Designed for internal use.

## TODO

### Watcher & Build Automation
- [x] Build Python script to monitor GitHub repo for new commits/releases
- [x] Externalize configuration (config.json)
- [x] Integrate Ansible Runner or subprocess trigger to call automation pipeline
- [x] Deploy watcher service on lab VM
- [x] Multithreading support for multiple repos
- [x] Implement logic to watch specific releases and commits. 

### Ansible Build Pipeline
- [x] Finalize playbook to clone repo, build, and package
- [x] Separate between commit and release builds
- [x] Implement dynamic version tagging for `.deb` files
- [x] Make config path configurable via CLI flag
- [x] Major refactor to follow the [Good Practices for Ansible](https://redhat-cop.github.io/automation-good-practices/)
- [x] Write proper ansible playbook for correct automation (check dependencies)

### Repo Flow
- [x] Define staging directory for review
- [x] Build CLI tool (repoctl.py)
- [x] Add a dry run flag to simulate actions without making changes
- [x] Integrate testing framework using GitHub Actions
- [x] Push `.deb` to APT repo, validate on target machines