# Operation, failures and evidence limits

[English](recovery-and-evidence.md) | [Português brasileiro](../../pt-BR/operations/recovery-and-evidence.md)

Static source review: 2026-10-10. Implemented facts, general theory and hypothetical changes are distinguished below. Runtime commands were not executed.

Use the CLI contract in the README before applying synchronization. `--dry-run` and `--audit-only` are mutually exclusive aliases for the same read-only plan. They do not create targets or backups. A proposed difference alone exits 0; handled discovery/pair errors yield 1, invalid root/CLI input yields 2. Skipped links or missing references alone are not errors. Preview cannot establish future permission or backup success.

The write path is opt-in by invoking the normal command, not a background daemon. Errors are handled per pair, allowing other pairs to proceed; successful earlier writes are not rolled back. If a backup fails, replacement does not begin. If replacement fails, backups or partial temporary artifacts may remain. An operator should inspect the identifier-only report, locate the exact backup session and deliberately restore the intended original after checking concurrent edits. Automatic bulk rollback, retention and crash recovery are absent. Output failures and pathological recursion can escape the usual error mapping.

The existing `unittest` suite uses isolated temporary fixtures for parsing, variants, preview, backups, replacement failures, permissions and idempotence. Existing verification records are historical evidence, not executions in this review. No runtime or application tests were run here. Installation consists of distributing the script with Python 3.10+; relocating it changes its default root. There is no service deployment, database, Docker topology, payment flow or network API to document. A library comparison may discuss these concerns conceptually without implying that the other portfolio applications call the CLI.

Remaining evidence gaps: crash/power-loss durability, concurrent writers and filesystem races, ACL/ownership portability, very deep trees, backup retention and scale measurements. Resolve these with separately authorized implementation and isolated experiments; no throughput or complete shell-parser compatibility is claimed.
