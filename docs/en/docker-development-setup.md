# Development setup and recovery

Run commands from the host `env-auditor/` directory. This project has no Dockerfile, Compose services, profiles, entrypoints, package manifest or third-party dependencies. It is a Python standard-library CLI requiring Python 3.10 or newer. No Docker environment or artificial virtual environment is introduced. The audit executed `--help` successfully with host Python 3.14.7.

## Setup and safe operation

```sh
python3 --version
python3 scripts/audit-envs.py --help
# Read-only analysis of an explicitly chosen directory:
python3 scripts/audit-envs.py /path/to/selected/project --audit-only
```

Replace the last path with the intended project. Normal invocation synchronizes and removes environment keys and creates backups; do not use it as a harmless dependency check. `--audit-only` avoids changes. No workspace-wide audit or mutation was executed during this Docker audit.

| Component / manager | Container path | Physical host path | Mount | Purpose |
| --- | --- | --- | --- | --- |
| Python standard library / host interpreter | Not applicable | Installed host Python distribution | None | Runtime and bundled library; no downloadable project dependencies |

There is no dependency installation/recovery command, dependency cache, node_modules, vendor or generated environment required by this repository. If the interpreter is missing, restore your Python installation through the host tool you originally used; the repository does not prescribe an installer. Python bytecode is disposable generated output, not custom configuration. Platform compatibility is governed by the host interpreter rather than Linux binary packages.

## Configuration recovery

`.env-audit.json` is optional custom JSON configuration; no tracked template or generation command exists. Missing custom exclusions/allowlists require a backup, or deliberate manual reconfiguration following the README. Dependency installation cannot recover them. `.env-audit-backups/` contains generated backups of environment files. It is produced by normal mutating runs, not by read-only checks, and deleting it destroys that recovery history: recover it from another backup. Do not run the tool merely to manufacture replacement backups.

For a missing tracked script or documentation, first confirm the file is absent, then restore that exact path:

```sh
test -e scripts/audit-envs.py || git restore --source=HEAD -- scripts/audit-envs.py
```

For target projects' missing `.env` files, restore their own tracked templates only when absent and supply real values from backups/secret sources. ENV Auditor can generate blank keys or copy safe example defaults, but cannot reconstruct deleted custom settings or credentials. Never overwrite an existing configuration file.

## Shutdown and troubleshooting

The CLI exits after its run; there are no project containers, ports or persistent volumes to stop. Permission errors require read access to selected sources and, for intentionally mutating runs, write access to the specific files/backups. Do not use blanket permission changes. Hidden Docker mounts and stopped application containers are not applicable. Do not add pip/uv install commands: the script imports only standard-library modules.

## Verification (2026-10-06)

Inspected the entire tracked file list, README and script imports/CLI. Verified Python version and `--help` execution without modifying project settings. Third-party dependency host persistence is not applicable, rather than a Docker persistence pass. Container installation, recreation, recovery and application startup checks are not applicable. No containers or temporary resources were created.
