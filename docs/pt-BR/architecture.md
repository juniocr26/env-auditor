# Decisões de Arquitetura e Trade-offs

[English](../en/architecture.md) | [Português](architecture.md)

ENV Auditor é uma ferramenta filesystem local: descobre conjuntos de ambientes, sincroniza contrato de chaves, classifica referências, remove atribuições sem evidência e reporta estrutura final. Este documento avalia [audit-envs.py](../../scripts/audit-envs.py), com o guia Technical Interview como contexto. Alternativas são opções de revisão, não decisões históricas presumidas.

## Estado da implementação

- **Implementado:** CLI Python standard library, descoberta, sincronização assimétrica, blocos multiline, duplicatas/possíveis secrets, classificação forte/fraca/sem evidência, exclusões, backups, dry-run, audit-only e exit status strict.
- **Projetado / preparado arquiteturalmente:** `SyncAction` representa sincronização planejada no dry-run; dataclasses/funções separam modelos, traversal, parsing, evidências e escrita num script. Não é engine de transação ou sistema de plugins.
- **Planejado / trabalho futuro:** sem roadmap versionado. Substituição atômica, locking, parsers e suítes regressão/CI são melhorias condicionais, não implementações atuais. Não há suíte automatizada ou workflow CI versionado.

## Decisão: CLI Python sem dependências em vez de serviço

**Contexto.** Entrada é um workspace local de texto, não fluxo remoto de contas/usuários.

**Decisão e justificativa.** Python 3.10+ fornece traversal, regex, JSON, dataclasses, argumentos e backups sem instalar pacotes. Um script mantém operação perto do filesystem e expõe modos revisáveis. Sem banco, ambiente Docker ou serviço de rede.

**Alternativas.** Shell/awk reduz runtime mas complica parsing multiline/modelos. Go/Rust distribui binário com custo de compilação/plataformas. Serviço web adiciona upload/acesso e transporta valores de configuração desnecessariamente.

**Trade-offs e consequências.** Parser/traversal são responsabilidade própria, sem semântica dotenv completa de dependência. Script fácil de copiar mas grande; funções/dataclasses, não pacotes, separam responsabilidades. Tempo exibido mede scan local, não benchmark portátil.

**Reavaliar quando.** Packaging, extensões independentes, compatibilidade dotenv completa ou tamanho dificultarem manutenção/testes.

**Evidências:** imports, `EnvFile`, `UsageEvidence`, `SyncAction`, `main`, [requisitos](../../README.pt-BR.md).

## Decisão: Um diretório representa um contrato de ambientes

**Contexto.** Local/prod/test podem divergir em chaves mantendo valores próprios.

**Decisão e justificativa.** Descoberta agrupa `.env`, `.env.*`, `.env.example` no mesmo diretório; cada diretório é um conjunto, inclusive monorepo. União de chaves reais entra no example vazia; chaves ausentes nos ambientes recebem bloco/default do example. Valor real nunca é copiado para example ou outro ambiente real.

**Alternativas.** Example autoritativo poderia rejeitar extras em vez de incorporá-los. Schemas por ambiente permitem diferenças deliberadas com mais configuração. Contrato global mistura projetos independentes.

**Trade-offs e consequências.** Chaves específicas viram placeholders comuns; paridade é igualdade de chaves, não valores válidos/app funcionando. Defaults example devem ser seguros. Valores existentes não são sobrescritos para chaves iguais. Sincronização precede cleanup; chave adicionada sem uso pode ser removida depois. Só example cria `.env`, salvo bloqueio de secret; só ambientes cria example. Sem registro de diretórios esperados fora dos descobertos.

**Reavaliar quando.** Ambientes exigirem schemas diferentes ou example revisado precisar rejeitar extras.

**Evidências:** `discover_projects`, `sync_project`, `create_example_from_envs`, `create_env_from_example`.

## Decisão: Parsear blocos sem avaliar sintaxe de ambiente

**Contexto.** Extrair chave/preservar default multiline difere de interpretar shell/framework.

