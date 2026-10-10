# Verification

The maintained CLI contract, synchronization rules, exclusions, backups, exit statuses, commands, and limitations are documented in the [English README](../../../README.md).

Previously recorded execution on 2026-10-09 from `Portifólio` (not rerun in this documentation audit):

```bash
python3 -B -m unittest discover -s env-auditor/tests -v
python3 -B env-auditor/scripts/audit-envs.py --dry-run
```

All 17 unittest cases passed. Temporary fixtures exercise writes, exact original and removed-block backups, permissions, atomic-write failure cleanup, idempotency, malformed and unreadable inputs, discovery failures, symbolic links, root selection, variant references, and previews without writes. Permission errors are injected rather than depending on chmod failures under elevated privileges.

Real-workspace previews were also executed from `env-auditor` using `python3 -B scripts/audit-envs.py --audit-only` and from `env-auditor/scripts` using `python3 -B audit-envs.py --dry-run`. All three selected the absolute `Portifólio` root and exited 0: one proposed update, three unchanged targets, one skipped target lacking an example, zero errors. The proposed update adds the variable name `TESTE` in `rust-event-relay/.env`.

SHA-256 digests, permission bits, and modification timestamps of discovered environment files were identical before and after previews. Backup-root existence was unchanged. No normal synchronization was run on the real workspace, no sibling application suites or services were run, and no dependencies were installed.


## Static documentation audit — 2026-10-09

Inspected the script and all 17 checked-in test methods without importing or executing them. Updated the architecture and interview material to the authoritative-example implementation. No environment files or backups were read or changed, and no preview or synchronization was executed. Previous runtime results above remain historical evidence. Static Markdown link and documentation-only change checks are recorded in the portfolio interview [review](../../../../engineering-library/docs/en/testing/verification.md).

## Presentation validation — 2026-10-10

Executed `python3 -B -m unittest discover -s env-auditor/tests -v`: all 22 tests passed. Five focused cases add category ordering, table alignment/separators, project and pair grouping, shared-key omission, initial counts after failure, completed/failed/unapplied actions, missing and empty targets, missing references and safe parse diagnostics. Existing tests cover empty values, both read-only CLI aliases with file/directory snapshots, backups, permission preservation, malformed input and injected failures. Generated [terminal examples](../operations/terminal-report.md) using temporary synthetic fixtures in audit and backup synchronization modes. No real environment synchronization or deployment; no commits or pushes. No-backup and usage-analysis modes remain unavailable.
