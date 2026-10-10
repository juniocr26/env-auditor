# Guia do projeto

[English](../../en/guides/project-guide.md) | [Português brasileiro](project-guide.md)

Consulte [README](../../../README.pt-BR.md) para comandos/exclusões e [arquitetura](../architecture/overview.md) para fronteiras. Aqui o objetivo é raciocinar sobre o plano sem executar sincronização.

## Leia o par antes do resultado

Para `api/.env.prod`, `.env.prod.example` local tem prioridade sobre `api/.env.example`; exemplos irmãos/ancestrais não participam. Referência ausente ignora alvo intacto. Exemplo específico pode propor variante ausente; o base só cria `.env`.

Se o exemplo declara A/B e o alvo A/OLD, mantém valor literal de A, acrescenta atribuição B da referência e remove bloco OLD inteiro. Uso de OLD no código não impede remoção. A vazio permanece vazio; defaults não o sobrescrevem. Referência vazia remove todas as atribuições ativas.

## Interprete prévia e persistência

`--dry-run` e `--audit-only` dão os mesmos totais propostos sem escrita do auditor. Diferenças sozinhas saem 0. Erros dão 1; referências ausentes/links são skips; 2 é raiz/argumentos inválidos. Prévia não testa backups/permissões futuros.

Execução normal faz backup de alvos existentes alterados antes do replace; par com falha não desfaz pares anteriores. Leia [limites](../architecture/overview.md#persistência-e-fronteiras-de-falha) antes de tratar replace como transação global. Veja [verificação](../testing/verification.md) para evidências datadas.

## Relatório completo e resumo de ações

As colunas do terminal são `Variável | Situação | Ação prevista` em todos os modos suportados. Cada par válido recebe tabela Unicode com a união inicial das chaves, nunca valores. Chaves só no exemplo aparecem primeiro; só no alvo, depois; compartilhadas, por último. Cada grupo é alfabético. Larguras seguem o conteúdo, com padding e separadores entre todas as linhas. Situações e ações usam os nomes reais do alvo e da referência.

O projeto é o primeiro diretório relativo abaixo da raiz; pares na raiz usam `.`. A descoberta continua por diretório; o resumo agrupa pares aninhados pelo projeto e repete caminhos de alvo/referência. O relatório completo inclui compartilhadas (`Presente nos dois` → `Preservar valor do <alvo>`); o resumo as omite. Projetos sem achados mostram `Nenhuma pendência de sincronização.` Referências ausentes e falhas de parsing/escrita permanecem como achados que exigem atenção. Alvos ausentes são explícitos, inclusive criação com referência vazia.

O resumo preserva a comparação inicial. Prévia usa `Proposta:` e confirma que nenhum arquivo foi alterado nem backup criado. Escrita bem-sucedida usa `Concluída:`. Pares com falha mostram `Falhou:`; ações conhecidas de variáveis usam `Não aplicada:`. Mudanças concluídas são resultados, não pendências. Alvo ausente pode receber linha adicional de criação com coluna de variável vazia. Diagnósticos de descoberta/arquivos ignorados e caminhos de backup continuam visíveis.

`added`, `removed` e `shared` contam chaves únicas por par validado e planejado, inclusive planos cuja escrita falha. `created`, `updated` e `unchanged` mantêm resultados por par (propostos na prévia); `actual_created` e `actual_updated` contam somente escritas bem-sucedidas. Erros e skips preservam seu significado; o modo é explícito.

Não há análise de uso, classificação de baixo uso ou ausência de referências no código. Ausência no exemplo é diferença de sincronização, nunca prova de desuso. A regra autoritativa existente continua removendo automaticamente atribuições só no alvo. Nenhuma exclusão baseada em busca de referências foi acrescentada. Sincronização sem backup não é suportada: `--no-backup` continua rejeitado (saída 2).

Veja [saídas sintéticas geradas](../operations/terminal-report.md) de auditoria e escrita.