**Decisão e justificativa.** Regex reconhece identificadores com `export` opcional; scanner de aspas agrupa multiline. `EnvEntry.block` preserva bloco para cópia. Duplicatas são reportadas; mapa guarda último bloco reconhecido. Ferramenta lê texto, não executa shell nem resolve interpolação.

**Alternativas.** Parser dotenv especializado melhora compatibilidade mas pode normalizar formato/retornar só valores decodificados. Parser por linguagem amplia muito o escopo.

**Trade-offs e consequências.** Linhas malformadas/não atribuições são ignoradas, sem validação abrangente. Comentários são preservados no original durante remoção, mas não anexados ao bloco copiado. Aspas não fechadas podem absorver linhas seguintes; remover bloco pode remover conteúdo posterior. Reescrita normaliza line endings; UTF-8 inválido com replacement não preserva bytes. Duplicatas não são reparadas automaticamente nem escolhem valor efetivo da aplicação.

**Reavaliar quando.** Sintaxe complexa, preservação exata ou bloqueio de escrita por input malformado forem necessários.

**Evidências:** `ENV_LINE_RE`, `_quote_is_open`, `parse_env`, `remove_keys_from_env_file`.

## Decisão: Evidência heurística com preservação conservadora de referência fraca

**Contexto.** Variáveis podem ser usadas por diversas linguagens, helpers ou infraestrutura externa.

**Decisão e justificativa.** Cada candidato runtime/config é lido uma vez por scan de projeto. Padrões conhecidos geram evidência forte; tokens uppercase independentes geram fraca. Qualquer evidência preserva chave. `ignore_unused_keys` protege consumo externo. Declarações env, Markdown/docs e assets binários conhecidos não contam como uso, evitando autojustificação pela existência.

**Alternativas.** Busca só por token preserva muita configuração antiga. AST distingue acesso de comentário mas exige parsers por linguagem. Tracing runtime vê caminhos exercitados, não todos os deploys. Report-only evita remoção incorreta mas exige limpeza manual.

**Trade-offs e consequências.** Regex em comentários/strings dá falsos positivos; nomes dinâmicos/arquivos ignorados ou ilegíveis dão falsos negativos. Falhas de leitura durante scan são ignoradas silenciosamente: sem evidência não prova não uso. Parser aceita lowercase, tokens fracos só uppercase. Arquivos inteiros entram em memória, sem teto de tamanho. Conjuntos aninhados podem gerar scans repetidos/sobrepostos por busca recursiva de cada projeto. Tempo local não prova trabalho O(1) por arquivo/memória constante; evita releitura por cada chave.

**Reavaliar quando.** Ocorrerem remoções falsas, repositórios crescerem ou semântica precisa for requisito. Adicionar regressões/exclusões antes de ampliar automação.

**Evidências:** `STRONG_USAGE_EXTRACTORS`, `ENV_TOKEN_RE`, `analyze_usage`, `iter_runtime_files`, [limites estáticos](../../README.pt-BR.md).

## Decisão: Cleanup automático com modos distintos de revisão

**Contexto.** Automação altera configuração local com evidências incompletas.

**Decisão e justificativa.** Padrão sincroniza **e remove** chaves sem evidência; fracas/excluídas sobrevivem. `--audit-only` reporta arquivos atuais sem sync/remover; `--dry-run` modela chaves sincronizadas via `SyncAction` e simula remoção sem escrever. Modos incompatíveis. `--show-usage` mostra chaves/caminhos para revisão.

**Alternativas.** Cleanup opt-in/confirmação interativa reduz surpresa mas muda automação. CLI atual não possui nenhum; sem `--remove-unused`.

**Trade-offs e consequências.** Padrão não é read-only seguro. Dry-run modela conjuntos de chaves, não plano transacional completo de conteúdo; listas por arquivo usam arquivos físicos, podendo omitir chaves que seriam criadas antes. `--strict` define exit status final, não preflight/proibição de escrita. `--strict-unused` exige strict e é mais útil em audit-only, pois cleanup normal remove findings. Sem strict, pode sair 0 com problemas reportados. Argparse trata argumentos; RuntimeErrors de configuração tratados retornam 2, mas nem toda exceção filesystem segue esse caminho.

