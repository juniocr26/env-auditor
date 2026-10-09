# Guia do projeto

[English](../en/guide.md) | [Português brasileiro](guide.md)

Consulte [README](../../README.pt-BR.md) para comandos/exclusões e [arquitetura](architecture.md) para fronteiras. Aqui o objetivo é raciocinar sobre o plano sem executar sincronização.

## Leia o par antes do resultado

Para `api/.env.prod`, `.env.prod.example` local tem prioridade sobre `api/.env.example`; exemplos irmãos/ancestrais não participam. Referência ausente ignora alvo intacto. Exemplo específico pode propor variante ausente; o base só cria `.env`.

Se o exemplo declara A/B e o alvo A/OLD, mantém valor literal de A, acrescenta atribuição B da referência e remove bloco OLD inteiro. Uso de OLD no código não impede remoção. A vazio permanece vazio; defaults não o sobrescrevem. Referência vazia remove todas as atribuições ativas.

## Interprete prévia e persistência

`--dry-run` e `--audit-only` dão os mesmos totais propostos sem escrita do auditor. Diferenças sozinhas saem 0. Erros dão 1; referências ausentes/links são skips; 2 é raiz/argumentos inválidos. Prévia não testa backups/permissões futuros.

Execução normal faz backup de alvos existentes alterados antes do replace; par com falha não desfaz pares anteriores. Leia [limites](architecture.md#persistência-e-fronteiras-de-falha) antes de tratar replace como transação global. Esta revisão não executou prévia, sincronização ou testes; [verificação](verification.md) separa evidências históricas.
