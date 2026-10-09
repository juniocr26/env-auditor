# Project guide

[English](guide.md) | [Português brasileiro](../pt-BR/guide.md)

Use the [README](../../README.md) for exact commands/exclusions and [architecture](architecture.md) for the execution boundaries. This guide explains how to reason about a plan without executing synchronization.

## Read the pair before the outcome

For `api/.env.prod`, a local `.env.prod.example` wins over `api/.env.example`; neither a sibling nor a parent example participates. Missing references skip the target unchanged. A specific example can propose creating a missing variant; the base example creates only `.env`.

If the selected example declares A and B while the target declares A and OLD, the plan keeps A's existing literal value, adds B's reference assignment and removes OLD's whole block. Source-code use of OLD does not prevent removal. An existing empty A remains empty; reference defaults do not overwrite it. An empty reference removes all active assignments.

## Interpret preview and persistence

`--dry-run` and `--audit-only` produce the same proposed totals with no auditor writes. Proposed changes alone return 0. Errors return 1, while missing references/links are skips; 2 is invalid root/arguments. Preview does not test future backups/write permissions.

Normal execution backs up changed existing targets before replacement; a failed pair does not undo previously changed pairs. Inspect [failure limits](architecture.md#persistence-and-failure-boundaries) before treating atomic replacement as a global transaction. This documentation review executed no preview, synchronization or tests; [verification](verification.md) distinguishes historical checks.