**Reavaliar quando.** CI/time exigir revisão antes da escrita, plano estruturado ou classificação previsível de erros. `--audit-only --strict` serve para CI read-only atual; nenhuma integração CI está entregue.

**Evidências:** `audit`, `main`, help CLI. Fixtures temporárias confirmaram bytes intactos em audit/dry-run e comportamento cleanup/strict.

## Decisão: Heurística de secret e relatório de chaves sem garantia universal de sigilo

**Contexto.** Defaults example podem ser versionados/copied; credenciais reais não devem ser propagadas.

**Decisão e justificativa.** Nome sensível mais valor não-placeholder gera finding no example; `public_non_secret_keys` ignora explicitamente a heurística. Rotinas mostram nomes/caminhos em vez de valores de atribuições. Sync e criação `.env` a partir de example são bloqueados com entradas suspeitas.

**Alternativas.** Secret scanners especializados reconhecem mais padrões/histórico; secret manager muda armazenamento/distribuição, não só paridade.

**Trade-offs e consequências.** Não é scan por entropia/validação semântica/remediação. Credencial com nome inocente pode passar; default seguro PASSWORD pode ser sinalizado. Valores entram em memória/backups. Bloquear sync **não** bloqueia cleanup posterior: fixture reproduziu remoção de chave não usada enquanto example suspeito causou strict exit 1. Guarda não é proteção global de escrita. Relatório evita valores de atribuição, mas caminhos/chaves e diagnósticos de JSON inválido podem ser sensíveis; não há garantia de redaction para input arbitrário.

**Reavaliar quando.** Gate precisar impedir toda escrita, logs exigirem redaction abrangente ou detecção exigir garantias maiores.

**Evidências:** `SECRET_NAME_RE`, `SAFE_PLACEHOLDER_RE`, `suspicious_example_keys`, `sync_project`, `audit`, `load_audit_config`.

## Decisão: Backups e traversal delimitado em vez de transação filesystem

**Contexto.** Desenvolvedor precisa recuperar configuração existente sem infraestrutura.

**Decisão e justificativa.** Copia arquivos existentes antes de cada mutação para `.env-audit-backups` com timestamp/caminho relativo; tenta permissões 0700/0600. Arquivos novos não têm versão anterior. `os.walk` poda dependências/storage/cache e paths ignorados; não segue symlinks de diretórios por padrão.

**Alternativas.** Arquivo temporário/rename atômico, locks e plano multi-arquivo melhoram interrupção/concorrência. Git não recupera segredos não versionados; backup remoto adiciona risco/retencão.

**Trade-offs e consequências.** `write_text` direto sem rename, lock ou rollback global: falha entre arquivos deixa sync parcial. Backups contêm valores reais e precisam de proteção/retenção; chmod best effort, arquivos novos usam umask. Symlinks de arquivos ainda podem ser lidos/escritos; root resolvido não impõe containment de todos os alvos. Ignore lexical não é sandbox. `ignore_files` filtra uso/poda diretórios, mas descoberta não aplica a cada nome env; `ignore_projects` controla descoberta, não toda busca de um projeto pai. Revisar root/exclusões deliberadamente.

**Reavaliar quando.** Execuções simultâneas, configuração crítica, fronteira symlink ou recuperação atômica forem requisitos. Justificam filesystem mais forte, não banco/serviço web por padrão.

**Evidências:** `is_ignored`, `discover_projects`, `iter_runtime_files`, `backup_path_for`, `create_backup`, `append_section`, `remove_keys_from_env_file`.

## Investigação runtime — 2026-10-05

Script executado com Python standard library sobre três conjuntos `TemporaryDirectory`, nunca ambientes reais do portfólio. Hashes confirmaram bytes intactos em audit-only/dry-run. Modo normal removeu chave sem evidência, preservou fracas/excluídas, copiou default example e criou três backups sem copiar valor real fictício ao example ou imprimi-lo. Example-only com possível secret bloqueou criação `.env` e retornou strict 1. Fixture separada reproduziu cleanup apesar de sync bloqueado por secret. Ambientes temporários, fixtures de fonte/config e backups foram removidos automaticamente. Experimentos não são suíte regressão nova nem verificação exaustiva de parser/segurança.
