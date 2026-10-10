# env-auditor

[English](README.md) | [Português brasileiro](README.pt-BR.md)

Python 3.10+ CLI, standard library only. Normal execution synchronizes environment files using authoritative examples, audits their structure, and automatically backs up changed existing targets.

## Documentation catalog and reading path

- [Complete categorized catalog](docs/en/index.md)
- [Review checklist and evidence gaps](docs/en/operations/completion-checklist.md)

Read purpose/setup first, then architecture and contracts, security and failures, tests/evidence, and local deployment/recovery. This is an independent portfolio project; runtime procedures in the documentation were not executed in the 2026-10-10 review.

From `Portifólio/env-auditor`:

```bash
python3 -B scripts/audit-envs.py
python3 -B scripts/audit-envs.py --dry-run
python3 -B scripts/audit-envs.py --audit-only
python3 -B scripts/audit-envs.py /absolute/scan/root
```

The default is exactly `Path(__file__).resolve().parents[2]`: the parent workspace of `env-auditor`, currently `Portifólio`. It is independent of the caller's working directory. From `Portifólio`, use `python3 -B env-auditor/scripts/audit-envs.py`; from `env-auditor/scripts`, use `python3 -B audit-envs.py`. No working-directory change is made. Explicit relative roots resolve against the caller. Nonexistent or non-directory roots are rejected.

Both preview modes calculate the same proposed synchronization without writing targets, backups, directories, or any other files. They are mutually exclusive. Preview differences alone do not cause failure.

## Discovery and synchronization

Recursive filesystem discovery includes siblings, nested and hidden directories, and Git-ignored files. Git tracking and application source code are not consulted. Eligible names are `.env` and `.env.*`. All names ending in `.example` are references and never runtime targets.

Each `.env.example` controls `.env` in its directory. Variants such as `.env.prod` prefer `.env.prod.example` and otherwise use the same-directory `.env.example`. Specific examples create missing corresponding targets; the base example creates `.env`, but does not invent variants. Targets without examples remain unchanged and are reported as skipped. References are never edited or generated from runtime values.

Missing assignments are copied literally from the reference. Existing values, including empty values, comments, formatting, duplicates of retained keys, and quoted multiline assignment blocks are preserved. Active assignments absent from the selected example are removed solely on that basis. UTF-8 and single/double quoted multiline literals are supported. Contents are never executed, expanded, interpolated, or sourced. An empty valid example has zero keys. Duplicate example keys, invalid UTF-8, malformed assignments, unterminated quotes, and unreadable inputs cause an error and leave the corresponding target unchanged. New targets copy the validated example, including comments.

Excluded directory names:

```text
.git .hg .svn node_modules vendor __pycache__ .venv venv
.env-audit-backups backups backup dist build out target .next .nuxt .cache
coverage .pytest_cache .tox
```

Also excluded: `bootstrap/cache`, `public/build`, filenames containing `.bak`, and filenames ending in `~`. Symbolic links are reported and skipped; symbolic directories and environment files are never followed. Discovery errors are reported and cause failure; an empty-discovery message appears only after successful empty discovery.

## Backups and writes

Before modifying an existing target, save exact original bytes and only the removed assignment blocks:

```text
<scan-root>/.env-audit-backups/<UTC timestamp plus unique suffix>/<relative directory>/<filename>.original
<scan-root>/.env-audit-backups/<UTC timestamp plus unique suffix>/<relative directory>/<filename>.removed
```

Backup directories use permissions `0700`, files use `0600`, and the backup root has a local `.gitignore` containing `*`. Backup directory names are collision-safe. Backup failure prevents modification of that target; partial backups may remain after a failure. Unchanged and new targets do not create backups. Target writes use a temporary file in the same directory and atomic replacement; temporary-file cleanup is attempted after failures; cleanup can itself fail. Existing permission bits are preserved, and new targets use `0600`.

Reports retain discovery, skips, errors and backup paths. Complete Unicode tables show every key without values; a project summary excludes shared keys and distinguishes proposed, completed, failed and unapplied actions. Initial comparison counts are separate from actual writes. See the [report guide](docs/en/guides/project-guide.md#complete-report-and-action-summary) and [synthetic terminal examples](docs/en/operations/terminal-report.md).

## Exit status and retired features

- `0`: processing completed without discovery or pair errors, including successful previews.
- `1`: discovery or processing errors; other eligible pairs are still processed.
- `2`: invalid root or CLI arguments.

`--strict`, `--strict-unused`, `--show-usage`, and `--no-backup` are retired and rejected. `.env-audit.json` is retired: its presence is reported and its settings are ignored. Static usage deletion and generation/modification of examples have been removed.

## Verification and limitations

```bash
# From Portifólio:
python3 -B -m unittest discover -s env-auditor/tests -v
python3 -B env-auditor/scripts/audit-envs.py --dry-run
```

Tests use temporary fixtures for synchronization writes and inject permission failures so they are reliable even with elevated privileges. The real workspace is checked only in preview mode.

Atomic replacement is per target; there is no transaction across all targets and no concurrent-writer lock. Do not edit files concurrently with synchronization. POSIX permission bits are used; ownership, ACLs, timestamps, and extended attributes are not preserved. The parser handles literal assignments and comments, not arbitrary shell scripts. References are authoritative; preview their changes before synchronization.

[Architecture](docs/en/architecture/overview.md) · [Guide](docs/en/guides/project-guide.md) · [Setup](docs/en/guides/setup.md) · [Verification](docs/en/testing/verification.md) · [License](LICENSE)


Static review clarified filesystem race, crash-durability and unexcluded hidden-storage limits in [architecture](docs/en/architecture/overview.md). Test commands above are documented instructions; this documentation audit did not execute them.
