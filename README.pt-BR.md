# env-auditor

[English](README.md) | [Português brasileiro](README.pt-BR.md)

CLI para Python 3.10+, apenas com a biblioteca padrão. A execução normal sincroniza arquivos de ambiente com exemplos autoritativos, valida sua estrutura e cria backups automaticamente antes de alterar alvos existentes.

Em `Portifólio/env-auditor`:

```bash
python3 -B scripts/audit-envs.py
python3 -B scripts/audit-envs.py --dry-run
python3 -B scripts/audit-envs.py --audit-only
python3 -B scripts/audit-envs.py /caminho/absoluto/da/raiz
```

A raiz padrão é exatamente `Path(__file__).resolve().parents[2]`: o workspace pai de `env-auditor`, atualmente `Portifólio`. Ela independe do diretório de execução. Em `Portifólio`, use `python3 -B env-auditor/scripts/audit-envs.py`; em `env-auditor/scripts`, use `python3 -B audit-envs.py`. O programa não muda o diretório de trabalho. Raízes relativas explícitas são resolvidas a partir do diretório do chamador. Raízes inexistentes ou que não sejam diretórios são rejeitadas.

Os dois modos de prévia calculam as mesmas mudanças propostas sem escrever alvos, backups, diretórios ou quaisquer outros arquivos. São mutuamente exclusivos. Diferenças propostas por si só não causam falha.

## Descoberta e sincronização

A descoberta recursiva usa o sistema de arquivos e inclui projetos irmãos, diretórios aninhados e ocultos e arquivos ignorados pelo Git. Não consulta arquivos rastreados nem código das aplicações. Os nomes elegíveis são `.env` e `.env.*`. Todo nome terminado em `.example` é referência, nunca alvo de execução.

Cada `.env.example` controla o `.env` do mesmo diretório. Variantes como `.env.prod` preferem `.env.prod.example`, recorrendo ao `.env.example` local se necessário. Exemplos específicos criam os alvos correspondentes ausentes; o exemplo base cria `.env`, mas não inventa variantes. Alvos sem exemplo ficam inalterados e são relatados como ignorados. Referências nunca são alteradas ou geradas a partir de valores reais.

Atribuições ausentes são copiadas literalmente da referência. Valores existentes, inclusive vazios, comentários, formatação, duplicatas de chaves mantidas e blocos com valores multilinha entre aspas são preservados. Atribuições ativas ausentes do exemplo selecionado são removidas exclusivamente por esse motivo. Há suporte a UTF-8 e literais multilinha entre aspas simples ou duplas. O conteúdo nunca é executado, expandido, interpolado ou carregado como script. Um exemplo vazio válido possui zero chaves. Chaves duplicadas no exemplo, UTF-8 inválido, atribuições malformadas, aspas sem fechamento e entradas ilegíveis causam erro sem alterar o alvo correspondente. Alvos novos copiam o exemplo validado, inclusive comentários.

Diretórios excluídos por nome:

```text
.git .hg .svn node_modules vendor __pycache__ .venv venv
.env-audit-backups backups backup dist build out target .next .nuxt .cache
coverage .pytest_cache .tox
```

Também são excluídos `bootstrap/cache`, `public/build`, nomes contendo `.bak` e nomes terminados em `~`. Links simbólicos são relatados e ignorados; diretórios e arquivos de ambiente simbólicos nunca são seguidos. Erros de descoberta causam falha. A mensagem de descoberta vazia só aparece após uma descoberta bem-sucedida e realmente vazia.

## Backups e escrita

Antes de alterar um alvo existente, são salvos os bytes originais exatos e apenas os blocos de atribuições removidas:

```text
<raiz>/.env-audit-backups/<timestamp UTC com sufixo único>/<diretório relativo>/<nome>.original
<raiz>/.env-audit-backups/<timestamp UTC com sufixo único>/<diretório relativo>/<nome>.removed
```

Diretórios de backup usam permissões `0700`, arquivos usam `0600`, e a raiz dos backups contém um `.gitignore` local com `*`. Os nomes dos diretórios evitam colisões. Falha no backup impede a alteração do alvo; backups parciais podem permanecer após uma falha. Alvos novos e inalterados não geram backups. A escrita usa arquivo temporário no mesmo diretório e substituição atômica; temporários são removidos após falhas. Os bits de permissão existentes são preservados, e alvos novos recebem `0600`.

Os relatórios mostram raiz absoluta, arquivos agrupados por diretório, pares selecionados, nomes e contagens de variáveis adicionadas/removidas, resultados de criação/atualização/inalterado/ignorado, caminhos de backup, erros e totais. Valores de ambiente e conteúdo de exceções do sistema de arquivos nunca são impressos.

## Códigos de saída e recursos aposentados

- `0`: processamento concluído sem erros de descoberta ou dos pares, inclusive prévias.
- `1`: erros de descoberta ou processamento; outros pares elegíveis continuam sendo processados.
- `2`: raiz ou argumentos inválidos.

`--strict`, `--strict-unused`, `--show-usage` e `--no-backup` foram aposentados e são rejeitados. `.env-audit.json` foi aposentado: sua presença é relatada e as configurações são ignoradas. Foram removidas a exclusão baseada em uso estático e a geração/alteração de exemplos.

## Verificação e limitações

```bash
# Em Portifólio:
python3 -B -m unittest discover -s env-auditor/tests -v
python3 -B env-auditor/scripts/audit-envs.py --dry-run
```

Os testes escrevem apenas em fixtures temporárias e simulam falhas de permissão, inclusive para processos com privilégios elevados. O workspace real é verificado somente em modo de prévia.

A substituição atômica ocorre por alvo; não há transação entre todos os alvos nem bloqueio de escritores concorrentes. Evite edições simultâneas durante a sincronização. São usados bits POSIX de permissão; proprietário, ACLs, timestamps e atributos estendidos não são preservados. O parser aceita atribuições literais e comentários, não scripts shell arbitrários. As referências são autoritativas; revise a prévia antes de sincronizar.

[Arquitetura](docs/pt-BR/architecture.md) · [Guia](docs/pt-BR/guide.md) · [Instalação](docs/pt-BR/setup.md) · [Verificação](docs/pt-BR/verification.md) · [Licença](LICENSE)

