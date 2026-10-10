# Project guide

[English](project-guide.md) | [Português brasileiro](../../pt-BR/guides/project-guide.md)

Use the [README](../../../README.md) for exact commands/exclusions and [architecture](../architecture/overview.md) for the execution boundaries. This guide explains how to reason about a plan without executing synchronization.

## Read the pair before the outcome

For `api/.env.prod`, a local `.env.prod.example` wins over `api/.env.example`; neither a sibling nor a parent example participates. Missing references skip the target unchanged. A specific example can propose creating a missing variant; the base example creates only `.env`.

If the selected example declares A and B while the target declares A and OLD, the plan keeps A's existing literal value, adds B's reference assignment and removes OLD's whole block. Source-code use of OLD does not prevent removal. An existing empty A remains empty; reference defaults do not overwrite it. An empty reference removes all active assignments.

## Interpret preview and persistence

`--dry-run` and `--audit-only` produce the same proposed totals with no auditor writes. Proposed changes alone return 0. Errors return 1, while missing references/links are skips; 2 is invalid root/arguments. Preview does not test future backups/write permissions.

Normal execution backs up changed existing targets before replacement; a failed pair does not undo previously changed pairs. Inspect [failure limits](../architecture/overview.md#persistence-and-failure-boundaries) before treating atomic replacement as a global transaction. See [verification](../testing/verification.md) for dated execution evidence.

## Complete report and action summary

Terminal columns are Portuguese in every supported mode: `Variável | Situação | Ação prevista`. Each valid pair gets a Unicode bordered table with the initial union of keys, never values. Example-only keys come first, target-only second, shared last; each group is alphabetical. Widths follow the contents, with padding and a separator between every row. Actual target/reference filenames appear in statuses and actions.

Projects are the first relative directory below the scan root; root-level pairs use `.`. Discovery remains grouped by directory, while the final summary groups nested pairs under their project and repeats each target/reference path. The complete report includes shared keys (`Presente nos dois` → `Preservar valor do <target>`); the summary omits them. Projects without findings print `Nenhuma pendência de sincronização.` Missing references and parse/write failures remain attention findings. Missing targets are explicitly identified, including empty references requiring creation.

The summary retains the initial comparison. Preview actions use `Proposta:` and explicitly confirm no files or backups were created. Successful write actions use `Concluída:`. Failed pairs show `Falhou:` and known variable actions use `Não aplicada:`. Completed changes are historical outcomes, not pending work. An absent target can appear as an additional file-creation row with an empty variable column. Discovery/skipped-file diagnostics and backup paths remain visible.

`added`, `removed` and `shared` count unique keys per successfully parsed/planned pair, including plans whose writes later fail. `created`, `updated` and `unchanged` retain pair outcomes (proposed in preview); `actual_created` and `actual_updated` count successful writes only. Errors and skips retain their existing meaning; execution mode is explicit.

There is no source usage analysis, low-use or no-reference classification. Absence from an example is only a synchronization difference, never evidence of non-use. The existing authoritative-reference rule still removes target-only assignments automatically. No deletion based on reference scanning was added. Synchronization without backups is unsupported: `--no-backup` remains rejected (exit 2).

See [generated synthetic output](../operations/terminal-report.md) for complete audit and write reports.
