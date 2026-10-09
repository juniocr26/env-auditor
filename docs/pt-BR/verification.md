# Verificação

O contrato da CLI, as regras de sincronização, exclusões, backups, códigos de saída, comandos e limitações estão documentados no [README em português](../../README.pt-BR.md).

Execução anteriormente registrada em 2026-10-09, a partir de `Portifólio`:

```bash
python3 -B -m unittest discover -s env-auditor/tests -v
python3 -B env-auditor/scripts/audit-envs.py --dry-run
```

Os 17 testes unittest passaram. Fixtures temporárias verificam escrita, backups exatos dos bytes originais e blocos removidos, permissões, limpeza de temporários após falha de escrita atômica, idempotência, entradas malformadas ou ilegíveis, erros de descoberta, links simbólicos, seleção da raiz e referências de variantes e prévias sem escrita. As falhas de permissão são simuladas para funcionar mesmo com privilégios elevados.

Também foram executadas prévias reais em `env-auditor` com `python3 -B scripts/audit-envs.py --audit-only` e em `env-auditor/scripts` com `python3 -B audit-envs.py --dry-run`. As três selecionaram a raiz absoluta `Portifólio` e retornaram 0: uma atualização proposta, três alvos inalterados, um alvo ignorado por falta de exemplo e zero erros. A atualização proposta adiciona a variável `TESTE` a `rust-event-relay/.env`.

Os hashes SHA-256, bits de permissão e timestamps de modificação dos arquivos de ambiente descobertos permaneceram idênticos antes e depois das prévias. A existência da raiz de backups também permaneceu igual. Não foi executada sincronização normal no workspace real, nem testes ou serviços das aplicações irmãs, nem instalação de dependências.


## Auditoria documental estática — 2026-10-09

Script e 17 métodos de teste inspecionados sem importar ou executar. Arquitetura e material de entrevista alinhados à implementação baseada em exemplos autoritativos. Nenhum arquivo de ambiente ou backup foi lido/alterado; nenhuma prévia ou sincronização foi executada. Resultados anteriores continuam como evidência histórica. Checagens estáticas de links e alterações somente documentais estão na [revisão](../../../tecnical-interview/docs/pt-BR/verification.md).
