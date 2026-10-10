# Relatório do terminal

[Guia](../guides/project-guide.md) · [Verificação](../testing/verification.md)

Fixture sintética: `demo/.env` contém KEEP (vazia) e OLD; `demo/.env.example` contém KEEP e NEW. Valores omitidos. Raiz e sessão de backup normalizadas. Saídas geradas em fixtures temporárias isoladas.

## Auditoria (`--audit-only` ou `--dry-run`)

```text
Scan root: <scan-root>
Modo: auditoria
Projeto: demo
[demo] Discovered: .env, .env.example
Pair: demo/.env <- demo/.env.example
Alvo: demo/.env
Referência: demo/.env.example
┌──────────┬─────────────────────────┬─────────────────────────┐
│ Variável │ Situação                │ Ação prevista           │
├──────────┼─────────────────────────┼─────────────────────────┤
│ NEW      │ Somente no .env.example │ Adicionar ao .env       │
├──────────┼─────────────────────────┼─────────────────────────┤
│ OLD      │ Somente no .env         │ Remover do .env         │
├──────────┼─────────────────────────┼─────────────────────────┤
│ KEEP     │ Presente nos dois       │ Preservar valor do .env │
└──────────┴─────────────────────────┴─────────────────────────┘
  Proposed updated
Resumo final por projeto (comparação inicial)
Projeto: demo
Alvo: demo/.env
Referência: demo/.env.example
┌──────────┬─────────────────────────┬─────────────────────────────┐
│ Variável │ Situação                │ Ação prevista               │
├──────────┼─────────────────────────┼─────────────────────────────┤
│ NEW      │ Somente no .env.example │ Proposta: Adicionar ao .env │
├──────────┼─────────────────────────┼─────────────────────────────┤
│ OLD      │ Somente no .env         │ Proposta: Remover do .env   │
└──────────┴─────────────────────────┴─────────────────────────────┘
Ações propostas; nenhum arquivo foi alterado. Nenhum backup foi criado.
Modo de execução: auditoria
Proposed totals: created=0, updated=1, unchanged=0, skipped=0, errors=0, added=1, removed=1, shared=1, actual_created=0, actual_updated=0
```

## Sincronização com backup

```text
Scan root: <scan-root>
Modo: sincronização com backup
Projeto: demo
[demo] Discovered: .env, .env.example
Pair: demo/.env <- demo/.env.example
Alvo: demo/.env
Referência: demo/.env.example
┌──────────┬─────────────────────────┬─────────────────────────┐
│ Variável │ Situação                │ Ação prevista           │
├──────────┼─────────────────────────┼─────────────────────────┤
│ NEW      │ Somente no .env.example │ Adicionar ao .env       │
├──────────┼─────────────────────────┼─────────────────────────┤
│ OLD      │ Somente no .env         │ Remover do .env         │
├──────────┼─────────────────────────┼─────────────────────────┤
│ KEEP     │ Presente nos dois       │ Preservar valor do .env │
└──────────┴─────────────────────────┴─────────────────────────┘
  Backup: <scan-root>/.env-audit-backups/<session>/demo/.env.original
  Backup: <scan-root>/.env-audit-backups/<session>/demo/.env.removed
  updated
Resumo final por projeto (comparação inicial)
Projeto: demo
Alvo: demo/.env
Referência: demo/.env.example
┌──────────┬─────────────────────────┬──────────────────────────────┐
│ Variável │ Situação                │ Ação prevista                │
├──────────┼─────────────────────────┼──────────────────────────────┤
│ NEW      │ Somente no .env.example │ Concluída: Adicionar ao .env │
├──────────┼─────────────────────────┼──────────────────────────────┤
│ OLD      │ Somente no .env         │ Concluída: Remover do .env   │
└──────────┴─────────────────────────┴──────────────────────────────┘
Modo de execução: sincronização com backup
Totals: created=0, updated=1, unchanged=0, skipped=0, errors=0, added=1, removed=1, shared=1, actual_created=0, actual_updated=1
```
