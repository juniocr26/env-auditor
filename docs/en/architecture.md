# Architecture Decisions & Trade-offs

[English](architecture.md) | [Português](../pt-BR/architecture.md)

ENV Auditor is a local filesystem tool: discover environment sets, synchronize their key contract, classify source references, remove assignments with no evidence, then report the final structure. This document evaluates the implementation in [audit-envs.py](../../scripts/audit-envs.py), with the Technical Interview study guide as supporting context. Alternatives are review options, not undocumented historical decisions.

## Implementation status

- **Implemented:** standard-library Python CLI, environment discovery, asymmetric synchronization, multiline assignment blocks, duplicate/possible-secret reporting, strong/weak/no-evidence classification, exclusions, backups, dry-run, audit-only and strict exit status.
- **Designed / architecturally prepared:** `SyncAction` represents planned synchronization for dry-run; dataclasses/functions separate models, traversal, parsing, evidence and writes within one script. This is not a general transaction engine or plugin system.
- **Planned / future work:** no checked-in feature roadmap. Atomic replacement, locking, richer parsers and regression/CI suites are conditional improvements discussed below, not delivered capabilities. No checked-in automated test suite or CI workflow exists.

## Decision: Dependency-free Python CLI rather than a service

**Context.** The input is a workspace containing local text files, not a remote user/account workflow.

**Decision and why.** Python 3.10+ standard-library modules provide traversal, regex, JSON, dataclasses, argument parsing and backups without package installation. Running one script keeps the operation close to the developer's filesystem and exposes reviewable CLI modes. No database, Docker environment or network service is required.

**Alternatives.** Shell/awk would reduce runtime requirements but complicate multiline parsing and evidence models. Go/Rust could distribute a binary with compilation/platform packaging costs. A web service would add uploads/access control and unnecessarily move configuration values across a network.

**Trade-offs and consequences.** The custom parser and traversal rules belong to this project; there is no dependency supplying full dotenv semantics. The single script is easy to copy but large, so responsibility separation relies on named functions/dataclasses rather than package isolation. Timing output measures each local evidence scan, not a portable performance benchmark.

**Revisit when.** Packaging, independent extensions or full dotenv compatibility becomes necessary, or script size prevents maintaining/test-driving boundaries.

