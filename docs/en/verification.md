# Verification

The maintained CLI contract, synchronization rules, exclusions, backups, exit statuses, commands, and limitations are documented in the [English README](../../README.md).

Executed on 2026-10-09 from `Portifólio`:

```bash
python3 -B -m unittest discover -s env-auditor/tests -v
python3 -B env-auditor/scripts/audit-envs.py --dry-run
```

All 17 unittest cases passed. Temporary fixtures exercise writes, exact original and removed-block backups, permissions, atomic-write failure cleanup, idempotency, malformed and unreadable inputs, discovery failures, symbolic links, root selection, variant references, and previews without writes. Permission errors are injected rather than depending on chmod failures under elevated privileges.

Real-workspace previews were also executed from `env-auditor` using `python3 -B scripts/audit-envs.py --audit-only` and from `env-auditor/scripts` using `python3 -B audit-envs.py --dry-run`. All three selected the absolute `Portifólio` root and exited 0: one proposed update, three unchanged targets, one skipped target lacking an example, zero errors. The proposed update adds the variable name `TESTE` in `rust-event-relay/.env`.

SHA-256 digests, permission bits, and modification timestamps of discovered environment files were identical before and after previews. Backup-root existence was unchanged. No normal synchronization was run on the real workspace, no sibling application suites or services were run, and no dependencies were installed.