**Evidence:** imports, `EnvFile`, `UsageEvidence`, `SyncAction`, `main`, [README requirements](../../README.md#requirements).

## Decision: One directory is one environment contract

**Context.** Local/prod/test files can drift in key names while keeping different values.

**Decision and why.** Discovery groups `.env`, `.env.*` and `.env.example` in the same directory; each directory is an environment set even inside a monorepo. The union of real keys is added to the example as empty assignments. Missing real keys receive the example assignment block/default. No real value is copied into the example or another real environment.

**Alternatives.** A strict authoritative example could reject extra runtime keys instead of incorporating them. Per-environment schemas would support deliberately different key sets with more configuration. A shared root-wide contract would incorrectly merge independent projects.

**Trade-offs and consequences.** Environment-specific keys become shared placeholders; parity means equal keys, not valid values or a working application. Example defaults must already be safe. Existing values are not overwritten for matching keys. Synchronization runs before evidence cleanup, so a newly added unused key may then be removed. Example-only creates `.env` unless the secret heuristic blocks it; environment-only creates an example. There is no registry of expected directories outside those discovered.

**Revisit when.** Different environments intentionally require different schemas or a reviewed example should reject unknown keys rather than grow automatically.

**Evidence:** `discover_projects`, `sync_project`, `create_example_from_envs`, `create_env_from_example`.

## Decision: Parse assignment blocks without evaluating environment syntax

**Context.** Key extraction and preserving a multiline default differ from interpreting shell or framework configuration.

**Decision and why.** A regex recognizes identifier assignments with optional `export`; quote scanning groups multiline values. `EnvEntry.block` preserves the assignment block for propagation. Duplicate names are reported; the entry map keeps the last recognized block. The tool reads text, not executable shell, and does not resolve variable interpolation.

**Alternatives.** A specialized dotenv parser could improve semantic compatibility but might normalize formatting or return only decoded values. Language-aware parsers would be much broader than key synchronization.

**Trade-offs and consequences.** Non-assignment/malformed lines are skipped, not comprehensively validated. Comments are preserved in the original during removal but are not attached to a copied assignment. Unterminated quoted values can absorb later lines; removing such a block can remove following content. Text rewriting normalizes line endings, and decoding with replacement is not byte-preserving for invalid UTF-8. Duplicate detection does not automatically repair duplicates or choose the application's effective value.

**Revisit when.** Files use more complex quoting/interpolation, exact formatting preservation is required, or malformed input must block modification.

**Evidence:** `ENV_LINE_RE`, `_quote_is_open`, `parse_env`, `remove_keys_from_env_file`.

## Decision: Heuristic evidence with conservative weak-reference preservation

**Context.** Variables can be consumed through several languages, helper functions or infrastructure outside the workspace.

**Decision and why.** Each candidate runtime/config file is read once per project scan. Known access patterns produce strong evidence; standalone uppercase tokens produce weak evidence. Any evidence preserves the key. `ignore_unused_keys` protects externally consumed names. Environment declarations, Markdown/docs and known binary assets are excluded as usage evidence so a variable does not justify itself simply by existing.

**Alternatives.** Exact token search alone would retain many stale keys. AST analysis could distinguish actual accesses from comments but requires language-specific parsers. Runtime tracing observes exercised paths, not every deployment path. A report-only tool avoids erroneous removals but requires manual cleanup.

**Trade-offs and consequences.** Regex matches in comments or strings can be strong/weak false positives; dynamic names and skipped/unreadable files can produce false negatives. File read failures during evidence scanning are silently skipped, so “no evidence” is not proof of non-use. Lowercase keys are parsed, but weak tokens recognize uppercase names. The scan reads complete files into memory and is not bounded by file size. Nested environment sets can cause repeated/overlapping scans because each project searches descendants. The local timing does not prove O(1) file work or constant memory; it avoids a separate reread for every key.

**Revisit when.** False removals occur, repositories become too large, or precise language semantics are required. Add regression cases and explicit exclusions before increasing automatic cleanup.

**Evidence:** `STRONG_USAGE_EXTRACTORS`, `ENV_TOKEN_RE`, `analyze_usage`, `iter_runtime_files`, [static-analysis limitations](../../README.md#important-limitation-of-static-usage-detection).

## Decision: Automatic cleanup with distinct review modes

**Context.** The tool automates maintenance, but evidence may be incomplete and writes affect local configuration.

**Decision and why.** Default execution synchronizes **and removes** keys with no evidence. Weak/excluded keys survive. `--audit-only` reports current files without synchronization/removal; `--dry-run` models synchronized key sets with `SyncAction` and simulates removal without writing. The modes are mutually exclusive. `--show-usage` exposes key/path evidence for developer review.

**Alternatives.** An explicit opt-in cleanup flag or interactive confirmation would reduce surprise but change automation behavior. The current CLI has neither; there is no `--remove-unused` flag.

**Trade-offs and consequences.** Normal execution is not a safe read-only default. Dry-run models key sets, not a complete transactional file-content plan; per-file removal lists use physical files and may omit keys that would first be created. `--strict` determines final exit status after processing, not a preflight or write prohibition. `--strict-unused` requires strict and is most useful with audit-only since normal cleanup removes findings. Non-strict runs may exit 0 while reporting review issues. Argument errors exit through argparse; handled configuration RuntimeErrors return 2, while not all filesystem exceptions are handled by that path.

**Revisit when.** CI or a team needs enforced review-before-write, a machine-readable plan or predictable error classification. Use `--audit-only --strict` for current read-only CI checks; no CI integration is shipped.

**Evidence:** `audit`, `main`, CLI help. Temporary-fixture investigation confirmed unchanged bytes under audit/dry-run and normal cleanup/strict behavior.

## Decision: Secret heuristics and key-only reporting, without a secrecy guarantee

**Context.** Example defaults can be versioned/copied; local credentials should not be propagated.

**Decision and why.** Names matching sensitive terms plus non-placeholder values are reported in `.env.example`; `public_non_secret_keys` explicitly bypasses that heuristic. Output routines report key names and paths instead of environment assignment values. Synchronization and example-only `.env` creation are blocked when suspicious example entries are detected.

**Alternatives.** Dedicated secret scanners can recognize more patterns/history; a secret manager changes how values are stored/distributed, not merely key parity.

**Trade-offs and consequences.** This is not entropy scanning, semantic validation or secret remediation. A credential under an innocuous key can be missed; a safe default under PASSWORD may be flagged. Values are read into memory and copied into backups. Blocking synchronization does **not** block later automatic unused-key cleanup: investigation reproduced removal of an unrelated unused key while the suspicious example still caused strict exit 1. Do not interpret the guard as global write protection. The reporting code avoids printing assignment values, but paths/key names and configuration parse-error diagnostics may themselves be sensitive; it is not an arbitrary-input log-redaction guarantee.

**Revisit when.** A security gate must prevent every write on a suspect file, logs require comprehensive redaction, or secret detection must satisfy stronger requirements.

**Evidence:** `SECRET_NAME_RE`, `SAFE_PLACEHOLDER_RE`, `suspicious_example_keys`, `sync_project`, `audit`, `load_audit_config`.

## Decision: Backups and bounded traversal instead of transactional filesystem management

**Context.** Developers need recovery of existing configuration without infrastructure.

**Decision and why.** Existing files are copied before each mutation into root-relative timestamped `.env-audit-backups`; backup-directory/file permissions attempt 0700/0600. New files have no previous version to back up. `os.walk` prunes known dependency/storage/cache directories and configured ignored paths; directory symlinks are not followed by default.

**Alternatives.** Atomic temporary-file replacement, locking and a staged multi-file plan could improve interruption/concurrent-run behavior. Version-control recovery is unsuitable for uncommitted secrets; storing backups remotely introduces secret exposure/retention requirements.

**Trade-offs and consequences.** Writes use direct `write_text`, without atomic rename, locks or global rollback; failure between files can leave partial synchronization. Backups contain full real values and need protection/retention; permission changes are best effort and new files follow the process umask. File symlinks can still be read/written through, and resolved root does not impose containment on every discovered target. Ignore rules are lexical, not a sandbox. `ignore_files` filters candidate usage files and prunes matching directories, but discovery does not apply it to each env filename; `ignore_projects` controls discovery, not a complete exclusion from another parent's recursive usage scan. Keep the reviewed root/exclusions deliberate.

**Revisit when.** Multiple runs may overlap, configuration is critical, symlink boundaries matter or recovery must be atomic. Those requirements justify stronger filesystem semantics, not a database/web service by default.

**Evidence:** `is_ignored`, `discover_projects`, `iter_runtime_files`, `backup_path_for`, `create_backup`, `append_section`, `remove_keys_from_env_file`.

## Runtime investigation — 2026-10-05

The script was executed with standard-library Python against three `TemporaryDirectory` fixture sets, never the portfolio's real environments. Hash snapshots confirmed that audit-only and dry-run left fixture bytes unchanged. Normal mode removed the no-evidence key, preserved weak/excluded keys, copied an example default and created three backups without copying the real fixture value into the example or printing it. An example-only possible secret blocked `.env` creation and yielded strict exit 1. A separate fixture reproduced unused cleanup despite synchronization being blocked by a possible secret. All temporary environments, source/config fixtures and backups were removed automatically. These targeted experiments are not a newly shipped automated regression suite or exhaustive parser/security verification.
